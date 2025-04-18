from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from datetime import time
from pytz import timezone
from handlers.progress import send_checklist_report, send_goals_report, analyze_weekly_productivity
from handlers.mood import ask_mood
from services.quote import send_quote

tz = timezone("Europe/Moscow")  # Или твой часовой пояс

def setup_jobs(bot: Bot) -> AsyncIOScheduler:
    """Setup all scheduled jobs and return the scheduler instance"""
    scheduler = AsyncIOScheduler(timezone=tz)
    
    # Утреннее вдохновение
    scheduler.add_job(send_quote, trigger='cron', hour=6, minute=0, args=[bot])

    # Настроение 3 раза в день
    for hour in [9, 14, 20]:
        scheduler.add_job(ask_mood, trigger='cron', hour=hour, minute=0, args=[bot])

    # Ежедневный чеклист
    scheduler.add_job(send_checklist_report, trigger='cron', hour=21, minute=30, args=[bot])

    # Еженедельный отчёт по целям
    scheduler.add_job(send_goals_report, trigger='cron', day_of_week='sun', hour=21, minute=0, args=[bot])
    scheduler.add_job(analyze_weekly_productivity, trigger='cron', day_of_week='sun', hour=21, minute=15, args=[bot])

    # Запуск планировщика
    scheduler.start()
    
    return scheduler

__all__ = ['scheduler', 'setup_jobs']
