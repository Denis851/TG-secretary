import asyncio
import logging
import signal
import os
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis
from redis.exceptions import ConnectionError, AuthenticationError
from aiohttp import web
from handlers import checklist, goals, start, progress, mood, schedule, reports
from handlers import settings as settings_handler
from services.scheduler import setup_jobs
from services.keep_alive import KeepAliveService
from middlewares.rate_limit import RateLimitMiddleware
from middlewares.error_handler import GlobalErrorHandler
from health import setup_health_check
from config import settings, clean_template_var
import structlog
from urllib.parse import urlparse
from typing import Optional
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramConflictError
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from redis.asyncio.retry import Retry
from redis.backoff import ExponentialBackoff
from redis.exceptions import TimeoutError
import time
import sys
import traceback

# Configure logging before anything else
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

# Configure structlog
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.format_exc_info,
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.PrintLoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Глобальные переменные для корректного завершения
bot = None
dp = None
scheduler = None
redis = None
keep_alive = None

# Application state keys
REDIS_CLIENT_KEY = web.AppKey('redis_client', Redis)
BOT_KEY = web.AppKey('bot', Bot)
APP_STATE_KEY = web.AppKey('app_state', dict)

async def on_shutdown(dp: Dispatcher, bot: Bot, redis_client: Optional[Redis]):
    logger.info("Shutting down bot...")
    
    # Delete webhook with retries
    if not await delete_webhook_with_retry(bot):
        logger.error("Failed to delete webhook after all retries")
    
    # Close Redis connection
    if redis_client is not None:
        try:
            await redis_client.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error("Error closing Redis connection", error=str(e))
    
    # Close storage
    try:
        if dp.storage:
            await dp.storage.close()
        logger.info("Storage closed")
    except Exception as e:
        logger.error("Error closing storage", error=str(e))
    
    # Close bot session
    try:
        await bot.session.close()
        logger.info("Bot session closed")
    except Exception as e:
        logger.error("Error closing bot session", error=str(e))

def signal_handler(signum, frame):
    """Обработчик сигналов завершения"""
    logger.info("received_signal", signal=signum)
    if dp and bot:
        asyncio.create_task(on_shutdown(dp, bot, redis))

async def setup_redis() -> Optional[Redis]:
    """Setup Redis connection with retries"""
    max_retries = 5
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            # Get Redis URL from settings
            if os.getenv('RAILWAY_ENVIRONMENT') == 'production':
                # For Railway environment, construct the URL using internal hostname
                redis_password = os.getenv('REDIS_PASSWORD', '')
                redis_url = f"redis://default:{redis_password}@redis.railway.internal:6379/0"
                logger.info("Using Railway internal Redis URL")
            else:
                # For local development
                redis_url = settings.redis_url
                logger.info("Using local Redis URL")

            # Mask password for logging
            masked_url = redis_url
            if 'default:' in redis_url:
                masked_url = redis_url.replace(redis_url.split('default:')[1].split('@')[0], '***')
            
            logger.info(f"Attempting to connect to Redis (attempt {attempt + 1}/{max_retries})")
            logger.debug("Redis connection details", url=masked_url)
            
            # Create Redis client with basic retry configuration
            redis_client = Redis.from_url(
                url=redis_url,
                decode_responses=True,
                socket_timeout=5.0,
                socket_connect_timeout=5.0,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            await redis_client.ping()
            logger.info("Successfully connected to Redis")
            return redis_client
            
        except (ConnectionError, TimeoutError, AuthenticationError) as e:
            logger.error(f"Failed to connect to Redis (attempt {attempt + 1}/{max_retries})", 
                        error=str(e), 
                        attempt=attempt + 1, 
                        max_retries=max_retries,
                        env=os.getenv('RAILWAY_ENVIRONMENT'),
                        redis_host=os.getenv('REDIS_HOST'),
                        redis_url=masked_url)
            
            if attempt < max_retries - 1:
                logger.info(f"Waiting {retry_delay} seconds before next attempt...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error("Max retries reached. Could not establish Redis connection.")
                return None
                
        except Exception as e:
            logger.error("Unexpected error while connecting to Redis", 
                        error=str(e), 
                        error_type=type(e).__name__,
                        traceback=traceback.format_exc())
            return None

async def delete_webhook_with_retry(bot: Bot, max_retries: int = 3) -> bool:
    for attempt in range(max_retries):
        try:
            webhook_info = await bot.get_webhook_info()
            if webhook_info.url:
                await bot.delete_webhook(drop_pending_updates=True)
                logger.info("Successfully deleted webhook")
            return True
        except Exception as e:
            logger.warning(
                "Failed to delete webhook",
                attempt=attempt + 1,
                max_retries=max_retries,
                error=str(e)
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
            continue
    return False

async def check_and_terminate_duplicate_instances(bot: Bot) -> bool:
    """Check for and terminate any duplicate bot instances"""
    try:
        # Get current webhook info
        webhook_info = await bot.get_webhook_info()
        if webhook_info.url:
            logger.info("Found existing webhook, attempting to delete it")
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("Successfully deleted existing webhook")
        
        # Try to get bot info to check if it's running
        bot_info = await bot.get_me()
        logger.info(f"Bot is running with username: @{bot_info.username}")
        return True
    except Exception as e:
        logger.error(f"Error checking for duplicate instances: {str(e)}")
        return False

async def main():
    # Initialize variables at the top level of main
    dp = None
    bot = None
    redis_client = None
    runner = None
    keep_alive_task = None
    app = None

    try:
        logger.info("Starting application...")
        
        # Log environment variables (excluding sensitive data)
        env_vars = {k: v for k, v in os.environ.items() 
                   if k not in ['BOT_TOKEN', 'REDIS_PASSWORD']}
        logger.debug("Environment variables", **env_vars)
        
        # Validate required environment variables
        required_vars = ['BOT_TOKEN']
        if os.getenv('RAILWAY_ENVIRONMENT') == 'production':
            required_vars.append('REDIS_PASSWORD')
            
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            logger.error("Missing required environment variables", missing_vars=missing_vars)
            return

        try:
            # Create web application first
            app = web.Application()
            logger.info("Web application created")
            
            # Add simple health check that responds immediately
            async def simple_health_check(request):
                return web.json_response({
                    'status': 'STARTING',
                    'message': 'Application is starting up',
                    'startup_time': time.time()
                })
            
            # Use app.router.add_route instead of add_get to have more control
            app.router.add_route('GET', '/health', simple_health_check)
            logger.info("Simple health check endpoint added")
            
            # Setup web server first
            runner = web.AppRunner(app)
            await runner.setup()
            port = int(os.getenv('PORT', 8080))
            site = web.TCPSite(runner, '0.0.0.0', port)
            await site.start()
            logger.info(f"Web server started on port {port}")
            
            # Add startup delay
            startup_delay = int(os.getenv('STARTUP_DELAY', '30'))
            logger.info(f"Waiting {startup_delay} seconds before continuing initialization...")
            await asyncio.sleep(startup_delay)
            
            # Setup Redis with retries
            redis_client = await setup_redis()
            if not redis_client:
                logger.error("Could not establish Redis connection. Exiting...")
                return
            
            # Store Redis client in app state
            app[REDIS_CLIENT_KEY] = redis_client
            logger.info("Redis client initialized and stored in app state")

            # Initialize bot and dispatcher
            session = AiohttpSession()
            bot = Bot(token=settings.BOT_TOKEN, session=session)
            logger.info("Bot initialized")
            
            app[BOT_KEY] = bot
            logger.info("Bot stored in app state")
            
            # Check for and terminate any duplicate instances
            if not await check_and_terminate_duplicate_instances(bot):
                logger.error("Failed to verify bot status. Exiting...")
                return
            
            dp = Dispatcher(storage=RedisStorage(redis=redis_client))
            logger.info("Dispatcher initialized")
            
            # Register middlewares
            dp.message.middleware(GlobalErrorHandler())
            dp.message.middleware(RateLimitMiddleware(redis_client))
            logger.info("Middlewares registered")
            
            # Include routers
            dp.include_router(start.router)
            dp.include_router(goals.router)
            dp.include_router(checklist.router)
            dp.include_router(mood.router)
            dp.include_router(progress.router)
            dp.include_router(reports.router)
            dp.include_router(settings_handler.router)
            logger.info("Routers included")
            
            # Replace simple health check with full health check
            # Remove the old route first
            routes_to_remove = []
            for route in app.router.routes():
                if str(route.resource.canonical) == '/health':
                    routes_to_remove.append(route)
                    logger.info("Found health check route to remove")
                    
            # Remove routes outside the loop
            for route in routes_to_remove:
                app.router._resources.remove(route.resource)
                logger.info("Removed health check route")
                    
            setup_health_check(app, bot)
            logger.info("Full health check setup completed")
            
            # Start keep-alive service
            keep_alive_task = asyncio.create_task(start_keep_alive())
            logger.info("Keep-alive service started")
            
            # Start polling
            logger.info("Starting bot polling...")
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
            
        except Exception as e:
            logger.error(
                "Error during initialization",
                error=str(e),
                error_type=type(e).__name__,
                traceback=traceback.format_exc()
            )
            raise
            
    except Exception as e:
        logger.error(
            "Fatal error in main",
            error=str(e),
            error_type=type(e).__name__,
            traceback=traceback.format_exc()
        )
        return
        
    finally:
        # Cancel keep-alive task if it exists
        if keep_alive_task is not None:
            keep_alive_task.cancel()
            try:
                await keep_alive_task
            except asyncio.CancelledError:
                pass
        
        # Stop web server if it exists
        if runner is not None:
            await runner.cleanup()
            logger.info("Web server stopped")
        
        # Shutdown if components are initialized
        if all([dp, bot, redis_client]):
            await on_shutdown(dp, bot, redis_client)
        else:
            logger.warning(
                "Some components were not initialized, skipping full shutdown",
                dispatcher=bool(dp),
                bot=bool(bot),
                redis=bool(redis_client)
            )

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
