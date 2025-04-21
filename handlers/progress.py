from aiogram import Bot, Router, F
from aiogram.types import Message
from services.storage import TaskStorage, GoalStorage
from config import settings
from datetime import datetime, timedelta
from collections import defaultdict

router = Router()
task_storage = TaskStorage()
goal_storage = GoalStorage()

@router.message(lambda msg: msg.text == "📈 Прогресс")
async def handle_progress(message: Message):
    await send_text_progress(message.bot)

# ---------- 📅 Отчёт по сегодняшним задачам и целям ----------

async def send_checklist_report(bot: Bot):
    tasks = task_storage.get_tasks()
    incomplete = [t for t in tasks if not t.get("completed") and not t.get("done")]
    
    if not incomplete:
        await bot.send_message(
            chat_id=settings.USER_ID,
            text="✅ Все задачи на сегодня выполнены!"
        )
        return

    text = "📝 Невыполненные задачи на сегодня:\n\n"
    text += "\n".join([f"🔲 {t['text']}" for t in incomplete])

    await bot.send_message(settings.USER_ID, text)

async def send_goals_report(bot: Bot):
    goals = goal_storage.get_goals()
    active = [g for g in goals if not g.get("completed")]

    if active:
        text = "🎯 Актуальные цели:\n\n"
        text += "\n".join([f"📌 {g['text']} ({g.get('priority', 'средний')})" for g in active])
    else:
        text = "🎉 Все цели достигнуты! Пора ставить новые 🚀"

    await bot.send_message(settings.USER_ID, text)

# ---------- 📈 Прогресс по команде "📈 Прогресс" ----------

async def send_text_progress(bot: Bot):
    tasks = task_storage.get_tasks()
    goals = goal_storage.get_goals()

    total_tasks = len(tasks)
    done_tasks = sum(1 for t in tasks if t.get("completed"))

    total_goals = len(goals)
    done_goals = sum(1 for g in goals if g.get("completed"))

    task_percent = int((done_tasks / total_tasks) * 100) if total_tasks else 0
    goal_percent = int((done_goals / total_goals) * 100) if total_goals else 0

    text = "📊 Прогресс за сегодня:\n\n"
    text += f"✅ Задачи: {done_tasks} из {total_tasks} ({task_percent}%)\n"
    text += f"🎯 Цели: {done_goals} из {total_goals} ({goal_percent}%)\n"

    if task_percent == 100 and goal_percent == 100:
        text += "\n🌟 Ты справился на 100%! Великолепно!"
    elif task_percent >= 70 or goal_percent >= 70:
        text += "\n🚀 Отличный прогресс! Продолжай!"
    elif task_percent == 0 and goal_percent == 0:
        text += "\n😴 Пора включиться! Ты всё успеешь!"
    else:
        text += "\n📈 Двигаемся вперёд! Каждый шаг важен."

    await bot.send_message(settings.USER_ID, text)

# ---------- 📊 Воскресный анализ недели ----------

def get_last_7_dates():
    today = datetime.today().date()
    return [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]

async def analyze_weekly_productivity(bot: Bot):
    """Отправляет еженедельный анализ продуктивности."""
    # В реальном приложении здесь нужно:
    # 1. Получить список пользователей
    # 2. Для каждого пользователя проанализировать:
    #    - Выполненные задачи
    #    - Достигнутые цели
    #    - Среднее настроение
    # 3. Сформировать персонализированный отчет
    # await bot.send_message(
    #     chat_id=user_id,
    #     text="📈 Анализ продуктивности за неделю:\n\n"
    #          "✅ Выполнено задач: X из Y\n"
    #          "🎯 Достигнуто целей: A из B\n"
    #          "😊 Среднее настроение: Z/5\n\n"
    #          "🌟 Ваш уровень продуктивности: 80%\n"
    #          "💪 Продолжайте в том же духе!"
    # )
    pass

@router.message(F.text == "📈 Прогресс")
async def show_progress(message: Message):
    await message.answer(
        "📊 Ваша статистика:\n\n"
        "За сегодня:\n"
        "✅ Выполнено задач: 0 из 0\n"
        "😊 Настроение: Нет данных\n\n"
        "За неделю:\n"
        "🎯 Достигнуто целей: 0 из 0\n"
        "📈 Средняя продуктивность: 0%"
    )
