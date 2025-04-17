from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def checklist_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Мой список")],
            [KeyboardButton(text="➕ Добавить")],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )
