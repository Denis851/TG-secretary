from aiogram import Bot
from config import settings
import random

QUOTES = [
    "✨ Утро — это шанс начать всё сначала.",
    "🚀 Ты можешь больше, чем думаешь.",
    "🔥 Сегодня лучший день, чтобы стать лучше.",
    "💡 Всё, что нужно — уже внутри тебя."
]

async def send_quote(bot: Bot):
    quote = random.choice(QUOTES)
    await bot.send_message(settings.USER_ID, f"Доброе утро! ☀️\n\n{quote}")
