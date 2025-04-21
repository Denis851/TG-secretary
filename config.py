from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os
from dotenv import load_dotenv
from pydantic import Field

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    # Bot settings
    BOT_TOKEN: str = Field(..., env='BOT_TOKEN')
    USER_ID: Optional[int] = Field(None, env='USER_ID')
    
    # Redis settings
    REDIS_URL: str = Field(
        default='redis://localhost:6379',
        env='REDIS_URL'
    )
    REDIS_MAX_CONNECTIONS: int = Field(
        default=10,
        env='REDIS_MAX_CONNECTIONS'
    )
    REDIS_SOCKET_TIMEOUT: int = Field(
        default=5,
        env='REDIS_SOCKET_TIMEOUT'
    )
    
    # Database settings
    DATABASE_URL: str = Field(
        default='sqlite:///data/bot.db',
        env='DATABASE_URL'
    )
    
    # Logging settings
    LOG_LEVEL: str = Field(
        default='INFO',
        env='LOG_LEVEL'
    )
    LOG_FORMAT: str = Field(
        default='json',
        env='LOG_FORMAT'
    )
    
    # Timezone settings
    TZ: str = Field(
        default='Europe/Moscow',
        env='TZ'
    )
    
    # Rate limiting settings
    RATE_LIMIT: int = Field(
        default=20,
        env='RATE_LIMIT'
    )
    RATE_LIMIT_PERIOD: int = Field(
        default=60,
        env='RATE_LIMIT_PERIOD'
    )
    
    # Health check settings
    HEALTH_CHECK_INTERVAL: int = Field(
        default=300,
        env='HEALTH_CHECK_INTERVAL'
    )
    HEALTH_CHECK_TIMEOUT: int = Field(
        default=30,
        env='HEALTH_CHECK_TIMEOUT'
    )
    
    # Keep-alive settings
    KEEP_ALIVE_INTERVAL: int = Field(
        default=300,
        env='KEEP_ALIVE_INTERVAL'
    )
    KEEP_ALIVE_TIMEOUT: int = Field(
        default=60,
        env='KEEP_ALIVE_TIMEOUT'
    )
    
    # Paths configuration
    DATA_DIR: str = "data"
    CHECKLIST_PATH: str = os.path.join(DATA_DIR, "checklist.json")
    GOALS_PATH: str = os.path.join(DATA_DIR, "goals.json")
    SCHEDULE_PATH: str = os.path.join(DATA_DIR, "schedule.json")
    MOOD_PATH: str = os.path.join(DATA_DIR, "mood.json")
    
    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'

# Create global settings instance
settings = Settings()

# Ensure data directory exists
os.makedirs(settings.DATA_DIR, exist_ok=True)