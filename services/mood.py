from aiogram import Bot
from datetime import datetime
from services.storage import load_json
from config import USER_ID

MOOD_PATH = "data/mood.json"

async def ask_mood(bot: Bot):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="😄 Отлично", callback_data="mood:great")],
        [InlineKeyboardButton(text="🙂 Нормально", callback_data="mood:ok")],
        [InlineKeyboardButton(text="😞 Устал", callback_data="mood:tired")]
    ])
    await bot.send_message(USER_ID, "Как ты себя чувствуешь сейчас?", reply_markup=keyboard)


async def analyze_daily_mood(bot: Bot):
    moods = load_json(MOOD_PATH)
    today = datetime.now().strftime("%Y-%m-%d")

    # Фильтруем по дате
    today_moods = [m for m in moods if m["time"].startswith(today)]

    if not today_moods:
        await bot.send_message(USER_ID, "📊 Сегодня ты не отмечал настроение.")
        return

    count = {"great": 0, "ok": 0, "tired": 0}
    for m in today_moods:
        count[m["mood"]] += 1

    total = sum(count.values())
    report = f"📊 Настроение за {today}:\n"
    report += f"😄 Отлично: {count['great']}\n"
    report += f"🙂 Нормально: {count['ok']}\n"
    report += f"😞 Устал: {count['tired']}\n"

    # Выгорание-предупреждение
    if count['tired'] > (total // 2):
        report += "\n⚠️ Сегодня ты чаще чувствовал усталость. Обрати внимание на отдых!"

    await bot.send_message(USER_ID, report)
