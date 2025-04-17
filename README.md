# Telegram Secretary Bot

Бот-секретарь для управления целями, задачами и отслеживания продуктивности.

## Функциональность

- 🎯 Управление целями
- 📋 Управление задачами
- 📊 Отслеживание настроения
- 📅 Планирование
- 📈 Анализ продуктивности
- 📄 Генерация отчетов

## Развертывание на сервере

### Подготовка сервера

1. Установите необходимые пакеты:
```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip git
```

2. Клонируйте репозиторий:
```bash
git clone https://github.com/yourusername/TG-secretary.git
cd TG-secretary
```

3. Создайте и активируйте виртуальное окружение:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

4. Установите зависимости:
```bash
pip install -r requirements.txt
```

5. Настройте переменные окружения:
```bash
cp .env.example .env
nano .env  # Добавьте BOT_TOKEN
```

### Настройка systemd

1. Отредактируйте файл `tg-secretary.service`:
```bash
sudo nano /etc/systemd/system/tg-secretary.service
```

2. Замените пути и имя пользователя в файле сервиса.

3. Включите и запустите сервис:
```bash
sudo systemctl daemon-reload
sudo systemctl enable tg-secretary
sudo systemctl start tg-secretary
```

4. Проверьте статус:
```bash
sudo systemctl status tg-secretary
```

### Мониторинг логов

Просмотр логов сервиса:
```bash
sudo journalctl -u tg-secretary -f
```

### Обновление бота

1. Остановите сервис:
```bash
sudo systemctl stop tg-secretary
```

2. Обновите код:
```bash
cd /path/to/TG-secretary
git pull
```

3. Обновите зависимости:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

4. Запустите сервис:
```bash
sudo systemctl start tg-secretary
```

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/yourusername/TG-secretary.git
cd TG-secretary
```

2. Создайте виртуальное окружение и активируйте его:
```bash
python -m venv .venv
source .venv/bin/activate  # для Linux/macOS
# или
.venv\Scripts\activate  # для Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл `.env` и добавьте в него:
```
BOT_TOKEN=your_bot_token_here
```

5. Создайте необходимые директории:
```bash
mkdir -p data fonts reports
```

6. Скачайте шрифт DejaVu Sans:
```bash
curl -o fonts/DejaVuSans.ttf https://raw.githubusercontent.com/dejavu-fonts/dejavu-fonts/master/dejavu-fonts-ttf-2.37/ttf/DejaVuSans.ttf
```

## Запуск

```bash
python main.py
```

## Структура проекта

```
TG-secretary/
├── data/           # Файлы с данными
├── fonts/          # Шрифты для отчетов
├── handlers/       # Обработчики команд
├── keyboards/      # Клавиатуры
├── reports/        # Сгенерированные отчеты
├── services/       # Сервисы
├── main.py        # Основной файл
└── requirements.txt
```

## Расписание задач

- 09:00 - Отправка цитаты дня
- 20:00 - Запрос настроения
- 21:00 - Отчет по задачам
- Воскресенье 18:00 - Отчет по целям
- Воскресенье 19:00 - Анализ продуктивности 