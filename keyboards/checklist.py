"""
Клавиатуры для работы с чеклистом
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict, Any
from datetime import datetime
from .base import BaseKeyboard
from constants.icons import (
    PRIORITY_ICONS,
    STATUS_ICONS,
    TIME_ICONS,
    ACTION_ICONS,
    NAVIGATION_ICONS
)

class ChecklistKeyboard(BaseKeyboard):
    """Класс для работы с клавиатурой чеклиста"""
    
    @classmethod
    def get_checklist_keyboard(cls, tasks: list) -> dict:
        """
        Создает клавиатуру для чеклиста
        :param tasks: список задач
        :return: словарь с клавиатурой и текстом сообщения
        """
        if not tasks:
            buttons = [[{
                "text": "➕ Добавить задачу",
                "callback_data": "add_task"
            }]]
            text = "У вас пока нет задач в чеклисте. Добавьте новую задачу!"
        else:
            buttons = []
            text = "📋 Ваш чеклист:\n\n"
            
            for i, task in enumerate(tasks, 1):
                status = "✅" if task.get("completed", task.get("done", False)) else "⬜️"
                text += f"{status} {i}. {task['text']}\n"
                
                # Кнопка с текстом задачи
                buttons.append([{
                    "text": f"{status} {task['text']}",
                    "callback_data": f"toggle_task:{task['text']}"
                }])
                
                # Кнопки управления задачей
                buttons.append([{
                    "text": "🗑",
                    "callback_data": f"delete_task:{task['text']}"
                }])
            
            # Кнопка добавления новой задачи
            buttons.append([{
                "text": "➕ Добавить задачу",
                "callback_data": "add_task"
            }])
        
        return {
            "text": text,
            "reply_markup": cls.create_inline_keyboard(buttons)
        }

    @classmethod
    def get_main_keyboard(cls) -> dict:
        """
        Создает основную клавиатуру бота
        :return: словарь с клавиатурой
        """
        buttons = [
            ["✅ Чеклист", "🎯 Цели"],
            ["📊 Статистика", "📝 Редактировать"]
        ]
        return {
            "reply_markup": cls.create_reply_keyboard(buttons)
        }

    @classmethod
    def generate_checklist_keyboard(
        cls,
        tasks: List[Dict[str, Any]],
        show_sort: bool = False
    ) -> InlineKeyboardMarkup:
        """Генерирует клавиатуру для чеклиста"""
        buttons = []
        
        # Добавляем кнопки управления
        if show_sort:
            buttons.extend(cls.generate_sort_buttons())
            buttons.append([{
                "text": f"{ACTION_ICONS['back']} Скрыть сортировку",
                "callback_data": "sort_tasks:hide"
            }])
        elif tasks:
            buttons.append([{
                "text": f"{NAVIGATION_ICONS['sort']} Сортировка",
                "callback_data": "sort_tasks:show"
            }])
        
        # Добавляем задачи
        for i, task in enumerate(tasks):
            icon = PRIORITY_ICONS.get(task.get("priority", "средний").lower(), "⚖️")
            status = STATUS_ICONS["completed"] if task.get("completed", False) else STATUS_ICONS["pending"]
            deadline_text = cls.format_deadline(task.get("deadline"))
            
            task_text = f"{status} {icon} {task['text']}"
            if deadline_text:
                task_text += f" {deadline_text}"
                
            buttons.extend([
                [{
                    "text": task_text,
                    "callback_data": f"toggle_task:{i}"
                }],
                [{
                    "text": f"{ACTION_ICONS['edit']} Текст",
                    "callback_data": f"edit_text_{i}"
                }, {
                    "text": f"{TIME_ICONS['deadline']} Дедлайн",
                    "callback_data": f"edit_deadline_{i}"
                }, {
                    "text": f"{ACTION_ICONS['delete']}",
                    "callback_data": f"delete_task:{i}"
                }]
            ])
        
        # Добавляем кнопку добавления
        buttons.append([{
            "text": f"{ACTION_ICONS['add']} Добавить задачу",
            "callback_data": "add_task"
        }])
        
        return cls.create_inline_keyboard(buttons)
    
    @classmethod
    def generate_sort_buttons(cls) -> List[List[Dict[str, str]]]:
        """Генерирует кнопки для сортировки"""
        return [
            [{
                "text": f"{PRIORITY_ICONS['высокий']} По приоритету",
                "callback_data": "sort_tasks:priority"
            }, {
                "text": f"{STATUS_ICONS['completed']} По статусу",
                "callback_data": "sort_tasks:status"
            }],
            [{
                "text": f"{TIME_ICONS['deadline']} По дедлайну",
                "callback_data": "sort_tasks:deadline"
            }, {
                "text": f"{TIME_ICONS['calendar']} По дате создания",
                "callback_data": "sort_tasks:date"
            }],
            [{
                "text": f"{NAVIGATION_ICONS['sort']} Изменить порядок",
                "callback_data": "sort_tasks:reverse"
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
    def create_inline_keyboard(buttons: List[List[Dict[str, str]]]) -> InlineKeyboardMarkup:
        """
        Создает inline клавиатуру из списка кнопок
        :param buttons: список кнопок
        :return: объект InlineKeyboardMarkup
        """
        keyboard = []
        for row in buttons:
            keyboard_row = []
            for button in row:
                keyboard_row.append(InlineKeyboardButton(
                    text=button["text"],
                    callback_data=button["callback_data"]
                ))
            keyboard.append(keyboard_row)
        return InlineKeyboardMarkup(inline_keyboard=keyboard) 