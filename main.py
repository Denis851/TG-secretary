import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from config import BOT_TOKEN
from handlers import checklist, goals, start, progress, mood, schedule, settings, reports
from services.scheduler import setup_scheduled_jobs
from aiogram.types import Message
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from keyboards.main import get_main_keyboard
import os
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(level=logging.INFO)

load_dotenv()

async def main():
    # Инициализация бота и диспетчера
    bot = Bot(token=os.getenv('BOT_TOKEN'), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    
    # Delete webhook before polling
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

    # Планировщик задач (утренние/вечерние уведомления)
    setup_scheduled_jobs(bot)

    scheduler = AsyncIOScheduler()
    
    # Отправка цитаты каждый день в 9:00
    scheduler.add_job(schedule.send_quote, 'cron', hour=9, minute=0, args=[bot])
    
    # Запрос настроения каждый день в 20:00
    scheduler.add_job(mood.ask_mood, 'cron', hour=20, minute=0, args=[bot])
    
    # Отчет по чеклисту каждый день в 21:00
    scheduler.add_job(checklist.send_checklist_report, 'cron', hour=21, minute=0, args=[bot])
    
    # Отчет по целям каждую неделю в воскресенье в 18:00
    scheduler.add_job(goals.send_goals_report, 'cron', day_of_week='sun', hour=18, minute=0, args=[bot])
    
    # Анализ продуктивности за неделю каждое воскресенье в 19:00
    scheduler.add_job(progress.analyze_weekly_productivity, 'cron', day_of_week='sun', hour=19, minute=0, args=[bot])
    
    scheduler.start()

    # Запуск polling
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен вручную.")
