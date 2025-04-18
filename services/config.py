import json
import os
from typing import Any, Optional

class Config:
    """Класс для работы с конфигурацией бота"""
    
    def __init__(self, config_path: str = "data/config.json"):
        self.config_path = config_path
        self._ensure_config_exists()
        
    def _ensure_config_exists(self) -> None:
        """Убеждается, что файл конфигурации существует"""
        if not os.path.exists(self.config_path):
            # Создаем директорию, если её нет
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            # Создаем файл с базовой конфигурацией
            self.save_config({
                "user_id": None,
                "timezone": "UTC",
                "notification_time": "09:00",
                "checklist_report_time": "21:00"
            })
    
    def load_config(self) -> dict:
        """Загружает конфигурацию из файла"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            return {}
            
    def save_config(self, config: dict) -> None:
        """Сохраняет конфигурацию в файл"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
            
    def get_user_id(self) -> Optional[int]:
        """Возвращает ID пользователя"""
        config = self.load_config()
        return config.get("user_id")
        
    def set_user_id(self, user_id: int) -> None:
        """Устанавливает ID пользователя"""
        config = self.load_config()
        config["user_id"] = user_id
        self.save_config(config)
        
    def get_setting(self, key: str) -> Any:
        """Получает значение настройки по ключу"""
        config = self.load_config()
        return config.get(key)
        
    def set_setting(self, key: str, value: Any) -> None:
        """Устанавливает значение настройки"""
        config = self.load_config()
        config[key] = value
        self.save_config(config) 