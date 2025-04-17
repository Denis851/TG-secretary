import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "7934121929:AAFOhXnkKxBeIDUzk4_A6U-Jqg4xZH6o-ig")
USER_ID = 1243785780

DATA_DIR = "data"
CHECKLIST_PATH = os.path.join(DATA_DIR, "checklist.json")
GOALS_PATH = os.path.join(DATA_DIR, "goals.json")
SCHEDULE_PATH = os.path.join(DATA_DIR, "schedule.json")
MOOD_PATH = os.path.join(DATA_DIR, "mood.json")
