import json
import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from config import CHECKLIST_PATH, GOALS_PATH, SCHEDULE_PATH, MOOD_PATH
import re

# Настройка логирования
logger = logging.getLogger(__name__)

class StorageError(Exception):
    """Базовый класс для ошибок хранилища"""
    pass

class FileAccessError(StorageError):
    """Ошибка доступа к файлу"""
    pass

class ValidationError(Exception):
    """Ошибка валидации данных"""
    pass

@dataclass
class ValidationRules:
    """Правила валидации для полей"""
    max_text_length: int = 500
    min_text_length: int = 1
    allowed_priorities: List[str] = ("высокий", "средний", "низкий")
    
class BaseStorage:
    """Базовый класс для работы с JSON хранилищем"""
    
    def __init__(self, filename: str):
        self.filename = filename
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        if not os.path.exists(filename):
            self.save_data([])
        self.validation_rules = ValidationRules()
    
    def load_data(self) -> List[Dict[str, Any]]:
        """
        Загружает данные из JSON файла
        
        Returns:
            List[Dict[str, Any]]: Список элементов
            
        Raises:
            StorageError: При проблемах с загрузкой данных
        """
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
            return json.load(f)
        except Exception as e:
            raise StorageError(f"Ошибка при загрузке данных: {str(e)}")
    
    def save_data(self, data: List[Dict[str, Any]]) -> None:
        """
        Сохраняет данные в JSON файл
        
        Args:
            data: Список элементов для сохранения
            
        Raises:
            StorageError: При проблемах с сохранением данных
        """
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise StorageError(f"Ошибка при сохранении данных: {str(e)}")
    
    def validate_text(self, text: str) -> None:
        """Проверяет текст на соответствие правилам"""
        if not isinstance(text, str):
            raise ValidationError("Текст должен быть строкой")
        
        text = text.strip()
        if len(text) < self.validation_rules.min_text_length:
            raise ValidationError("Текст слишком короткий")
        if len(text) > self.validation_rules.max_text_length:
            raise ValidationError(f"Текст не должен превышать {self.validation_rules.max_text_length} символов")
    
    def validate_priority(self, priority: str) -> None:
        """Проверяет приоритет на соответствие правилам"""
        if priority not in self.validation_rules.allowed_priorities:
            raise ValidationError(f"Недопустимый приоритет. Разрешены: {', '.join(self.validation_rules.allowed_priorities)}")
    
    def validate_deadline(self, deadline: Optional[str]) -> None:
        """Проверяет дедлайн на соответствие формату"""
        if deadline is not None:
            try:
                datetime.strptime(deadline, "%Y-%m-%d")
            except ValueError:
                raise ValidationError("Неверный формат даты. Используйте YYYY-MM-DD")

    def sort_items(self, items: List[Dict[str, Any]], sort_by: str = "priority", reverse: bool = False) -> List[Dict[str, Any]]:
        """
        Сортирует элементы по заданному критерию
        
        Args:
            items: Список элементов для сортировки
            sort_by: Критерий сортировки ('priority', 'status', 'date', 'deadline')
            reverse: Сортировать в обратном порядке
            
        Returns:
            List[Dict[str, Any]]: Отсортированный список
        """
        priority_order = {"высокий": 3, "средний": 2, "низкий": 1}
        
        if sort_by == "priority":
            return sorted(
                items,
                key=lambda x: (priority_order.get(x.get("priority", "средний"), 0)),
                reverse=not reverse
            )
        elif sort_by == "status":
            return sorted(
                items,
                key=lambda x: (x.get("completed", x.get("done", False)), x.get("completed_at", "")),
                reverse=not reverse
            )
        elif sort_by == "date":
            return sorted(
                items,
                key=lambda x: x.get("created_at", ""),
                reverse=not reverse
            )
        elif sort_by == "deadline":
            def deadline_key(x):
                deadline = x.get("deadline")
                if not deadline:
                    return datetime.max if reverse else datetime.min
                try:
                    return datetime.strptime(deadline, "%Y-%m-%d")
                except ValueError:
                    return datetime.max if reverse else datetime.min
            
            return sorted(items, key=deadline_key, reverse=reverse)
        
        return items

class TaskStorage(BaseStorage):
    """Класс для работы с задачами"""
    
    def __init__(self):
        super().__init__(CHECKLIST_PATH)
    
    def get_tasks(self) -> List[Dict[str, Any]]:
        """Получает список всех задач"""
        return self.load_data()
    
    def add_task(self, text: str, priority: str = "средний", deadline: Optional[str] = None) -> None:
        """
        Добавляет новую задачу
        
        Args:
            text: Текст задачи
            priority: Приоритет задачи
            deadline: Дедлайн в формате YYYY-MM-DD
            
        Raises:
            ValidationError: При невалидных данных
        """
        self.validate_text(text)
        self.validate_priority(priority)
        self.validate_deadline(deadline)
        
        tasks = self.get_tasks()
        tasks.append({
            "text": text.strip(),
            "priority": priority,
            "deadline": deadline,
            "completed": False,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        self.save_data(tasks)
    
    def update_task_status(self, index: int, completed: bool) -> None:
        """Обновляет статус задачи"""
        tasks = self.get_tasks()
        if not 0 <= index < len(tasks):
            raise ValidationError("Неверный индекс задачи")
        
        tasks[index]["completed"] = completed
        if completed:
            tasks[index]["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            tasks[index].pop("completed_at", None)
        
        self.save_data(tasks)

    def get_sorted_tasks(self, sort_by: str = "priority", reverse: bool = False) -> List[Dict[str, Any]]:
        """Получает отсортированный список задач"""
        tasks = self.get_tasks()
        return self.sort_items(tasks, sort_by, reverse)

class GoalStorage(BaseStorage):
    """Класс для работы с целями"""
    
    def __init__(self):
        super().__init__(GOALS_PATH)
    
    def get_goals(self) -> List[Dict[str, Any]]:
        """Получает список всех целей"""
        return self.load_data()
    
    def add_goal(self, text: str, priority: str = "средний", deadline: Optional[str] = None) -> None:
        """
        Добавляет новую цель
        
        Args:
            text: Текст цели
            priority: Приоритет цели
            deadline: Дедлайн в формате YYYY-MM-DD
            
        Raises:
            ValidationError: При невалидных данных
        """
        self.validate_text(text)
        self.validate_priority(priority)
        self.validate_deadline(deadline)
        
        goals = self.get_goals()
        goals.append({
            "text": text.strip(),
            "priority": priority,
            "deadline": deadline,
            "completed": False,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        self.save_data(goals)
    
    def update_goal_status(self, index: int, completed: bool) -> None:
        """Обновляет статус цели"""
        goals = self.get_goals()
        if not 0 <= index < len(goals):
            raise ValidationError("Неверный индекс цели")
        
        goals[index]["completed"] = completed
        if completed:
            goals[index]["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            goals[index].pop("completed_at", None)
        
        self.save_data(goals)

    def get_sorted_goals(self, sort_by: str = "priority", reverse: bool = False) -> List[Dict[str, Any]]:
        """Получает отсортированный список целей"""
        goals = self.get_goals()
        return self.sort_items(goals, sort_by, reverse)

class MoodStorage(BaseStorage):
    """Класс для работы с записями настроения"""
    
    def __init__(self):
        super().__init__(MOOD_PATH)
    
    def get_moods(self) -> List[Dict[str, Any]]:
        """Получает список всех записей о настроении"""
        return self.load_data()
    
    def add_mood(self, mood_data: Dict[str, Any]) -> None:
        """
        Добавляет новую запись о настроении
        
        Args:
            mood_data: Данные о настроении
            
        Raises:
            ValidationError: При невалидных данных
        """
        try:
            moods = self.get_moods()
            # Проверяем, что значение настроения является строкой и содержит число от 1 до 5
            value = str(mood_data.get('value', ''))
            if not value.isdigit() or int(value) < 1 or int(value) > 5:
                raise ValidationError("Значение настроения должно быть числом от 1 до 5")
            
            moods.append({
                'value': value,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            self.save_data(moods)
        except Exception as e:
            raise StorageError(f"Ошибка при сохранении настроения: {str(e)}")
    
    def get_recent_moods(self, limit: int = 7) -> List[Dict[str, Any]]:
        """Получает последние записи о настроении"""
        try:
            moods = self.get_moods()
            return sorted(moods, key=lambda x: x['timestamp'], reverse=True)[:limit]
        except Exception as e:
            raise StorageError(f"Ошибка при получении истории настроений: {str(e)}")

class ScheduleStorage(BaseStorage):
    """Класс для работы с расписанием"""
    
    def __init__(self):
        super().__init__(SCHEDULE_PATH)
    
    def get_schedule(self) -> List[Dict[str, Any]]:
        """Получает список всех пунктов расписания"""
        return self.load_data()
    
    def add_entry(self, time: str, text: str) -> None:
        """
        Добавляет новый пункт в расписание
        
        Args:
            time: Время в формате ЧЧ:ММ
            text: Текст пункта расписания
            
        Raises:
            ValidationError: При невалидных данных
        """
        if not self.validate_time_format(time):
            raise ValidationError("Неверный формат времени")
        if not text.strip():
            raise ValidationError("Текст не может быть пустым")
        
        schedule = self.get_schedule()
        schedule.append({
            "time": time,
            "text": text.strip()
        })
        self.save_data(sorted(schedule, key=lambda x: x["time"]))
    
    def update_entry_text(self, index: int, new_text: str) -> None:
        """Обновляет текст пункта расписания"""
        if not new_text.strip():
            raise ValidationError("Текст не может быть пустым")
        
        schedule = self.get_schedule()
        if not 0 <= index < len(schedule):
            raise ValidationError("Неверный индекс")
        
        schedule[index]["text"] = new_text.strip()
        self.save_data(schedule)
    
    def update_entry_time(self, index: int, new_time: str) -> None:
        """Обновляет время пункта расписания"""
        if not self.validate_time_format(new_time):
            raise ValidationError("Неверный формат времени")
        
        schedule = self.get_schedule()
        if not 0 <= index < len(schedule):
            raise ValidationError("Неверный индекс")
        
        schedule[index]["time"] = new_time
        self.save_data(sorted(schedule, key=lambda x: x["time"]))
    
    def delete_entry(self, index: int) -> Dict[str, Any]:
        """Удаляет пункт расписания"""
        schedule = self.get_schedule()
        if not 0 <= index < len(schedule):
            raise ValidationError("Неверный индекс")
        
        deleted = schedule.pop(index)
        self.save_data(schedule)
        return deleted
    
    @staticmethod
    def validate_time_format(time: str) -> bool:
        """Проверяет формат времени (ЧЧ:ММ)"""
        pattern = r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$'
        return bool(re.match(pattern, time))
    
    def get_sorted_schedule(self) -> List[Dict[str, Any]]:
        """Получает отсортированный по времени список пунктов расписания"""
        schedule = self.get_schedule()
        return sorted(schedule, key=lambda x: datetime.strptime(x.get("time", "00:00"), "%H:%M"))

# Создаем глобальные экземпляры для использования
task_storage = TaskStorage()
goal_storage = GoalStorage()
mood_storage = MoodStorage()
schedule_storage = ScheduleStorage()