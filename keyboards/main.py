from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton(text="📅 Расписание"),
            KeyboardButton(text="✅ Чеклист")
        ],
        [
            KeyboardButton(text="🎯 Цели"),
            KeyboardButton(text="📈 Прогресс")
        ],
        [
            KeyboardButton(text="😊 Настроение"),
            KeyboardButton(text="📊 Отчет")
        ]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Выберите действие"
    ) 