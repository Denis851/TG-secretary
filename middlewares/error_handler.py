from aiogram.types import Update
from aiogram.exceptions import TelegramAPIError
from aiogram import BaseMiddleware
import logging

class GlobalErrorHandler(BaseMiddleware):
    async def __call__(self, handler, event: Update, data: dict):
        try:
            return await handler(event, data)
        except TelegramAPIError as e:
            logging.error(f"Telegram API Error: {e}")
            if hasattr(event, "message"):
                await event.message.answer("⚠️ Произошла ошибка при работе с Telegram.")
        except Exception as e:
            logging.exception("Unexpected error:")
            if hasattr(event, "message"):
                await event.message.answer("⚠️ Что-то пошло не так. Попробуй ещё раз.")
