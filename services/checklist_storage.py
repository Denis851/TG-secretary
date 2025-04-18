import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

class ChecklistStorage:
    """Класс для работы с хранилищем задач"""
    
    def __init__(self, storage_path: str = "data/checklist.json"):
        self.storage_path = storage_path
        self._ensure_storage_exists()
        
    def _ensure_storage_exists(self) -> None:
        """Убеждается, что файл хранилища существует"""
        if not os.path.exists(self.storage_path):
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            self.save_tasks([])
            
    def get_tasks(self) -> List[Dict[str, Any]]:
        """Получает список всех задач"""
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
            
    def save_tasks(self, tasks: List[Dict[str, Any]]) -> None:
        """Сохраняет список задач"""
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(tasks, f, ensure_ascii=False, indent=2)
            
    def add_task(self, text: str, priority: str = "medium", deadline: Optional[str] = None) -> None:
        """Добавляет новую задачу"""
        tasks = self.get_tasks()
        
        new_task = {
            "text": text,
            "priority": priority,
            "deadline": deadline,
            "completed": False,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        tasks.append(new_task)
        self.save_tasks(tasks)
        
    def update_task(self, index: int, **kwargs) -> None:
        """Обновляет задачу по индексу"""
        tasks = self.get_tasks()
        if 0 <= index < len(tasks):
            tasks[index].update(kwargs)
            self.save_tasks(tasks)
            
    def delete_task(self, index: int) -> None:
        """Удаляет задачу по индексу"""
        tasks = self.get_tasks()
        if 0 <= index < len(tasks):
            tasks.pop(index)
            self.save_tasks(tasks)
            
    def toggle_task(self, index: int) -> None:
        """Переключает статус выполнения задачи"""
        tasks = self.get_tasks()
        if 0 <= index < len(tasks):
            tasks[index]["completed"] = not tasks[index].get("completed", False)
            if tasks[index]["completed"]:
                tasks[index]["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            else:
                tasks[index].pop("completed_at", None)
            self.save_tasks(tasks) 