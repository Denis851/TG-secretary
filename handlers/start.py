# -*- coding: utf-8 -*-
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from keyboards.main import get_main_keyboard

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я — твой фокус-ассистент\n\n"
        "— соблюдать распорядок дня\n"
        "— достигать целей\n"
        "— отслеживать задачи\n"
        "— контролировать настроение\n"
        "— получать мотивацию",
        reply_markup=get_main_keyboard()
    )
