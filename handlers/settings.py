from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from handlers.reports import generate_and_send_report
import os

router = Router()

@router.message(F.text == "📝 Редактировать")
async def show_settings(message: Message):
    """Show settings menu with inline keyboard."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏰ Расписание", callback_data="edit_schedule")],
        [InlineKeyboardButton(text="✅ Задачи", callback_data="edit_tasks")],
        [InlineKeyboardButton(text="🎯 Цели", callback_data="edit_goals")],
        [InlineKeyboardButton(text="🔔 Уведомления", callback_data="edit_notifications")],
        [InlineKeyboardButton(text="📊 Отчет", callback_data="generate_report")]
    ])
    
    await message.answer(
        "Выберите, что хотите отредактировать:",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "generate_report")
async def handle_report_generation(callback: CallbackQuery):
    """Handle report generation button press."""
    try:
        await callback.answer("⏳ Генерирую отчет...")
        await generate_and_send_report(callback.message, callback.from_user.id)
    finally:
        # Remove the inline keyboard
        await callback.message.edit_reply_markup(reply_markup=None)