from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import json
from datetime import datetime, timedelta
import os

# Ensure fonts directory exists
fonts_dir = 'fonts'
if not os.path.exists(fonts_dir):
    os.makedirs(fonts_dir)

# Register DejaVu Sans font
font_path = os.path.join(fonts_dir, 'DejaVuSans.ttf')
if os.path.exists(font_path):
    pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))
else:
    raise FileNotFoundError(f"Font file not found at {font_path}")

def load_json(filename):
    """Load data from a JSON file."""
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading {filename}: {e}")
    return []

def format_goal(goal):
    """Format a single goal for the report."""
    status = "✓" if goal.get("completed", False) else "□"
    priority_icons = {"high": "!", "medium": "~", "low": "-"}
    priority = priority_icons.get(goal.get("priority", "medium"), "~")
    
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
    return f"{num:d}/{total:d}"

def generate_full_report(output_path):
    """Generate a comprehensive PDF report combining checklist, goals and productivity data."""
    # Initialize PDF
    c = canvas.Canvas(output_path, pagesize=A4)
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
    try:
        c.save()
        print(f"Report successfully generated at {output_path}")
    except Exception as e:
        raise Exception(f"Failed to save report: {str(e)}")
