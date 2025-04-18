from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import json
from datetime import datetime, timedelta
import os
from pathlib import Path
import urllib.request
import logging
import ssl

logger = logging.getLogger(__name__)

# Ensure required directories exist
def ensure_directories():
    """Create necessary directories if they don't exist."""
    directories = ['fonts', 'reports', 'data']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)

def download_font():
    """Download DejaVu Sans font if it doesn't exist."""
    font_path = Path('fonts/DejaVuSans.ttf')
    if not font_path.exists():
        logger.info("Downloading DejaVu Sans font...")
        # Список URL-ов для скачивания шрифта
        font_urls = [
            "https://raw.githubusercontent.com/dejavu-fonts/dejavu-fonts/master/ttf/DejaVuSans.ttf",
            "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf",
            "https://cdn.jsdelivr.net/npm/@fontsource/dejavu-sans/files/dejavu-sans-latin-400-normal.ttf"
        ]
        
        # Создаем контекст SSL без проверки сертификата
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        success = False
        for url in font_urls:
            try:
                logger.info(f"Trying to download font from {url}")
                # Открываем URL с использованием созданного контекста SSL
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, context=ctx) as response, open(font_path, 'wb') as out_file:
                    out_file.write(response.read())
                logger.info("Font downloaded successfully")
                success = True
                break
            except Exception as e:
                logger.warning(f"Failed to download font from {url}: {e}")
                continue
        
        if not success:
            # Если не удалось скачать шрифт, используем встроенный шрифт Helvetica
            logger.warning("Could not download DejaVu Sans font. Using Helvetica instead.")
            return False
    return True

# Create directories and try to download font
ensure_directories()
use_dejavu = download_font()

# Register font
if use_dejavu:
    font_path = Path('fonts/DejaVuSans.ttf')
    if font_path.exists():
        pdfmetrics.registerFont(TTFont('DejaVuSans', str(font_path)))
    else:
        logger.warning("DejaVu Sans font not found. Using Helvetica.")
        pdfmetrics.registerFont(TTFont('DejaVuSans', 'Helvetica'))
else:
    logger.warning("Using Helvetica as fallback font.")
    pdfmetrics.registerFont(TTFont('DejaVuSans', 'Helvetica'))

def load_json(filename):
    """Load data from a JSON file."""
    try:
        file_path = Path(filename)
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading {filename}: {e}")
    return []

def format_goal(goal):
    """Format a single goal for the report."""
    status = "✓" if goal.get("completed", False) else "□"
    priority_icons = {"высокий": "!", "средний": "~", "низкий": "-"}
    priority = priority_icons.get(goal.get("priority", "средний"), "~")
    
    deadline = goal.get("deadline", "Без срока")
    if deadline != "Без срока":
        try:
            deadline_date = datetime.strptime(deadline, "%Y-%m-%d")
            deadline = deadline_date.strftime("%d.%m.%Y")
        except:
            pass
            
    return f"{status} {priority} {goal['text']} (до {deadline})"

def format_task(task):
    """Format a single task for the report."""
    status = "✓" if task.get("completed", False) else "□"
    return f"{status} {task['text']}"

def draw_wrapped_text(c, text, x, y, width, font_name, font_size, line_height):
    """Draw text that automatically wraps to the next line if too long."""
    c.setFont(font_name, font_size)
    words = text.split()
    line = ''
    
    for word in words:
        test_line = line + ' ' + word if line else word
        if c.stringWidth(test_line, font_name, font_size) < width:
            line = test_line
        else:
            if y < 50:  # Check if we're near the bottom of the page
                c.showPage()
                y = A4[1] - 50  # Reset to top of new page
                c.setFont(font_name, font_size)
            c.drawString(x, y, line)
            y -= line_height
            line = word
    
    if line:
        if y < 50:  # Check if we're near the bottom of the page
            c.showPage()
            y = A4[1] - 50  # Reset to top of new page
            c.setFont(font_name, font_size)
        c.drawString(x, y, line)
        y -= line_height
    
    return y

def format_number(num, total):
    """Format numbers for better readability."""
    return f"{num}/{total}"

def generate_full_report(output_path):
    """Generate a comprehensive PDF report combining checklist, goals and productivity data."""
    try:
        # Ensure the output directory exists
        output_dir = Path(output_path).parent
        output_dir.mkdir(exist_ok=True)
        
        # Initialize PDF
        c = canvas.Canvas(str(output_path), pagesize=A4)
        width, height = A4
        
        # Set initial position
        y = height - 50
        line_height = 20
        
        # Title
        c.setFont('DejaVuSans', 14)
        now = datetime.now()
        date_str = now.strftime("%d.%m.%Y")
        title = f'Отчет по продуктивности ({date_str})'
        c.drawString((width - c.stringWidth(title, 'DejaVuSans', 14)) / 2, y, title)
        y -= line_height * 2
        
        # Goals section
        c.setFont('DejaVuSans', 12)
        c.drawString(50, y, 'Цели:')
        y -= line_height
        
        goals = load_json('data/goals.json')
        if goals:
            for goal in goals:
                text = format_goal(goal)
                y = draw_wrapped_text(c, text, 50, y, width - 100, 'DejaVuSans', 12, line_height)
        else:
            c.drawString(50, y, 'Нет активных целей')
            y -= line_height
        y -= line_height
        
        # Tasks section
        if y < 100:  # Check if we need a new page
            c.showPage()
            y = height - 50
            c.setFont('DejaVuSans', 12)
        
        c.drawString(50, y, 'Задачи на сегодня:')
        y -= line_height
        
        tasks = load_json('data/checklist.json')
        if tasks:
            for task in tasks:
                text = format_task(task)
                y = draw_wrapped_text(c, text, 50, y, width - 100, 'DejaVuSans', 12, line_height)
        else:
            c.drawString(50, y, 'Нет активных задач')
            y -= line_height
        y -= line_height
        
        # Productivity section
        if y < 150:  # Check if we need a new page
            c.showPage()
            y = height - 50
            c.setFont('DejaVuSans', 12)
        
        c.drawString(50, y, 'Анализ продуктивности за неделю:')
        y -= line_height
        
        moods = load_json('data/moods.json')
        week_ago = now - timedelta(days=7)
        week_moods = [m for m in moods if datetime.fromisoformat(m['timestamp']) > week_ago]
        
        if week_moods:
            try:
                # Safely convert mood values to numbers
                mood_values = []
                for m in week_moods:
                    try:
                        value = float(m['value'])
                        if 0 <= value <= 5:  # Validate range
                            mood_values.append(value)
                    except (ValueError, TypeError):
                        continue
                
                if mood_values:
                    avg_mood = sum(mood_values) / len(mood_values)
                    c.drawString(50, y, f'Средняя оценка настроения: {avg_mood:.1f}/5')
                    y -= line_height
                else:
                    c.drawString(50, y, 'Нет валидных данных о настроении')
                    y -= line_height
                
                # Count completed tasks
                tasks = load_json('data/checklist.json')
                completed_tasks = sum(1 for t in tasks if t.get('completed', False))
                total_tasks = len(tasks)
                c.drawString(50, y, f'Выполнено задач: {format_number(completed_tasks, total_tasks)}')
                y -= line_height
                
                # Count completed goals
                goals = load_json('data/goals.json')
                completed_goals = sum(1 for g in goals if g.get('completed', False))
                total_goals = len(goals)
                c.drawString(50, y, f'Достигнуто целей: {format_number(completed_goals, total_goals)}')
                y -= line_height
                
            except Exception as e:
                c.drawString(50, y, f'Ошибка при анализе данных: {str(e)}')
                y -= line_height
        else:
            c.drawString(50, y, 'Нет данных о продуктивности за последнюю неделю')
            y -= line_height
        
        # Save the report
        c.save()
        print(f"Report successfully generated at {output_path}")
        
    except Exception as e:
        raise Exception(f"Failed to generate report: {str(e)}")
