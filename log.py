import logging
import os
from logging.handlers import RotatingFileHandler

# Создаем директорию для логов, если её нет
os.makedirs('logs', exist_ok=True)

# Настраиваем логгер
logger = logging.getLogger('bot_logger')
logger.setLevel(logging.INFO)

# Создаем форматтер для логов
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Добавляем обработчик для записи в файл
file_handler = RotatingFileHandler(
    'logs/bot.log',
    maxBytes=1024 * 1024,  # 1MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Добавляем обработчик для вывода в консоль
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler) 