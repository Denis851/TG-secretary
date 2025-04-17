"""
Клавиатуры для работы с целями
"""
from typing import List, Dict, Any, Union, Tuple
from .base import BaseKeyboard
from constants.icons import (
    PRIORITY_ICONS,
    STATUS_ICONS,
    TIME_ICONS,
    ACTION_ICONS,
    NAVIGATION_ICONS
)
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime

class GoalsKeyboard(BaseKeyboard):
    """Класс для создания клавиатур целей"""
    
    @classmethod
    def generate_goals_keyboard(
        cls,
        goals: List[Dict[str, Any]],
        show_sort: bool = False
    ) -> Dict[str, Any]:
        """
        Генерирует клавиатуру для целей
        
        Args:
            goals: список целей
            show_sort: показывать ли кнопки сортировки
            
        Returns:
            Dict с текстом сообщения и разметкой клавиатуры
        """
        keyboard = []
        text = "🎯 Ваши цели:\n\n"
        
        # Добавляем кнопки сортировки если нужно
        if show_sort and goals:
            keyboard.extend(cls.generate_sort_buttons())
        elif goals:
            keyboard.append([{
                "text": f"{NAVIGATION_ICONS['sort']} Сортировка",
                "callback_data": "sort_goals:show"
            }])
        
        # Добавляем цели
        for i, goal in enumerate(goals, 1):
            status = "✅" if goal.get("completed") else "⬜️"
            priority = goal.get("priority", "normal").lower()
            priority_emoji = "🔴" if priority == "high" else "🟡" if priority == "medium" else "🟢"
            goal_text = goal.get("text", "")
            deadline = cls.format_deadline(goal.get("deadline", ""))
            
            if goals:
                text += f"{status} {i}. {goal_text} {priority_emoji} {deadline}\n"
            
            # Кнопка с текстом цели
            keyboard.append([{
                "text": f"{status} {priority_emoji} {goal_text}",
                "callback_data": f"goal_toggle:{i-1}"
            }])
            
            # Кнопки управления целью
            keyboard.append([{
                "text": f"{ACTION_ICONS['edit']}",
                "callback_data": f"goal_edit:{i-1}"
            }, {
                "text": f"{ACTION_ICONS['delete']}",
                "callback_data": f"goal_delete:{i-1}"
            }])
        
        # Добавляем кнопку добавления
        keyboard.append([{
            "text": f"{ACTION_ICONS['add']} Добавить цель",
            "callback_data": "goal_add"
        }])
        
        return {
            "text": text,
            "reply_markup": cls.create_inline_keyboard(keyboard)
        }
    
    @classmethod
    def generate_sort_buttons(cls) -> List[List[Dict[str, str]]]:
        """Генерирует кнопки для сортировки"""
        return [
            [{
                "text": f"{PRIORITY_ICONS['высокий']} По приоритету",
                "callback_data": "sort_goals:priority"
            }, {
                "text": f"{STATUS_ICONS['completed']} По статусу",
                "callback_data": "sort_goals:status"
            }],
            [{
                "text": f"{TIME_ICONS['deadline']} По дедлайну",
                "callback_data": "sort_goals:deadline"
            }, {
                "text": f"{TIME_ICONS['calendar']} По дате создания",
                "callback_data": "sort_goals:date"
            }],
            [{
                "text": f"{NAVIGATION_ICONS['sort']} Изменить порядок",
                "callback_data": "sort_goals:reverse"
            }]
        ]
    
    @staticmethod
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
                return f"{STATUS_ICONS['overdue']} Просрочено ({date.strftime('%d.%m')})"
            elif delta.days < 7:
                return f"{TIME_ICONS['deadline']} Через {delta.days} дн."
            else:
                return f"{TIME_ICONS['calendar']} {date.strftime('%d.%m')}"
        except ValueError:
            return ""

    @staticmethod
    def create_inline_keyboard(buttons: List[Union[Dict[str, str], List[Dict[str, str]]]]) -> InlineKeyboardMarkup:
        """
        Creates an inline keyboard from a list of buttons.
        
        Args:
            buttons: List of button configurations. Each item can be either:
                    - A dictionary representing a single button: {"text": str, "callback_data": str}
                    - A list of dictionaries representing a row of buttons
        
        Returns:
            InlineKeyboardMarkup: The constructed keyboard
        
        Example:
            buttons = [
                {"text": "Single Button", "callback_data": "single"},  # Single button in a row
                [  # Row of multiple buttons
                    {"text": "Button 1", "callback_data": "btn1"},
                    {"text": "Button 2", "callback_data": "btn2"}
                ]
            ]
        """
        keyboard = []
        for row in buttons:
            if isinstance(row, dict):
                # Single button as dict - create a new row with one button
                keyboard.append([InlineKeyboardButton(**row)])
            elif isinstance(row, list):
                # Row of buttons - convert each dict to InlineKeyboardButton
                keyboard.append([InlineKeyboardButton(**btn) for btn in row])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def get_goals_keyboard(cls, goals: list) -> dict:
        """
        Создает клавиатуру для целей
        :param goals: список целей
        :return: словарь с клавиатурой и текстом сообщения
        """
        if not goals:
            buttons = [[{
                "text": "➕ Добавить цель",
                "callback_data": "goal_add"
            }]]
            text = "У вас пока нет целей. Добавьте новую цель!"
        else:
            buttons = []
            text = "🎯 Ваши цели:\n\n"
            
            for i, goal in enumerate(goals, 1):
                status = "✅" if goal.get("completed") else "⬜️"
                priority = goal.get("priority", "средний").lower()
                priority_emoji = "🔴" if priority == "высокий" else "🟡" if priority == "средний" else "🟢"
                
                text += f"{status} {i}. {goal['text']} {priority_emoji}\n"
                
                # Кнопка с текстом цели
                buttons.append([{
                    "text": f"{status} {goal['text']}",
                    "callback_data": f"goal_toggle:{i-1}"
                }])
                
                # Кнопки управления целью
                buttons.append([{
                    "text": "🗑",
                    "callback_data": f"goal_delete:{i-1}"
                }])
            
            # Кнопка добавления новой цели
            buttons.append([{
                "text": "➕ Добавить цель",
                "callback_data": "goal_add"
            }])
        
        return {
            "text": text,
            "reply_markup": cls.create_inline_keyboard(buttons)
        }

    @staticmethod
    def get_main_keyboard() -> dict:
        """
        Создает основную клавиатуру с кнопками меню
        :return: словарь с клавиатурой и текстом сообщения
        """
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="✅ Чеклист"),
                    KeyboardButton(text="🎯 Цели")
                ],
                [
                    KeyboardButton(text="📊 Статистика"),
                    KeyboardButton(text="📝 Редактировать")
                ]
            ],
            resize_keyboard=True
        )
        
        return {
            "text": "Выберите действие:",
            "reply_markup": keyboard
        } 