from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Расписание"), KeyboardButton(text="✅ Чеклист")],
            [KeyboardButton(text="🎯 Цели"), KeyboardButton(text="📈 Прогресс")],
            [KeyboardButton(text="😃 Настроение"), KeyboardButton(text="📝 Редактировать")]
        ],
        resize_keyboard=True
    )