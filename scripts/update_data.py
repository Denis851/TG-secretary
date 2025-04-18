import json
from pathlib import Path

def update_goals():
    """Обновляет структуру данных целей"""
    goals_path = Path("data/goals.json")
    if not goals_path.exists():
        print("Файл goals.json не найден")
        return
        
    with open(goals_path, "r", encoding='utf-8') as f:
        goals = json.load(f)
    
    for goal in goals:
        goal["type"] = "goal"
        goal["progress"] = goal.get("progress", 0)
        goal["subtasks"] = goal.get("subtasks", [])
        
        # Конвертируем приоритеты в русский язык
        if goal["priority"] == "high":
            goal["priority"] = "высокий"
        elif goal["priority"] == "medium":
            goal["priority"] = "средний"
        elif goal["priority"] == "low":
            goal["priority"] = "низкий"
    
    with open(goals_path, "w", encoding='utf-8') as f:
        json.dump(goals, f, ensure_ascii=False, indent=2)
    print("Файл goals.json обновлен")

def update_tasks():
    """Обновляет структуру данных задач"""
    tasks_path = Path("data/checklist.json")
    if not tasks_path.exists():
        print("Файл checklist.json не найден")
        return
        
    with open(tasks_path, "r", encoding='utf-8') as f:
        tasks = json.load(f)
    
    for task in tasks:
        task["type"] = "task"
        # Убеждаемся, что приоритет на русском
        if task["priority"] == "high":
            task["priority"] = "высокий"
        elif task["priority"] == "medium":
            task["priority"] = "средний"
        elif task["priority"] == "low":
            task["priority"] = "низкий"
    
    with open(tasks_path, "w", encoding='utf-8') as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)
    print("Файл checklist.json обновлен")

if __name__ == "__main__":
    print("Начинаем обновление данных...")
    update_goals()
    update_tasks()
    print("Обновление завершено") 