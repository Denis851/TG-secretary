from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from states.add_task import AddTask
from services.storage import task_storage, ValidationError, StorageError
from keyboards.checklist import ChecklistKeyboard
from datetime import datetime, timedelta
from typing import List, Dict, Any
from services.config import Config
from services.checklist_storage import ChecklistStorage
from log import logger

router = Router()
checklist_keyboard = ChecklistKeyboard()

# Визуальные иконки приоритета
PRIORITY_ICONS = {
    "высокий": "🔥",
    "средний": "⚖️",
    "низкий": "💤"
}

DEADLINE_PRESETS = {
    "today": "Сегодня",
    "tomorrow": "Завтра",
    "week": "Через неделю",
    "no_deadline": "Без дедлайна"
}

def format_deadline(deadline: str) -> str:
    """Форматирует дедлайн для отображения"""
    if not deadline:
        return ""
    try:
        date = datetime.strptime(deadline, "%Y-%m-%d").date()
        today = datetime.now().date()
        delta = date - today
        
        if delta.days == 0:
            return "⏰ Сегодня"
        elif delta.days == 1:
            return "⏰ Завтра"
        elif delta.days < 0:
            return f"⚠️ Просрочено ({date.strftime('%d.%m')})"
        elif delta.days < 7:
            return f"⏰ Через {delta.days} дн."
        else:
            return f"📅 {date.strftime('%d.%m')}"
    except ValueError:
        return ""

def generate_sort_buttons() -> List[List[InlineKeyboardButton]]:
    """Генерирует кнопки для сортировки"""
    return [
        [
            InlineKeyboardButton(text="🔥 По приоритету", callback_data="sort_tasks:priority"),
            InlineKeyboardButton(text="✅ По статусу", callback_data="sort_tasks:status")
        ],
        [
            InlineKeyboardButton(text="⏰ По дедлайну", callback_data="sort_tasks:deadline"),
            InlineKeyboardButton(text="📅 По дате создания", callback_data="sort_tasks:date")
        ],
        [
            InlineKeyboardButton(text="↕️ Изменить порядок", callback_data="sort_tasks:reverse")
        ]
    ]

def generate_checklist_inline_keyboard(data: List[Dict[str, Any]], show_sort: bool = False) -> InlineKeyboardMarkup:
    """Генерирует клавиатуру для чеклиста"""
    buttons = []
    
    # Добавляем кнопки сортировки, если нужно
    if show_sort and data:
        buttons.extend(generate_sort_buttons())
        buttons.append([InlineKeyboardButton(text="⬅️ Скрыть сортировку", callback_data="sort_tasks:hide")])
    elif data:
        buttons.append([InlineKeyboardButton(text="🔄 Сортировка", callback_data="sort_tasks:show")])
    
    # Добавляем задачи
    for i, item in enumerate(data):
        icon = PRIORITY_ICONS.get(item.get("priority", "средний").lower(), "⚖️")
        status = "✅" if item.get("completed", False) else "🔲"
        deadline_text = format_deadline(item.get("deadline"))
        task_text = f"{status} {icon} {item['text']}"
        if deadline_text:
            task_text += f" {deadline_text}"
            
        buttons.append([
            InlineKeyboardButton(text=task_text, callback_data=f"toggle_task:{i}"),
            InlineKeyboardButton(text="🗑️", callback_data=f"delete_task:{i}")
        ])
    
    buttons.append([InlineKeyboardButton(text="➕ Добавить задачу", callback_data="add_task")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.message(F.text == "✅ Чеклист")
async def show_checklist(message: Message):
    try:
        tasks = task_storage.get_tasks()
        keyboard = checklist_keyboard.get_checklist_keyboard(tasks)
        await message.answer(**keyboard)
    except StorageError as e:
        await message.answer(f"❌ Произошла ошибка при загрузке задач: {str(e)}")

@router.callback_query(F.data == "add_task")
async def start_add_task(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите текст новой задачи:")
    await state.set_state(AddTask.waiting_for_task_text)
    await callback.answer()

@router.callback_query(F.data.startswith("toggle_task:"))
async def toggle_task_status(callback: CallbackQuery):
    try:
        task_text = callback.data.split(":")[1]
        tasks = task_storage.get_tasks()
        
        for task in tasks:
            if task["text"] == task_text:
                task["completed"] = not task.get("completed", False)
                if task["completed"]:
                    task["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                else:
                    task.pop("completed_at", None)
                break
        
        task_storage.save_data(tasks)
        keyboard = checklist_keyboard.get_checklist_keyboard(tasks)
        await callback.message.edit_text(**keyboard)
        await callback.answer("✅ Статус задачи обновлён")
    except StorageError as e:
        await callback.answer(f"❌ Произошла ошибка: {str(e)}", show_alert=True)

@router.callback_query(F.data.startswith("delete_task:"))
async def delete_task(callback: CallbackQuery):
    try:
        task_text = callback.data.split(":")[1]
        tasks = task_storage.get_tasks()
        tasks = [task for task in tasks if task["text"] != task_text]
        task_storage.save_data(tasks)
        
        keyboard = checklist_keyboard.get_checklist_keyboard(tasks)
        await callback.message.edit_text(**keyboard)
        await callback.answer("🗑️ Задача удалена")
    except StorageError as e:
        await callback.answer(f"❌ Произошла ошибка: {str(e)}", show_alert=True)

@router.message(AddTask.waiting_for_task_text)
async def receive_task_text(message: Message, state: FSMContext):
    try:
        text = message.text.strip()
        task_storage.validate_text(text)
        
        task_storage.add_task(
            text=text,
            priority="средний"  # Default priority
        )
        
        tasks = task_storage.get_tasks()
        keyboard = checklist_keyboard.get_checklist_keyboard(tasks)
        await message.answer(**keyboard)
        await state.clear()
    except ValidationError as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
    except StorageError as e:
        await message.answer(f"❌ Произошла ошибка: {str(e)}")
    finally:
        await state.clear()

@router.callback_query(F.data.startswith("priority_"))
async def receive_priority(callback: CallbackQuery, state: FSMContext):
    try:
        priority = callback.data.split("_")[1]
        await state.update_data(priority=priority)
        await state.set_state(AddTask.waiting_for_deadline)
        
        # Текущая дата
        today = datetime.now().date()
        
        # Создаем кнопки с предустановленными датами
        buttons = [
            [{
                "text": "Сегодня",
                "callback_data": f"deadline_{today.strftime('%Y-%m-%d')}"
            }, {
                "text": "Завтра",
                "callback_data": f"deadline_{(today + timedelta(days=1)).strftime('%Y-%m-%d')}"
            }],
            [{
                "text": "Через неделю",
                "callback_data": f"deadline_{(today + timedelta(weeks=1)).strftime('%Y-%m-%d')}"
            }],
            [{
                "text": "Без дедлайна",
                "callback_data": "deadline_none"
            }]
        ]
        
        await callback.message.edit_text(
            "Выберите дедлайн для задачи:",
            reply_markup=ChecklistKeyboard.create_inline_keyboard(buttons)
        )
        
    except ValidationError as e:
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
        await state.clear()
    except Exception as e:
        await callback.answer("❌ Произошла неизвестная ошибка", show_alert=True)
        await state.clear()

@router.callback_query(F.data.startswith("deadline_"))
async def receive_deadline(callback: CallbackQuery, state: FSMContext):
    try:
        deadline = callback.data.split("_")[1]
        data = await state.get_data()
        text = data.get("text")
        priority = data.get("priority")
        
        # Если выбрано "без дедлайна", устанавливаем None
        if deadline == "none":
            deadline = None
            
        task_storage.add_task(
            text=text,
            priority=priority,
            deadline=deadline
        )
        
        # Получаем настройки сортировки
        sort_data = await state.get_data()
        current_sort = sort_data.get("current_sort", "priority")
        reverse_sort = sort_data.get("reverse_sort", False)
        show_sort = sort_data.get("show_sort", False)
        
        # Получаем отсортированный список задач
        tasks = task_storage.get_sorted_tasks(current_sort, reverse_sort)
        
        # Формируем текст подтверждения
        deadline_text = (
            f" (дедлайн: {ChecklistKeyboard.format_deadline(deadline)})" if deadline else ""
        )
        
        await callback.message.edit_text(
            f"✅ Добавлена задача: {text}{deadline_text}"
        )
        
        await callback.message.answer(
            "Ваши задачи:",
            reply_markup=ChecklistKeyboard.generate_checklist_keyboard(tasks, show_sort)
        )
        
    except ValidationError as e:
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
    except StorageError as e:
        await callback.answer(f"❌ Произошла ошибка: {str(e)}", show_alert=True)
    finally:
        await state.clear()

@router.callback_query(F.data.startswith("sort_tasks:"))
async def handle_sort_tasks(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split(":")[1]
    
    try:
        # Получаем текущие настройки сортировки из состояния
        sort_data = await state.get_data()
        current_sort = sort_data.get("current_sort", "priority")
        reverse_sort = sort_data.get("reverse_sort", False)
        show_sort = sort_data.get("show_sort", False)
        
        if action == "show":
            show_sort = True
        elif action == "hide":
            show_sort = False
        elif action == "reverse":
            reverse_sort = not reverse_sort
        else:
            current_sort = action
            
        # Сохраняем настройки сортировки
        await state.update_data(
            current_sort=current_sort,
            reverse_sort=reverse_sort,
            show_sort=show_sort
        )
        
        # Получаем отсортированный список задач
        tasks = task_storage.get_sorted_tasks(current_sort, reverse_sort)
        
        # Обновляем клавиатуру
        await callback.message.edit_reply_markup(
            reply_markup=ChecklistKeyboard.generate_checklist_keyboard(tasks, show_sort)
        )
        
        sort_names = {
            "priority": "приоритету",
            "status": "статусу",
            "deadline": "дедлайну",
            "date": "дате создания"
        }
        
        if action not in ["show", "hide"]:
            await callback.answer(
                f"Отсортировано по {sort_names.get(current_sort, current_sort)}"
                f"{' (обратный порядок)' if reverse_sort else ''}"
            )
        else:
            await callback.answer()
            
    except StorageError as e:
        await callback.answer(f"❌ Произошла ошибка: {str(e)}", show_alert=True)

async def send_checklist_report(bot: Bot):
    """Отправляет ежедневный отчет по выполненным задачам."""
    try:
        # Получаем хранилище задач
        storage = ChecklistStorage()
        tasks = storage.get_tasks()
        
        if not tasks:
            return  # Нет задач для отчета
            
        # Подсчитываем статистику
        completed_tasks = len([task for task in tasks if task.get('completed', False)])
        total_tasks = len(tasks)
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        # Формируем текст отчета
        report_text = (
            "📋 Отчет по задачам за день:\n\n"
            f"✅ Выполнено: {completed_tasks} из {total_tasks} задач\n"
            f"📊 Процент выполнения: {completion_rate:.1f}%\n\n"
            "🎯 Детали по задачам:\n"
        )
        
        # Добавляем список задач, сгруппированный по статусу
        completed_tasks_list = []
        pending_tasks_list = []
        
        for task in tasks:
            task_text = f"• {task['text']}"
            if task.get('priority'):
                priority_icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}
                task_text += f" {priority_icons.get(task['priority'], '')}"
            if task.get('deadline'):
                task_text += f" (до {task['deadline']})"
                
            if task.get('completed', False):
                completed_tasks_list.append(task_text)
            else:
                pending_tasks_list.append(task_text)
        
        if completed_tasks_list:
            report_text += "\nВыполненные задачи:\n" + "\n".join(completed_tasks_list)
        if pending_tasks_list:
            report_text += "\n\nОжидающие выполнения:\n" + "\n".join(pending_tasks_list)
            
        # Получаем ID пользователя из конфига
        config = Config()
        user_id = config.get_user_id()
        
        # Отправляем отчет
        await bot.send_message(
            chat_id=user_id,
            text=report_text
        )
        
    except Exception as e:
        logger.error(f"Error sending checklist report: {str(e)}")
