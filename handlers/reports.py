from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile
from services.report_generator import generate_full_report
import os
from datetime import datetime

router = Router()

async def generate_and_send_report(message: Message, user_id: int = None):
    """Generate and send a productivity report."""
    try:
        # Create reports directory if it doesn't exist
        os.makedirs("reports", exist_ok=True)
        
        # Generate report filename with timestamp
        now = datetime.now().strftime("%Y-%m-%d_%H-%M")
        user_id = user_id or message.from_user.id
        report_path = f"reports/report_{user_id}_{now}.pdf"
        
        # Generate the report
        generate_full_report(report_path)
        
        # Read and send the file
        with open(report_path, 'rb') as file:
            bytes_data = file.read()
            document = BufferedInputFile(bytes_data, filename=f"report_{now}.pdf")
            await message.answer_document(
                document=document,
                caption="📊 Сводный отчет по задачам, целям и продуктивности"
            )
            
        # Clean up
        os.remove(report_path)
        return True
        
    except Exception as e:
        await message.answer(f"❌ Произошла ошибка при создании отчета: {str(e)}")
        return False

@router.message(F.text == "📊 Отчет")
async def handle_report_command(message: Message):
    """Handle the report command."""
    await generate_and_send_report(message) 