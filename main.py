import asyncio
import logging
import signal
import os
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis import asyncio as aioredis
from redis.exceptions import ConnectionError, AuthenticationError
from aiohttp import web
from handlers import checklist, goals, start, progress, mood, schedule, settings, reports
from services.scheduler import setup_jobs
from services.keep_alive import KeepAliveService
from middlewares.rate_limit import RateLimitMiddleware
from middlewares.error_handler import GlobalErrorHandler
from health import setup_health_check
from config import settings, clean_template_var
import structlog
from urllib.parse import urlparse

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

async def on_shutdown(dispatcher: Dispatcher, bot: Bot):
    """Действия при завершении работы бота"""
    logger.info("shutting_down")
    
    # Остановка keep-alive сервиса
    if keep_alive:
        await keep_alive.stop()
    
    # Остановка планировщика
    if scheduler:
        scheduler.shutdown()
    
    # Закрытие сессии бота
    if bot and hasattr(bot, 'session'):
        await bot.session.close()
    
    # Закрытие Redis соединения
    if redis:
        await redis.close()
    
    logger.info("shutdown_complete")

def signal_handler(signum, frame):
    """Обработчик сигналов завершения"""
    logger.info("received_signal", signal=signum)
    if dp and bot:
        asyncio.create_task(on_shutdown(dp, bot))

async def setup_redis():
    """Настройка Redis с повторными попытками"""
    max_retries = 5
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            # Get Redis URL from environment
            redis_url = settings.redis_url
            logger.info(
                "connecting_to_redis",
                attempt=attempt + 1,
                max_retries=max_retries,
                url=redis_url,
                environment=os.getenv('RAILWAY_ENVIRONMENT', 'development')
            )
            
            # Validate Redis URL
            try:
                parsed = urlparse(redis_url)
                if not parsed.scheme or not parsed.hostname:
                    raise ValueError("Invalid Redis URL format")
                
                # Check if port is valid
                if parsed.port is not None:
                    try:
                        int(parsed.port)
                    except ValueError:
                        raise ValueError(f"Invalid port in Redis URL: {parsed.port}")
            except ValueError as e:
                logger.error("invalid_redis_url", error=str(e), url=redis_url)
                raise
            
            # Create Redis connection with additional options
            redis = aioredis.from_url(
                redis_url,
                decode_responses=True,
                retry_on_timeout=True,
                health_check_interval=30,
                socket_timeout=5.0,
                socket_connect_timeout=5.0,
                retry_on_error=[ConnectionError, AuthenticationError],
                encoding='utf-8'
            )
            
            # Test connection with timeout
            try:
                await asyncio.wait_for(redis.ping(), timeout=5.0)
                logger.info("redis_connection_established")
                return redis
            except asyncio.TimeoutError:
                raise ConnectionError("Redis connection timeout")
            except AuthenticationError as e:
                logger.error(
                    "redis_authentication_failed",
                    error=str(e),
                    url=redis_url,
                    attempt=attempt + 1
                )
                # In production, don't try different credentials
                if os.getenv('RAILWAY_ENVIRONMENT') == 'production':
                    raise
                # Try different authentication scenarios
                if attempt == 0:
                    # First try: try with Railway's default credentials
                    logger.info("retrying_with_railway_credentials")
                    settings.REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', 'redis')
                    settings.REDIS_USER = os.getenv('REDIS_USER', 'default')
                    continue
                elif attempt == 1:
                    # Second try: try without authentication
                    logger.info("retrying_without_authentication")
                    settings.REDIS_PASSWORD = None
                    settings.REDIS_USER = None
                    continue
                elif attempt == 2:
                    # Third try: try with default password only
                    logger.info("retrying_with_default_password")
                    settings.REDIS_PASSWORD = "redis"
                    settings.REDIS_USER = None
                    continue
                raise
            
        except (ConnectionError, ValueError, AuthenticationError) as e:
            if attempt < max_retries - 1:
                logger.warning(
                    "redis_connection_failed",
                    error=str(e),
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    retry_in=retry_delay,
                    url=redis_url
                )
                await asyncio.sleep(retry_delay)
            else:
                logger.error(
                    "redis_connection_failed_final",
                    error=str(e),
                    url=redis_url,
                    environment=os.getenv('RAILWAY_ENVIRONMENT', 'development')
                )
                raise

async def main():
    global bot, dp, scheduler, redis, keep_alive
    
    try:
        # Инициализация Redis с повторными попытками
        redis = await setup_redis()
        
        # Инициализация бота и диспетчера
        bot = Bot(
            token=settings.BOT_TOKEN,
            parse_mode=ParseMode.HTML
        )
        
        # Удаляем webhook с несколькими попытками
        max_retries = 3
        retry_delay = 5  # seconds
        
        for attempt in range(max_retries):
            try:
                logger.info("attempting_to_delete_webhook", attempt=attempt + 1, max_retries=max_retries)
                await bot.delete_webhook(drop_pending_updates=True)
                logger.info("webhook_deleted_successfully")
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning("webhook_deletion_failed", error=str(e), retry_in=retry_delay)
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error("webhook_deletion_failed_after_all_attempts", error=str(e))
                    raise
        
        # Инициализация диспетчера с Redis storage
        storage = RedisStorage(redis=redis)
        dp = Dispatcher(storage=storage)
        
        # Подключаем middleware
        dp.message.middleware(RateLimitMiddleware(redis))
        dp.callback_query.middleware(RateLimitMiddleware(redis))
        dp.message.middleware(GlobalErrorHandler())
        dp.callback_query.middleware(GlobalErrorHandler())

        # Подключаем handlers
        dp.include_router(start.router)
        dp.include_router(checklist.router)
        dp.include_router(goals.router)
        dp.include_router(progress.router)
        dp.include_router(schedule.router)
        dp.include_router(mood.router)
        dp.include_router(settings.router)
        dp.include_router(reports.router)

        # Инициализация планировщика задач
        scheduler = setup_jobs(bot)

        # Инициализация и запуск keep-alive сервиса
        keep_alive = KeepAliveService(bot)
        await keep_alive.start()

        # Установка обработчиков сигналов
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Создание и настройка web приложения для health check
        app = web.Application()
        setup_health_check(app, bot)
        
        # Запуск web сервера в отдельной задаче
        runner = web.AppRunner(app)
        await runner.setup()
        port = int(os.getenv('PORT', 8080))
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()

        # Запуск polling
        logger.info("bot_started")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error("bot_startup_error", error=str(e))
        raise
    finally:
        await on_shutdown(dp, bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("bot_stopped")
