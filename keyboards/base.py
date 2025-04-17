from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from typing import List, Dict, Any, Union

class BaseKeyboard:
    """Базовый класс для всех клавиатур"""
    
    @staticmethod
    def create_main_keyboard() -> ReplyKeyboardMarkup:
        """Создает основную клавиатуру с цветными кнопками"""
        return ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text=COLORED_BUTTONS["checklist"]),
                    KeyboardButton(text=COLORED_BUTTONS["goals"])
                ],
                [
                    KeyboardButton(text=COLORED_BUTTONS["progress"]),
                    KeyboardButton(text=COLORED_BUTTONS["mood"])
                ],
                [
                    KeyboardButton(text=COLORED_BUTTONS["schedule"]),
                    KeyboardButton(text=COLORED_BUTTONS["report"])
                ]
            ],
            resize_keyboard=True
        )
    
    @staticmethod
    def create_inline_keyboard(buttons_data: list) -> InlineKeyboardMarkup:
        """
        Создает inline клавиатуру из списка данных для кнопок
        :param buttons_data: список кортежей (текст, callback_data)
        :return: InlineKeyboardMarkup
        """
        keyboard = []
        for row in buttons_data:
            if isinstance(row, (list, tuple)):
                keyboard_row = []
                for button in row:
                    if isinstance(button, (list, tuple)):
                        text, callback_data = button
                        keyboard_row.append(InlineKeyboardButton(
                            text=text,
                            callback_data=callback_data
                        ))
                keyboard.append(keyboard_row)
            else:
                text, callback_data = row
                keyboard.append([InlineKeyboardButton(
                    text=text,
                    callback_data=callback_data
                )])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def create_reply_keyboard(buttons: list, resize_keyboard: bool = True, one_time_keyboard: bool = False) -> ReplyKeyboardMarkup:
        """
        Создает reply клавиатуру из списка текстов кнопок
        :param buttons: список текстов для кнопок
        :param resize_keyboard: подгонять размер кнопок
        :param one_time_keyboard: скрывать после использования
        :return: ReplyKeyboardMarkup
        """
        keyboard = []
        for row in buttons:
            if isinstance(row, (list, tuple)):
                keyboard_row = []
                for button_text in row:
                    keyboard_row.append(KeyboardButton(text=button_text))
                keyboard.append(keyboard_row)
            else:
                keyboard.append([KeyboardButton(text=row)])
        
        return ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=resize_keyboard,
            one_time_keyboard=one_time_keyboard
        ) 