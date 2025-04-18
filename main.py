import asyncio
import logging
import signal
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from handlers import checklist, goals, start, progress, mood, schedule, settings, reports
from services.scheduler import setup_jobs
from aiogram.types import Message
from aiogram.filters import Command
from keyboards.main import get_main_keyboard
import os
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# Глобальные переменные для корректного завершения
bot = None
dp = None
scheduler = None

async def on_shutdown(dispatcher: Dispatcher, bot: Bot):
    """Действия при завершении работы бота"""
    logger.info("Shutting down...")
    
    # Остановка планировщика
    if scheduler:
        scheduler.shutdown()
    
    # Закрытие сессии бота
    await bot.session.close()
    
    logger.info("Bye!")

def signal_handler(signum, frame):
    """Обработчик сигналов завершения"""
    logger.info(f"Received signal {signum}")
    asyncio.create_task(on_shutdown(dp, bot))

async def main():
    global bot, dp, scheduler
    
    # Проверка наличия токена
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        raise ValueError("BOT_TOKEN не найден в переменных окружения")

    # Инициализация бота и диспетчера
    bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    
    try:
        # Удаляем webhook и ждем завершения операции
        await bot.delete_webhook(drop_pending_updates=True)
        
        dp = Dispatcher(storage=MemoryStorage())

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

        # Установка обработчиков сигналов
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Запуск polling
        logger.info("Бот запущен")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        raise
    finally:
        await on_shutdown(dp, bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped!")
