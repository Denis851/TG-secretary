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

# Настройка структурированного логирования
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()

# Глобальные переменные для корректного завершения
bot = None
dp = None
scheduler = None
redis = None
keep_alive = None

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
    try:
        redis_client = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            encoding='utf-8',
            decode_responses=True,
            retry=Retry(
                ExponentialBackoff(),
                3,
                retry_on_error=[ConnectionError, TimeoutError]
            )
        )
        await redis_client.ping()
        logger.info("Successfully connected to Redis")
        return redis_client
    except Exception as e:
        logger.error("Failed to connect to Redis", error=str(e))
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
    # Initialize structlog
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ]
    )
    
    # Setup Redis with retries
    redis_client = await setup_redis()
    if not redis_client:
        logger.error("Could not establish Redis connection. Exiting...")
        return

    # Initialize bot and dispatcher
    session = AiohttpSession()
    bot = Bot(token=settings.BOT_TOKEN, session=session)
    
    # Check for and terminate any duplicate instances
    if not await check_and_terminate_duplicate_instances(bot):
        logger.error("Failed to verify bot status. Exiting...")
        return
    
    dp = Dispatcher(storage=RedisStorage(redis=redis_client))
    
    # Register middlewares
    dp.message.middleware(ErrorHandler())
    dp.message.middleware(RateLimitMiddleware(redis_client))
    
    # Include routers
    dp.include_router(start.router)
    dp.include_router(goals.router)
    dp.include_router(checklist.router)
    dp.include_router(mood.router)
    dp.include_router(progress.router)
    dp.include_router(reports.router)
    dp.include_router(settings_handler.router)
    
    # Create web application
    app = web.Application()
    setup_health_check(app, bot)
    
    # Setup web server
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv('PORT', 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Web server started on port {port}")
    
    try:
        # Start keep-alive service
        keep_alive_task = asyncio.create_task(start_keep_alive())
        
        # Start polling
        logger.info("Starting bot polling...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except TelegramConflictError:
        logger.error("Another instance of the bot is already running")
    except Exception as e:
        logger.error("Error during bot execution", error=str(e))
    finally:
        # Cancel keep-alive task if it exists
        if 'keep_alive_task' in locals():
            keep_alive_task.cancel()
            try:
                await keep_alive_task
            except asyncio.CancelledError:
                pass
        
        # Stop web server
        await runner.cleanup()
        logger.info("Web server stopped")
        
        # Shutdown
        await on_shutdown(dp, bot, redis_client)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
