import asyncio
import logging
import signal
import os
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.client.session.middlewares import BaseMiddleware
from redis import asyncio as aioredis
from aiohttp import web
from handlers import checklist, goals, start, progress, mood, schedule, settings, reports
from services.scheduler import setup_jobs
from services.keep_alive import KeepAliveService
from middlewares.rate_limit import RateLimitMiddleware
from middlewares.error_handler import GlobalErrorHandler
from health import setup_health_check
from config import settings
import structlog

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
    await bot.session.close()
    
    # Закрытие Redis соединения
    if redis:
        await redis.close()
    
    logger.info("shutdown_complete")

def signal_handler(signum, frame):
    """Обработчик сигналов завершения"""
    logger.info("received_signal", signal=signum)
    asyncio.create_task(on_shutdown(dp, bot))

async def setup_redis():
    """Настройка Redis с повторными попытками"""
    max_retries = 5
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            redis = aioredis.from_url(settings.REDIS_URL)
            await redis.ping()
            logger.info("redis_connection_established")
            return redis
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning("redis_connection_failed", error=str(e), retry_in=retry_delay)
                await asyncio.sleep(retry_delay)
            else:
                logger.error("redis_connection_failed_after_all_attempts", error=str(e))
                raise

async def main():
    global bot, dp, scheduler, redis, keep_alive
    
    try:
        # Инициализация Redis с повторными попытками
        redis = await setup_redis()
        
        # Инициализация бота и диспетчера
        bot = Bot(
            token=settings.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
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
