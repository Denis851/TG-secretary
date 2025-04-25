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
    last_error = None
    
    for attempt in range(max_retries):
        try:
            # Get Redis URL from environment
            redis_url = settings.redis_url
            # Mask password in logs
            masked_url = redis_url
            parsed = urlparse(redis_url)
            if parsed.password:
                masked_url = masked_url.replace(parsed.password, '***')
            
            logger.info(
                "connecting_to_redis",
                attempt=attempt + 1,
                max_retries=max_retries,
                url=masked_url,
                host=parsed.hostname,
                port=parsed.port,
                environment=os.getenv('RAILWAY_ENVIRONMENT', 'development')
            )
            
            # Create Redis connection with additional options
            redis = aioredis.from_url(
                redis_url,
                decode_responses=True,
                retry_on_timeout=True,
                health_check_interval=30,
                socket_timeout=10.0,
                socket_connect_timeout=10.0,
                retry_on_error=[ConnectionError, AuthenticationError],
                encoding='utf-8',
                max_connections=10,
                username='default'  # Explicitly set username
            )
            
            # Test connection with timeout
            try:
                await asyncio.wait_for(redis.ping(), timeout=10.0)
                logger.info(
                    "redis_connection_established",
                    url=masked_url,
                    host=parsed.hostname,
                    port=parsed.port
                )
                return redis
            except asyncio.TimeoutError:
                last_error = "Redis connection timeout"
                logger.error(
                    "redis_connection_timeout",
                    url=masked_url,
                    host=parsed.hostname,
                    port=parsed.port
                )
                raise ConnectionError(last_error)
            except AuthenticationError as e:
                last_error = str(e)
                logger.error(
                    "redis_authentication_failed",
                    error=last_error,
                    url=masked_url,
                    host=parsed.hostname,
                    port=parsed.port,
                    attempt=attempt + 1,
                    redis_password_set=bool(os.getenv('REDIS_PASSWORD')),
                    redis_url_set=bool(os.getenv('REDIS_URL'))
                )
                raise
            
        except (ConnectionError, ValueError, AuthenticationError) as e:
            last_error = str(e)
            if attempt < max_retries - 1:
                logger.warning(
                    "redis_connection_failed",
                    error=last_error,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    retry_in=retry_delay,
                    url=masked_url,
                    host=parsed.hostname,
                    port=parsed.port,
                    redis_password_set=bool(os.getenv('REDIS_PASSWORD')),
                    redis_url_set=bool(os.getenv('REDIS_URL'))
                )
                await asyncio.sleep(retry_delay)
            else:
                logger.error(
                    "redis_connection_failed_final",
                    error=last_error,
                    url=masked_url,
                    host=parsed.hostname,
                    port=parsed.port,
                    environment=os.getenv('RAILWAY_ENVIRONMENT', 'development'),
                    redis_password_set=bool(os.getenv('REDIS_PASSWORD')),
                    redis_url_set=bool(os.getenv('REDIS_URL'))
                )
                raise Exception(f"Failed to connect to Redis after {max_retries} attempts. Last error: {last_error}")

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
