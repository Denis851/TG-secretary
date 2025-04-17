"""
Клавиатуры для работы с расписанием
"""
from typing import List, Dict, Any
from .base import BaseKeyboard
from constants.icons import (
    TIME_ICONS,
    ACTION_ICONS
)
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def schedule_item_kb(index: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить", callback_data=f"edit_schedule:{index}")]
        ]
    )

class ScheduleKeyboard(BaseKeyboard):
    """Класс для создания клавиатур расписания"""
    
    @classmethod
    def generate_schedule_keyboard(
        cls,
        schedule: List[Dict[str, Any]],
        show_controls: bool = True
    ) -> InlineKeyboardMarkup:
        """Генерирует клавиатуру для расписания"""
        buttons = []
        
        # Добавляем кнопки управления
        if show_controls:
            buttons.append([{
                "text": f"{ACTION_ICONS['add']} Добавить пункт",
                "callback_data": "schedule_add"
            }, {
                "text": f"{ACTION_ICONS['refresh']} Обновить",
                "callback_data": "schedule_refresh"
            }])
        
        # Добавляем пункты расписания
        for i, entry in enumerate(schedule):
            time = entry.get("time", "00:00")
            task = entry.get("text", "")
            
            buttons.extend([
                [{
                    "text": f"{TIME_ICONS['clock']} {time} — {task}",
                    "callback_data": f"view_schedule_{i}"
                }],
                [{
                    "text": f"{ACTION_ICONS['edit']} Текст",
                    "callback_data": f"edit_text_{i}"
                }, {
                    "text": f"{TIME_ICONS['clock']} Время",
                    "callback_data": f"edit_time_{i}"
                }, {
                    "text": f"{ACTION_ICONS['delete']}",
                    "callback_data": f"delete_schedule_{i}"
                }]
            ])
        
        return cls.create_inline_keyboard(buttons)

