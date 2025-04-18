from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.storage import GoalStorage
from keyboards.goals import GoalsKeyboard
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json
import os
import re
from constants.icons import STATUS_ICONS, PRIORITY_ICONS, TIME_ICONS, ACTION_ICONS, NAVIGATION_ICONS
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

# Путь к файлу для хранения целей
GOALS_FILE = "data/goals.json"

# Создаем директорию data, если её нет
os.makedirs("data", exist_ok=True)

def load_goals() -> List[Dict[str, Any]]:
    """Загружает цели из файла"""
    try:
        if os.path.exists(GOALS_FILE):
            with open(GOALS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading goals: {e}")
    return []

def save_goals(goals: List[Dict[str, Any]]) -> None:
    """Сохраняет цели в файл"""
    try:
        with open(GOALS_FILE, 'w', encoding='utf-8') as f:
            json.dump(goals, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving goals: {e}")

router = Router()
goals_storage = GoalStorage()
goals_keyboard = GoalsKeyboard()

class GoalStates(StatesGroup):
    waiting_for_text = State()
    waiting_for_priority = State()
    waiting_for_deadline = State()
    editing_text = State()
    editing_priority = State()
    editing_deadline = State()

def format_deadline(deadline: str) -> str:
    """Форматирует дедлайн для отображения"""
    if not deadline:
        return ""
    try:
        date = datetime.strptime(deadline, "%Y-%m-%d").date()
        today = datetime.now().date()
        delta = date - today
        
        if delta.days == 0:
            return f"{TIME_ICONS['deadline']} Сегодня"
        elif delta.days == 1:
            return f"{TIME_ICONS['deadline']} Завтра"
        elif delta.days < 0:
            return f"{STATUS_ICONS['error']} Просрочено ({date.strftime('%d.%m')})"
        elif delta.days < 7:
            return f"{TIME_ICONS['deadline']} Через {delta.days} дн."
        else:
            return f"{TIME_ICONS['calendar']} {date.strftime('%d.%m')}"
    except ValueError:
        return ""

def format_goal_text(goal: Dict[str, Any], index: int) -> str:
    """Форматирует текст одной цели для отображения"""
    status = STATUS_ICONS['completed'] if goal.get("completed", False) else STATUS_ICONS['pending']
    priority = goal.get("priority", "medium").lower()
    priority_emoji = PRIORITY_ICONS.get(priority, PRIORITY_ICONS['medium'])
    deadline_text = format_deadline(goal.get("deadline", ""))
    
    text = f"{status} {index}. {goal['text']}"
    if priority != "medium":  # Показываем приоритет только если он не средний
        text += f" {priority_emoji}"
    if deadline_text:
        text += f" {deadline_text}"
    return text

def format_goal_button_text(goal: Dict[str, Any]) -> str:
    """Форматирует текст для кнопки цели"""
    status = STATUS_ICONS['completed'] if goal.get("completed", False) else STATUS_ICONS['pending']
    priority = goal.get("priority", "medium").lower()
    priority_emoji = PRIORITY_ICONS.get(priority, PRIORITY_ICONS['medium'])
    deadline_text = format_deadline(goal.get("deadline", ""))
    
    text = f"{status} {goal['text']}"
    if priority != "medium":
        text += f" {priority_emoji}"
    if deadline_text:
        text += f" | {deadline_text}"
    return text

def generate_goals_keyboard(goals: List[Dict[str, Any]], show_sort: bool = False) -> InlineKeyboardMarkup:
    """Генерирует клавиатуру для целей"""
    buttons = []
    
    # Добавляем кнопки сортировки
    if show_sort and goals:
        buttons.extend([
            [
                InlineKeyboardButton(text=f"{PRIORITY_ICONS['high']} По приоритету", callback_data="sort_goals:priority"),
                InlineKeyboardButton(text=f"{STATUS_ICONS['completed']} По статусу", callback_data="sort_goals:status")
            ],
            [
                InlineKeyboardButton(text=f"{TIME_ICONS['deadline']} По дедлайну", callback_data="sort_goals:deadline"),
                InlineKeyboardButton(text=f"{TIME_ICONS['calendar']} По дате", callback_data="sort_goals:date")
            ],
            [InlineKeyboardButton(text=f"{ACTION_ICONS['back']} Скрыть сортировку", callback_data="sort_goals:hide")]
        ])
    elif goals:
        buttons.append([InlineKeyboardButton(text=f"{NAVIGATION_ICONS['sort']} Сортировка", callback_data="sort_goals:show")])
    
    # Добавляем цели
    for i, goal in enumerate(goals):
        goal_text = format_goal_button_text(goal)
        buttons.append([
            InlineKeyboardButton(text=goal_text, callback_data=f"toggle_goal:{i}"),
            InlineKeyboardButton(text=ACTION_ICONS['delete'], callback_data=f"delete_goal:{i}")
        ])
    
    # Кнопка добавления цели
    buttons.append([InlineKeyboardButton(text=f"{ACTION_ICONS['add']} Добавить цель", callback_data="add_goal")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.message(F.text == "🎯 Цели")
async def show_goals_command(message: Message):
    """Handle the 'Goals' command."""
    try:
        goals = goals_storage.get_goals()
        keyboard = generate_goals_keyboard(goals)
        await message.answer(
            text="🎯 Ваши цели:",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error in show_goals_command: {str(e)}", exc_info=True)
        await message.answer("❌ Произошла ошибка при загрузке целей")

@router.callback_query(F.data == "show_goals")
async def show_goals(callback: CallbackQuery, state: FSMContext):
    """Show the list of goals."""
    try:
        goals = goals_storage.get_goals()
        keyboard, message_text = goals_keyboard.generate_goals_keyboard(goals)
        await callback.message.edit_text(text=message_text, reply_markup=keyboard)
        await callback.answer()
        await state.clear()
    except Exception as e:
        logger.error(f"Error in show_goals: {str(e)}")
        await callback.answer("Произошла ошибка при отображении целей", show_alert=True)

@router.callback_query(F.data == "goals_next_page")
async def next_page(callback: CallbackQuery, state: FSMContext):
    """Show the next page of goals."""
    goals = goals_storage.get_goals()
    keyboard, message_text = goals_keyboard.generate_goals_keyboard(goals, goals_keyboard.current_page + 1)
    await callback.message.edit_text(text=message_text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data == "goals_prev_page")
async def prev_page(callback: CallbackQuery, state: FSMContext):
    """Show the previous page of goals."""
    goals = goals_storage.get_goals()
    keyboard, message_text = goals_keyboard.generate_goals_keyboard(goals, goals_keyboard.current_page - 1)
    await callback.message.edit_text(text=message_text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("toggle_goal:"))
async def toggle_goal(callback: CallbackQuery, state: FSMContext):
    """Toggle the completion status of a goal."""
    try:
        goal_idx = int(callback.data.split(":")[1])
        goals = goals_storage.get_goals()
        
        if not 0 <= goal_idx < len(goals):
            await callback.answer("Ошибка: цель не найдена", show_alert=True)
            return
            
        goals[goal_idx]["completed"] = not goals[goal_idx].get("completed", False)
        goals_storage.save_data(goals)
        
        keyboard, message_text = goals_keyboard.generate_goals_keyboard(goals)
        await callback.message.edit_text(text=message_text, reply_markup=keyboard)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in toggle_goal: {str(e)}")
        await callback.answer("Произошла ошибка при изменении статуса цели", show_alert=True)

@router.callback_query(F.data.startswith("delete_goal:"))
async def delete_goal(callback: CallbackQuery, state: FSMContext):
    """Delete a goal."""
    try:
        goal_idx = int(callback.data.split(":")[1])
        goals = goals_storage.get_goals()
        
        if not 0 <= goal_idx < len(goals):
            await callback.answer("Ошибка: цель не найдена", show_alert=True)
            return
            
        del goals[goal_idx]
        goals_storage.save_data(goals)
        
        keyboard, message_text = goals_keyboard.generate_goals_keyboard(goals)
        await callback.message.edit_text(text=message_text, reply_markup=keyboard)
        await callback.answer("Цель удалена")
    except Exception as e:
        logger.error(f"Error in delete_goal: {str(e)}")
        await callback.answer("Произошла ошибка при удалении цели", show_alert=True)

@router.callback_query(F.data.startswith("edit_goal:"))
async def start_edit_goal(callback: CallbackQuery, state: FSMContext):
    """Start editing a goal."""
    try:
        goal_idx = int(callback.data.split(":")[1])
        goals = goals_storage.get_goals()
        
        if not 0 <= goal_idx < len(goals):
            await callback.answer("Ошибка: цель не найдена", show_alert=True)
            return
            
        await state.update_data(editing_goal_idx=goal_idx)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Изменить текст", callback_data=f"edit_goal_text:{goal_idx}"),
                InlineKeyboardButton(text="🎯 Изменить приоритет", callback_data=f"edit_goal_priority:{goal_idx}")
            ],
            [
                InlineKeyboardButton(text="⏰ Изменить срок", callback_data=f"edit_goal_deadline:{goal_idx}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="show_goals")
            ]
        ])
        
        await callback.message.edit_text(
            text=f"Редактирование цели:\n{goals[goal_idx]['text']}",
            reply_markup=keyboard
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in start_edit_goal: {str(e)}")
        await callback.answer("Произошла ошибка при начале редактирования", show_alert=True)

@router.callback_query(F.data.startswith("edit_goal_text:"))
async def start_edit_goal_text(callback: CallbackQuery, state: FSMContext):
    """Start editing goal text."""
    goal_idx = int(callback.data.split(":")[1])
    await state.set_state(GoalStates.editing_text)
    await state.update_data(editing_goal_idx=goal_idx)
    await callback.message.edit_text("Введите новый текст цели:")
    await callback.answer()

@router.message(GoalStates.editing_text)
async def receive_edited_text(message: Message, state: FSMContext):
    """Handle edited goal text."""
    data = await state.get_data()
    goal_idx = data["editing_goal_idx"]
    goals = goals_storage.get_goals()
    
    goals[goal_idx]["text"] = message.text
    goals_storage.save_data(goals)
    
    keyboard, message_text = goals_keyboard.generate_goals_keyboard(goals, goals_keyboard.current_page)
    await message.answer(text=message_text, reply_markup=keyboard)
    await state.clear()

@router.callback_query(F.data.startswith("edit_goal_priority:"))
async def start_edit_goal_priority(callback: CallbackQuery, state: FSMContext):
    """Start editing goal priority."""
    goal_idx = int(callback.data.split(":")[1])
    await state.set_state(GoalStates.editing_priority)
    await state.update_data(editing_goal_idx=goal_idx)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"{PRIORITY_ICONS['high']} Высокий", callback_data=f"priority:high"),
            InlineKeyboardButton(text=f"{PRIORITY_ICONS['medium']} Средний", callback_data=f"priority:medium"),
            InlineKeyboardButton(text=f"{PRIORITY_ICONS['low']} Низкий", callback_data=f"priority:low")
        ]
    ])
    
    await callback.message.edit_text("Выберите новый приоритет:", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(GoalStates.editing_priority)
async def receive_edited_priority(callback: CallbackQuery, state: FSMContext):
    """Handle edited goal priority."""
    data = await state.get_data()
    goal_idx = data["editing_goal_idx"]
    priority = callback.data.split(":")[1]
    
    goals = goals_storage.get_goals()
    goals[goal_idx]["priority"] = priority
    goals_storage.save_data(goals)
    
    keyboard, message_text = goals_keyboard.generate_goals_keyboard(goals, goals_keyboard.current_page)
    await callback.message.edit_text(text=message_text, reply_markup=keyboard)
    await state.clear()
    await callback.answer()

@router.callback_query(F.data.startswith("edit_goal_deadline:"))
async def start_edit_goal_deadline(callback: CallbackQuery, state: FSMContext):
    """Start editing goal deadline."""
    try:
        goal_idx = int(callback.data.split(":")[1])
        await state.set_state(GoalStates.editing_deadline)
        await state.update_data(editing_goal_idx=goal_idx)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=f"{TIME_ICONS['clock']} Сегодня", callback_data=f"edit_deadline:{goal_idx}:{datetime.now().strftime('%Y-%m-%d')}"),
                InlineKeyboardButton(text=f"{TIME_ICONS['clock']} Завтра", callback_data=f"edit_deadline:{goal_idx}:{(datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')}")
            ],
            [
                InlineKeyboardButton(text=f"{TIME_ICONS['calendar']} Неделя", callback_data=f"edit_deadline:{goal_idx}:{(datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')}"),
                InlineKeyboardButton(text=f"{TIME_ICONS['calendar']} Месяц", callback_data=f"edit_deadline:{goal_idx}:{(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')}")
            ],
            [
                InlineKeyboardButton(text="Без срока", callback_data=f"edit_deadline:{goal_idx}:none")
            ]
        ])
        
        await callback.message.edit_text("Выберите новый срок:", reply_markup=keyboard)
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}", show_alert=True)
        await state.clear()

@router.callback_query(F.data.startswith("edit_deadline:"))
async def receive_edited_deadline(callback: CallbackQuery, state: FSMContext):
    """Handle edited goal deadline."""
    try:
        parts = callback.data.split(":")
        if len(parts) < 3:
            await callback.answer("Ошибка: неверный формат данных", show_alert=True)
            await state.clear()
            return
            
        goal_idx = int(parts[1])
        deadline = parts[2]
        
        goals = goals_storage.get_goals()
        if not 0 <= goal_idx < len(goals):
            await callback.answer("Ошибка: цель не найдена", show_alert=True)
            await state.clear()
            return
            
        goals[goal_idx]["deadline"] = None if deadline == "none" else deadline
        goals_storage.save_data(goals)
        
        keyboard, message_text = goals_keyboard.generate_goals_keyboard(goals)
        await callback.message.edit_text(text=message_text, reply_markup=keyboard)
        await state.clear()
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in receive_edited_deadline: {str(e)}")
        await callback.answer(f"Произошла ошибка: {str(e)}", show_alert=True)
        await state.clear()

@router.callback_query(GoalStates.waiting_for_deadline)
async def receive_deadline(callback: CallbackQuery, state: FSMContext):
    """Handle deadline selection for a new goal."""
    try:
        parts = callback.data.split(":")
        if len(parts) < 2:
            await callback.answer("Ошибка: неверный формат данных", show_alert=True)
            await state.clear()
            return
            
        deadline_type = parts[1]
        state_data = await state.get_data()
        
        if not state_data.get("text"):
            await callback.answer("Ошибка: текст цели не найден", show_alert=True)
            await state.clear()
            return
            
        if not state_data.get("priority"):
            await callback.answer("Ошибка: приоритет не выбран", show_alert=True)
            await state.clear()
            return
        
        # Определяем дату дедлайна
        deadline = None
        today = datetime.now().date()
        
        if deadline_type == "today":
            deadline = today.strftime("%Y-%m-%d")
        elif deadline_type == "tomorrow":
            deadline = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        elif deadline_type == "week":
            deadline = (today + timedelta(days=7)).strftime("%Y-%m-%d")
        
        # Add the goal using storage method
        try:
            goals_storage.add_goal(
                text=state_data["text"],
                priority=state_data["priority"],
                deadline=deadline
            )
            
            # Get updated goals list and generate keyboard
            goals = goals_storage.get_goals()
            keyboard = generate_goals_keyboard(goals)
            
            # Update message with new goals list
            await callback.message.edit_text(
                text="🎯 Ваши цели:",
                reply_markup=keyboard
            )
            await callback.answer("✅ Цель добавлена")
            
        except Exception as e:
            logger.error(f"Error in receive_deadline: {str(e)}")
            await callback.answer(f"Ошибка при сохранении цели: {str(e)}", show_alert=True)
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error in receive_deadline: {str(e)}")
        await callback.answer(f"Произошла ошибка: {str(e)}", show_alert=True)
        await state.clear()

@router.callback_query(F.data == "goals_sort")
async def show_sort_options(callback: CallbackQuery):
    """Show goal sorting options."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="По приоритету", callback_data="sort:priority"),
            InlineKeyboardButton(text="По сроку", callback_data="sort:deadline")
        ],
        [
            InlineKeyboardButton(text="По статусу", callback_data="sort:status"),
            InlineKeyboardButton(text="По умолчанию", callback_data="sort:default")
        ]
    ])
    await callback.message.edit_text("Выберите способ сортировки:", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("goals_sort:"))
async def sort_goals(callback: CallbackQuery):
    """Sort goals based on selected criteria."""
    try:
        sort_type = callback.data.split(":")[1]
        goals = goals_storage.get_goals()
        
        if sort_type == "priority":
            priority_order = {"high": 0, "medium": 1, "low": 2}
            goals.sort(key=lambda x: priority_order.get(x.get("priority", "medium"), 1))
        elif sort_type == "deadline":
            goals.sort(key=lambda x: x.get("deadline") or "9999-12-31")
        elif sort_type == "status":
            goals.sort(key=lambda x: not x.get("completed", False))
        elif sort_type == "date":
            goals.sort(key=lambda x: x.get("created_at") or "")
        
        goals_storage.save_data(goals)
        keyboard, message_text = goals_keyboard.generate_goals_keyboard(goals)
        await callback.message.edit_text(text=message_text, reply_markup=keyboard)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in sort_goals: {str(e)}")
        await callback.answer("Произошла ошибка при сортировке целей", show_alert=True)

async def send_goals_report(bot: Bot):
    """Send weekly goals report."""
    goals = goals_storage.get_goals()
    completed = [g for g in goals if g.get("completed", False)]
    active = [g for g in goals if not g.get("completed", False)]
    overdue = [g for g in active if g.get("deadline") and datetime.strptime(g["deadline"], "%Y-%m-%d").date() < datetime.now().date()]
    
    text = "🎯 Еженедельный отчет по целям:\n\n"
    text += f"✅ Достигнуто: {len(completed)} целей\n"
    text += f"⏳ В процессе: {len(active)} целей\n"
    text += f"❌ Просрочено: {len(overdue)} целей\n\n"
    
    if overdue:
        text += "Просроченные цели:\n"
        for goal in overdue:
            text += f"• {goal['text']} ({goal.get('priority', 'средний')})\n"
    
    await bot.send_message(USER_ID, text)

@router.callback_query(F.data == "add_goal")
async def start_add_goal(callback: CallbackQuery, state: FSMContext):
    """Start the goal addition process."""
    try:
        await state.set_state(GoalStates.waiting_for_text)
        await callback.message.answer("Введите текст цели:")
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in start_add_goal: {str(e)}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)

@router.message(GoalStates.waiting_for_text)
async def receive_goal_text(message: Message, state: FSMContext):
    """Handle receiving the goal text."""
    try:
        text = message.text.strip()
        await state.update_data(text=text)
        
        # Создаем клавиатуру для выбора приоритета
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔴 Высокий", callback_data="priority_high"),
                InlineKeyboardButton(text="🟡 Средний", callback_data="priority_medium"),
                InlineKeyboardButton(text="🟢 Низкий", callback_data="priority_low")
            ]
        ])
        
        await message.answer("Выберите приоритет:", reply_markup=keyboard)
        await state.set_state(GoalStates.waiting_for_priority)
    except Exception as e:
        logger.error(f"Error in receive_goal_text: {str(e)}")
        await message.answer("❌ Произошла ошибка при сохранении текста цели")
        await state.clear()

@router.callback_query(GoalStates.waiting_for_priority)
async def receive_priority(callback: CallbackQuery, state: FSMContext):
    """Handle receiving the goal priority."""
    try:
        priority = callback.data.split("_")[1]
        data = await state.get_data()
        text = data.get("text")
        
        if not text:
            await callback.answer("❌ Ошибка: текст цели не найден", show_alert=True)
            await state.clear()
            return
        
        # Сохраняем приоритет в состоянии
        await state.update_data(priority=priority)
        
        # Создаем клавиатуру для выбора дедлайна
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Сегодня", callback_data="deadline:today"),
                InlineKeyboardButton(text="Завтра", callback_data="deadline:tomorrow")
            ],
            [
                InlineKeyboardButton(text="Через неделю", callback_data="deadline:week"),
                InlineKeyboardButton(text="Без дедлайна", callback_data="deadline:none")
            ]
        ])
        
        await callback.message.edit_text(
            text="Выберите срок выполнения:",
            reply_markup=keyboard
        )
        await state.set_state(GoalStates.waiting_for_deadline)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in receive_priority: {str(e)}")
        await callback.answer("❌ Произошла ошибка при сохранении приоритета", show_alert=True)
        await state.clear()
