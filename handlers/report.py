from aiogram import Router, F
from aiogram.types import Message
from services.report_generator import generate_full_report

router = Router()

@router.message(F.text == "/отчёт")
async def send_full_report(message: Message):
    pdf_path = "data/full_report.pdf"
    generate_full_report(pdf_path)
    await message.answer_document(open(pdf_path, "rb"), caption="📄 Отчёт по всем данным")

