from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.storage import goal_storage, ValidationError, StorageError
from keyboards.goals import GoalsKeyboard
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json
import os
import re

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

# Обновляем иконки
STATUS_ICONS = {
    'completed': '✅',
    'pending': '⬜️',
    'error': '❌',
    'success': '✅'
}

PRIORITY_ICONS = {
    'high': '🔴',
    'medium': '🟡',
    'low': '🟢'
}

TIME_ICONS = {
    'deadline': '📅',
    'calendar': '📆'
}

ACTION_ICONS = {
    'add': '➕',
    'edit': '✏️',
    'delete': '🗑',
    'back': '◀️'
}

NAVIGATION_ICONS = {
    'sort': '🔄'
}

router = Router()
goals_keyboard = GoalsKeyboard()

class AddGoal(StatesGroup):
    waiting_for_goal_text = State()
    waiting_for_priority = State()
    waiting_for_deadline = State()

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
async def show_goals(message: Message, state: FSMContext):
    try:
        goals = load_goals()
        
        if not goals:
            text = "У вас пока нет целей. Добавьте новую цель!"
        else:
            text = "🎯 Ваши цели:\n\n"
            for i, goal in enumerate(goals, 1):
                text += format_goal_text(goal, i) + "\n"
        
        keyboard = generate_goals_keyboard(goals)
        await message.answer(text=text, reply_markup=keyboard)
    except Exception as e:
        await message.answer("❌ Произошла ошибка при загрузке целей: " + str(e))

@router.callback_query(F.data == "add_goal")
async def start_add_goal(callback: CallbackQuery, state: FSMContext):
    try:
        await state.set_state(AddGoal.waiting_for_goal_text)
        await callback.message.answer("Введите текст новой цели:")
        await callback.answer()
    except Exception as e:
        await callback.answer("❌ Произошла ошибка: " + str(e), show_alert=True)

@router.callback_query(F.data.startswith("toggle_goal:"))
async def toggle_goal_status(callback: CallbackQuery, state: FSMContext):
    try:
        goal_id = int(callback.data.split(":")[1])
        goals = load_goals()
        
        if 0 <= goal_id < len(goals):
            goals[goal_id]["completed"] = not goals[goal_id].get("completed", False)
            if goals[goal_id]["completed"]:
                goals[goal_id]["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            else:
                goals[goal_id].pop("completed_at", None)
            
            # Сохраняем обновленный список целей
            save_goals(goals)
            
            text = "🎯 Ваши цели:\n\n"
            for i, goal in enumerate(goals, 1):
                text += format_goal_text(goal, i) + "\n"
            
            keyboard = generate_goals_keyboard(goals)
            await callback.message.edit_text(text=text, reply_markup=keyboard)
            await callback.answer("✅ Статус цели обновлён")
    except Exception as e:
        await callback.answer("❌ Произошла ошибка: " + str(e), show_alert=True)

@router.callback_query(F.data.startswith("delete_goal:"))
async def delete_goal(callback: CallbackQuery, state: FSMContext):
    try:
        goal_id = int(callback.data.split(":")[1])
        goals = load_goals()
        
        if 0 <= goal_id < len(goals):
            deleted_goal = goals.pop(goal_id)
            # Сохраняем обновленный список целей
            save_goals(goals)
            
            text = "🎯 Ваши цели:\n\n" if goals else "У вас пока нет целей. Добавьте новую цель!"
            if goals:
                for i, goal in enumerate(goals, 1):
                    text += format_goal_text(goal, i) + "\n"
            
            keyboard = generate_goals_keyboard(goals)
            await callback.message.edit_text(text=text, reply_markup=keyboard)
            await callback.answer("🗑 Цель удалена")
    except Exception as e:
        await callback.answer("❌ Произошла ошибка: " + str(e), show_alert=True)

@router.message(AddGoal.waiting_for_goal_text)
async def receive_goal_text(message: Message, state: FSMContext):
    try:
        print("Receiving goal text...")
        
        if not isinstance(message.text, str):
            print(f"Invalid text type: {type(message.text)}")
            await message.answer("❌ Ошибка: текст цели должен быть строкой")
            return
            
        text = message.text.strip()
        if not text:
            await message.answer("❌ Текст цели не может быть пустым")
            return
            
        print(f"Saving goal text: {text}")
        
        # Сохраняем текст цели в состоянии
        await state.update_data(goal_text=text)
        
        # Показываем клавиатуру с выбором приоритета
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{PRIORITY_ICONS['high']} Высокий", callback_data="priority:high")],
            [InlineKeyboardButton(text=f"{PRIORITY_ICONS['medium']} Средний", callback_data="priority:medium")],
            [InlineKeyboardButton(text=f"{PRIORITY_ICONS['low']} Низкий", callback_data="priority:low")]
        ])
        
        await message.answer("Выберите приоритет цели:", reply_markup=keyboard)
        await state.set_state(AddGoal.waiting_for_priority)
        
    except Exception as e:
        print(f"Error in receive_goal_text: {str(e)}")
        await message.answer("❌ Произошла ошибка при сохранении текста цели: " + str(e))
        await state.clear()

@router.callback_query(AddGoal.waiting_for_priority)
async def receive_priority(callback: CallbackQuery, state: FSMContext):
    try:
        print("Receiving priority...")
        priority = callback.data.split(":")[1]
        print(f"Priority value: {priority}")
        
        # Сохраняем приоритет в состоянии
        current_data = await state.get_data()
        await state.update_data(
            goal_text=current_data.get("goal_text"),
            priority=priority
        )
        
        # Показываем клавиатуру с выбором дедлайна
        today = datetime.now().date()
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=f"{TIME_ICONS['deadline']} Сегодня", 
                                   callback_data=f"deadline:{today.strftime('%Y-%m-%d')}"),
                InlineKeyboardButton(text=f"{TIME_ICONS['deadline']} Завтра", 
                                   callback_data=f"deadline:{(today + timedelta(days=1)).strftime('%Y-%m-%d')}")
            ],
            [
                InlineKeyboardButton(text=f"{TIME_ICONS['deadline']} Через неделю", 
                                   callback_data=f"deadline:{(today + timedelta(weeks=1)).strftime('%Y-%m-%d')}")
            ],
            [
                InlineKeyboardButton(text=f"{TIME_ICONS['calendar']} Без дедлайна", 
                                   callback_data="deadline:none")
            ]
        ])
        
        await callback.message.edit_text("Выберите дедлайн для цели:", reply_markup=keyboard)
        await state.set_state(AddGoal.waiting_for_deadline)
        await callback.answer()
        
    except Exception as e:
        print(f"Error in receive_priority: {str(e)}")
        await callback.answer("❌ Произошла ошибка при сохранении приоритета: " + str(e), show_alert=True)
        await state.clear()

@router.callback_query(AddGoal.waiting_for_deadline)
async def receive_deadline(callback: CallbackQuery, state: FSMContext):
    try:
        print(f"Receiving deadline: {callback.data}")
        deadline = None
        if callback.data.startswith("deadline:"):
            deadline = callback.data.split(":", 1)[1]
            if deadline == "none":
                deadline = None
                
        print(f"Deadline value: {deadline}")
        
        # Получаем сохраненные данные
        data = await state.get_data()
        print(f"State data: {data}")
        
        # Загружаем текущие цели
        goals = load_goals()
        goal_text = data.get("goal_text")
        priority = data.get("priority")
        
        if not isinstance(goal_text, str):
            raise ValueError("Текст цели должен быть строкой")
            
        # Создаем новую цель
        new_goal = {
            "text": goal_text,
            "priority": priority,
            "deadline": deadline,
            "completed": False,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        print(f"New goal: {new_goal}")
        # Добавляем новую цель к существующим
        goals.append(new_goal)
        
        # Сохраняем обновленный список целей
        save_goals(goals)
        
        # Формируем текст сообщения
        text = "🎯 Ваши цели:\n\n"
        for i, goal in enumerate(goals, 1):
            text += format_goal_text(goal, i) + "\n"
        
        # Создаем новую клавиатуру
        keyboard = generate_goals_keyboard(goals)
        
        # Отправляем новое сообщение со списком целей
        await callback.message.answer(text=text, reply_markup=keyboard)
        await callback.message.delete()
        await callback.answer("✅ Цель добавлена")
        await state.clear()
        
    except Exception as e:
        print(f"Error in receive_deadline: {str(e)}")
        await callback.answer("❌ Произошла ошибка: " + str(e), show_alert=True)
        await state.clear()

@router.callback_query(F.data.startswith("sort_goals:"))
async def handle_sort_goals(callback: CallbackQuery, state: FSMContext):
    try:
        action = callback.data.split(":")[1]
        data = await state.get_data()
        goals = data.get("goals", [])
        
        if not goals:
            await callback.answer("Нет целей для сортировки")
            return
            
        if action == "show":
            keyboard = generate_goals_keyboard(goals, show_sort=True)
            await callback.message.edit_reply_markup(reply_markup=keyboard)
        elif action == "hide":
            keyboard = generate_goals_keyboard(goals, show_sort=False)
            await callback.message.edit_reply_markup(reply_markup=keyboard)
        else:
            # Сортировка по разным параметрам
            if action == "priority":
                priority_order = {"high": 0, "medium": 1, "low": 2}
                goals.sort(key=lambda x: priority_order.get(x.get("priority", "medium"), 1))
            elif action == "status":
                goals.sort(key=lambda x: x.get("completed", False))
            elif action == "deadline":
                goals.sort(key=lambda x: x.get("deadline", "9999-12-31"))
            elif action == "date":
                goals.sort(key=lambda x: x.get("created_at", ""))
            elif action == "reverse":
                goals.reverse()
            
            await state.update_data(goals=goals)
            keyboard = generate_goals_keyboard(goals, show_sort=True)
            text = "🎯 Ваши цели:\n\n"
            
            for i, goal in enumerate(goals, 1):
                text += format_goal_text(goal, i) + "\n"
            
            await callback.message.edit_text(text=text, reply_markup=keyboard)
        
        await callback.answer()
    except Exception as e:
        await callback.answer(f"{STATUS_ICONS['error']} Произошла ошибка: {str(e)}", show_alert=True)

async def send_goals_report(bot: Bot):
    """Отправляет еженедельный отчет по целям."""
    # В реальном приложении здесь нужно:
    # 1. Получить список пользователей
    # 2. Для каждого пользователя получить его цели
    # 3. Сформировать отчет по достигнутым и текущим целям
    # 4. Отправить персонализированный отчет
    # await bot.send_message(
    #     chat_id=user_id,
    #     text="🎯 Еженедельный отчет по целям:\n\n"
    #          "✅ Достигнуто: X целей\n"
    #          "⏳ В процессе: Y целей\n"
    #          "❌ Просрочено: Z целей"
    # )
    pass
