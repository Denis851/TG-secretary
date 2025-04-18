from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile
from services.report_generator import generate_full_report
import os
from datetime import datetime
from pathlib import Path

router = Router()

async def generate_and_send_report(message: Message, user_id: int = None):
    """Generate and send a productivity report."""
    try:
        # Create reports directory if it doesn't exist
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        
        # Generate report filename with timestamp
        now = datetime.now().strftime("%Y-%m-%d_%H-%M")
        user_id = user_id or message.from_user.id
        report_filename = f"report_{user_id}_{now}.pdf"
        report_path = reports_dir / report_filename
        
        # Generate the report
        generate_full_report(str(report_path))
        
        # Read and send the file
        if report_path.exists():
            with open(report_path, 'rb') as file:
                bytes_data = file.read()
                document = BufferedInputFile(bytes_data, filename=f"report_{now}.pdf")
                await message.answer_document(
                    document=document,
                    caption="📊 Сводный отчет по задачам, целям и продуктивности"
                )
            
            # Clean up
            report_path.unlink()
            return True
        else:
            raise FileNotFoundError("Отчет не был создан")
        
    except Exception as e:
        await message.answer(f"❌ Произошла ошибка при создании отчета: {str(e)}")
        return False

@router.message(F.text == "📊 Отчет")
async def handle_report_command(message: Message):
    """Handle the report command."""
    await generate_and_send_report(message) 