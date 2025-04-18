from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from services.storage import mood_storage
from datetime import datetime

router = Router()

MOOD_EMOJIS = {
    "5": "😊",
    "4": "🙂",
    "3": "😐",
    "2": "🙁",
    "1": "😢"
}

def generate_mood_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="😊 5", callback_data="mood_5"),
            InlineKeyboardButton(text="🙂 4", callback_data="mood_4"),
            InlineKeyboardButton(text="😐 3", callback_data="mood_3"),
            InlineKeyboardButton(text="🙁 2", callback_data="mood_2"),
            InlineKeyboardButton(text="😢 1", callback_data="mood_1"),
        ]
    ])

async def ask_mood(bot: Bot):
    """Отправляет запрос на оценку настроения."""
    keyboard = generate_mood_keyboard()
    # В реальном приложении здесь нужно получить список пользователей из базы данных
    # await bot.send_message(chat_id=user_id, text="Как ваше настроение сегодня?", reply_markup=keyboard)
    pass

@router.message(F.text == "😊 Настроение")
async def show_mood(message: Message):
    keyboard = generate_mood_keyboard()
    await message.answer("Как ваше настроение сейчас?", reply_markup=keyboard)

@router.callback_query(F.data.startswith("mood_"))
async def process_mood(callback: CallbackQuery):
    try:
        mood_value = int(callback.data.split("_")[1])  # Convert to integer
        if mood_value not in range(1, 6):  # Check range 1-5
            await callback.answer("❌ Некорректное значение настроения", show_alert=True)
            return
            
        # Сохраняем настроение
        mood_storage.add_mood(mood_value)
        
        await callback.message.edit_reply_markup()
        await callback.message.answer(f"Записал ваше настроение: {MOOD_EMOJIS[str(mood_value)]}")
        await callback.answer()
        
    except Exception as e:
        await callback.answer(f"❌ Произошла ошибка при сохранении настроения: {str(e)}", show_alert=True) 