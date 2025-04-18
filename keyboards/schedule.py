"""
Клавиатуры для работы с расписанием
"""
from typing import List, Dict, Any, Tuple
from .base import BaseKeyboard
from constants.icons import (
    TIME_ICONS,
    ACTION_ICONS,
    NAVIGATION_ICONS
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
        page: int = 0
    ) -> Tuple[InlineKeyboardMarkup, str]:
        """Генерирует клавиатуру для расписания и текст сообщения."""
        entries_per_page = 5
        total_pages = (len(schedule) + entries_per_page - 1) // entries_per_page
        start_idx = page * entries_per_page
        end_idx = min(start_idx + entries_per_page, len(schedule))
        
        current_entries = schedule[start_idx:end_idx]
        buttons = []
        message_lines = ["📅 Ваше расписание:"]
        
        # Добавляем записи
        for i, entry in enumerate(current_entries, start=start_idx + 1):
            entry_text = f"{i}. {entry['time']} - {entry['text']}"
            message_lines.append(entry_text)
            
            # Кнопки действий для записи
            entry_idx = i - 1
            buttons.append([
                InlineKeyboardButton(
                    text=entry_text[:30] + "..." if len(entry_text) > 30 else entry_text,
                    callback_data=f"schedule_entry:{entry_idx}"
                )
            ])
            buttons.append([
                InlineKeyboardButton(text=f"{ACTION_ICONS['edit']}", callback_data=f"edit_schedule:{entry_idx}"),
                InlineKeyboardButton(text=f"{ACTION_ICONS['delete']}", callback_data=f"delete_schedule:{entry_idx}")
            ])
        
        # Добавляем навигацию
        if total_pages > 1:
            nav_buttons = []
            if page > 0:
                nav_buttons.append(InlineKeyboardButton(text=NAVIGATION_ICONS['prev'], callback_data="schedule_prev_page"))
            nav_buttons.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="ignore"))
            if page < total_pages - 1:
                nav_buttons.append(InlineKeyboardButton(text=NAVIGATION_ICONS['next'], callback_data="schedule_next_page"))
            buttons.append(nav_buttons)
        
        # Кнопки сортировки
        buttons.append([
            InlineKeyboardButton(text=f"{TIME_ICONS['clock']} По времени", callback_data="schedule_sort:time"),
            InlineKeyboardButton(text=f"{TIME_ICONS['calendar']} По дате", callback_data="schedule_sort:date")
        ])
        
        # Кнопка добавления записи
        buttons.append([InlineKeyboardButton(text=f"{ACTION_ICONS['add']} Добавить запись", callback_data="add_schedule")])
        
        if not schedule:
            message_lines.append("\nУ вас пока нет записей в расписании. Нажмите кнопку «Добавить запись», чтобы создать новую.")
        
        return InlineKeyboardMarkup(inline_keyboard=buttons), "\n".join(message_lines)

