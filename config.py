import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot settings
BOT_TOKEN = os.getenv("BOT_TOKEN")
USER_ID = int(os.getenv("USER_ID", 0))

# Paths configuration
DATA_DIR = "data"
CHECKLIST_PATH = os.path.join(DATA_DIR, "checklist.json")
GOALS_PATH = os.path.join(DATA_DIR, "goals.json")
SCHEDULE_PATH = os.path.join(DATA_DIR, "schedule.json")
MOOD_PATH = os.path.join(DATA_DIR, "mood.json")