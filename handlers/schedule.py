from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from states.schedule_states import ScheduleEdit
from services.storage import schedule_storage, ValidationError
from datetime import datetime
import re
import random
import logging

router = Router()
quotes = [
    "Самая длинная дорога начинается с первого шага. — Лао-цзы",
    "Успех — это способность идти от неудачи к неудаче, не теряя энтузиазма. — Уинстон Черчилль",
    "Единственный способ делать великую работу — любить то, что вы делаете. — Стив Джобс",
    "Никогда не поздно быть тем, кем ты мог бы быть. — Джордж Элиот",
    "Будущее принадлежит тем, кто верит в красоту своей мечты. — Элеонора Рузвельт"
]

def generate_schedule_keyboard(schedule, show_controls=True):
    keyboard = []
    
    # Добавляем кнопки управления
    if show_controls:
        keyboard.append([
            InlineKeyboardButton(text="➕ Добавить пункт", callback_data="schedule_add"),
            InlineKeyboardButton(text="🔄 Обновить", callback_data="schedule_refresh")
        ])
    
    # Добавляем пункты расписания
    sorted_schedule = schedule_storage.get_sorted_schedule()
    for i, entry in enumerate(sorted_schedule):
        time = entry.get("time", "00:00")
        task = entry.get("text", "")
        keyboard.extend([
            [InlineKeyboardButton(text=f"🕒 {time} — {task}", callback_data=f"view_schedule_{i}")],
            [
                InlineKeyboardButton(text="✏️ Текст", callback_data=f"edit_text_{i}"),
                InlineKeyboardButton(text="⏰ Время", callback_data=f"edit_time_{i}"),
                InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_schedule_{i}")
            ]
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def send_quote(bot: Bot):
    """Отправляет случайную мотивирующую цитату."""
    quote = random.choice(quotes)
    # В реальном приложении здесь нужно получить список пользователей из базы данных
    # и отправить каждому. Сейчас это заглушка
    # await bot.send_message(chat_id=user_id, text=f"🌟 Цитата дня:\n\n{quote}")
    pass

@router.message(F.text == "📅 Расписание")
async def show_schedule(message: Message):
    try:
        schedule = schedule_storage.get_schedule()
        if not schedule:
            await message.answer(
                "📅 Расписание пусто.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="➕ Добавить пункт", callback_data="schedule_add")
                ]])
            )
            return
        await message.answer("🗓️ Текущее расписание:", reply_markup=generate_schedule_keyboard(schedule))
    except Exception as e:
        await message.answer(f"❌ Произошла ошибка при загрузке расписания: {str(e)}")

@router.callback_query(F.data == "schedule_add")
async def add_schedule_entry(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ScheduleEdit.waiting_for_new_entry)
    await callback.message.answer("Введите время и описание в формате ЧЧ:ММ Описание\nНапример: 09:00 Утренняя планерка")
    await callback.answer()

@router.message(ScheduleEdit.waiting_for_new_entry)
async def process_new_entry(message: Message, state: FSMContext):
    try:
        text = message.text.strip()
        match = re.match(r'^(\d{1,2}:\d{2})\s+(.+)$', text)
        
        if not match:
            await message.answer("❌ Неверный формат. Используйте формат ЧЧ:ММ Описание\nНапример: 09:00 Утренняя планерка")
            return
        
        time, description = match.groups()
        schedule_storage.add_entry(time, description)
        schedule = schedule_storage.get_schedule()
        
        await message.answer("✅ Пункт добавлен в расписание", reply_markup=generate_schedule_keyboard(schedule))
        await state.clear()
    except ValidationError as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
    except Exception as e:
        await message.answer(f"❌ Произошла ошибка: {str(e)}")
    finally:
        await state.clear()

@router.callback_query(F.data.startswith("edit_text_"))
async def edit_schedule_text(callback: CallbackQuery, state: FSMContext):
    index = int(callback.data.split("_")[-1])
    await state.update_data(index=index)
    await state.set_state(ScheduleEdit.waiting_for_new_text)
    await callback.message.answer("✏️ Введите новый текст для этого пункта:")
    await callback.answer()

@router.callback_query(F.data.startswith("edit_time_"))
async def edit_schedule_time(callback: CallbackQuery, state: FSMContext):
    index = int(callback.data.split("_")[-1])
    await state.update_data(index=index)
    await state.set_state(ScheduleEdit.waiting_for_new_time)
    await callback.message.answer("⏰ Введите новое время в формате ЧЧ:ММ (например, 09:00):")
    await callback.answer()

@router.message(ScheduleEdit.waiting_for_new_text)
async def receive_schedule_text_update(message: Message, state: FSMContext):
    try:
        new_text = message.text.strip()
        data = await state.get_data()
        index = data["index"]
        
        schedule_storage.update_entry_text(index, new_text)
        schedule = schedule_storage.get_schedule()
        
        await message.answer("✅ Текст обновлен", reply_markup=generate_schedule_keyboard(schedule))
        await state.clear()
    except ValidationError as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
    except Exception as e:
        await message.answer(f"❌ Произошла ошибка: {str(e)}")
    finally:
        await state.clear()

@router.message(ScheduleEdit.waiting_for_new_time)
async def receive_schedule_time_update(message: Message, state: FSMContext):
    try:
        new_time = message.text.strip()
        data = await state.get_data()
        index = data["index"]
        
        schedule_storage.update_entry_time(index, new_time)
        schedule = schedule_storage.get_schedule()
        
        await message.answer("✅ Время обновлено", reply_markup=generate_schedule_keyboard(schedule))
        await state.clear()
    except ValidationError as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
    except Exception as e:
        await message.answer(f"❌ Произошла ошибка: {str(e)}")
    finally:
        await state.clear()

@router.callback_query(F.data.startswith("delete_schedule_"))
async def delete_schedule_entry(callback: CallbackQuery):
    try:
        index = int(callback.data.split("_")[-1])
        deleted = schedule_storage.delete_entry(index)
        schedule = schedule_storage.get_schedule()
        
        await callback.message.edit_reply_markup(reply_markup=generate_schedule_keyboard(schedule))
        await callback.answer(f"🗑️ Удалено: {deleted['time']} — {deleted['text']}")
    except ValidationError as e:
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ Произошла ошибка: {str(e)}", show_alert=True)

@router.callback_query(F.data == "schedule_refresh")
async def refresh_schedule(callback: CallbackQuery):
    try:
        schedule = schedule_storage.get_schedule()
        await callback.message.edit_reply_markup(reply_markup=generate_schedule_keyboard(schedule))
        await callback.answer("🔄 Расписание обновлено")
    except Exception as e:
        await callback.answer(f"❌ Произошла ошибка: {str(e)}", show_alert=True)

@router.callback_query(F.data.startswith("view_schedule_"))
async def view_schedule_entry(callback: CallbackQuery):
    try:
        index = int(callback.data.split("_")[-1])
        schedule = schedule_storage.get_schedule()
        
        if 0 <= index < len(schedule):
            entry = schedule[index]
            await callback.answer(
                f"🕒 {entry['time']}\n📝 {entry['text']}",
                show_alert=True
            )
        else:
            await callback.answer("❌ Ошибка: неправильный индекс", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ Произошла ошибка: {str(e)}", show_alert=True)

@router.callback_query(F.data.startswith("delete_schedule:"))
async def delete_schedule_entry(callback: CallbackQuery, state: FSMContext):
    """Delete a schedule entry."""
    try:
        entry_idx = int(callback.data.split(":")[1])
        schedule = schedule_storage.get_schedule()
        
        if not 0 <= entry_idx < len(schedule):
            await callback.answer("Ошибка: запись не найдена", show_alert=True)
            return
            
        schedule_storage.delete_entry(entry_idx)
        
        # Получаем обновленное расписание и генерируем новую клавиатуру
        updated_schedule = schedule_storage.get_schedule()
        keyboard, message_text = generate_schedule_keyboard(updated_schedule)
        
        await callback.message.edit_text(text=message_text, reply_markup=keyboard)
        await callback.answer("Запись удалена")
    except Exception as e:
        logger.error(f"Error in delete_schedule_entry: {str(e)}")
        await callback.answer("Произошла ошибка при удалении записи", show_alert=True)

@router.callback_query(F.data.startswith("edit_schedule:"))
async def start_edit_schedule(callback: CallbackQuery, state: FSMContext):
    """Start editing a schedule entry."""
    try:
        entry_idx = int(callback.data.split(":")[1])
        schedule = schedule_storage.get_schedule()
        
        if not 0 <= entry_idx < len(schedule):
            await callback.answer("Ошибка: запись не найдена", show_alert=True)
            return
            
        entry = schedule[entry_idx]
        await state.update_data(editing_entry_idx=entry_idx)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Изменить текст", callback_data=f"edit_schedule_text:{entry_idx}"),
                InlineKeyboardButton(text="⏰ Изменить время", callback_data=f"edit_schedule_time:{entry_idx}")
            ],
            [
                InlineKeyboardButton(text="❌ Отмена", callback_data="show_schedule")
            ]
        ])
        
        await callback.message.edit_text(
            text=f"Редактирование записи:\n{entry['time']} - {entry['text']}",
            reply_markup=keyboard
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in start_edit_schedule: {str(e)}")
        await callback.answer("Произошла ошибка при начале редактирования", show_alert=True)

@router.callback_query(F.data == "show_schedule")
async def show_schedule(callback: CallbackQuery, state: FSMContext):
    """Show the schedule."""
    try:
        schedule = schedule_storage.get_schedule()
        keyboard, message_text = generate_schedule_keyboard(schedule)
        await callback.message.edit_text(text=message_text, reply_markup=keyboard)
        await callback.answer()
        await state.clear()
    except Exception as e:
        logger.error(f"Error in show_schedule: {str(e)}")
        await callback.answer("Произошла ошибка при отображении расписания", show_alert=True)

@router.callback_query(F.data.startswith("schedule_sort:"))
async def sort_schedule(callback: CallbackQuery):
    """Sort schedule entries based on selected criteria."""
    try:
        sort_type = callback.data.split(":")[1]
        schedule = schedule_storage.get_schedule()
        
        if sort_type == "time":
            schedule.sort(key=lambda x: x.get("time", "00:00"))
        elif sort_type == "date":
            schedule.sort(key=lambda x: x.get("created_at", ""))
        
        schedule_storage.save_data(schedule)
        keyboard, message_text = generate_schedule_keyboard(schedule)
        await callback.message.edit_text(text=message_text, reply_markup=keyboard)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in sort_schedule: {str(e)}")
        await callback.answer("Произошла ошибка при сортировке расписания", show_alert=True)
