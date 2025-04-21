from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os
from dotenv import load_dotenv
from pydantic import Field
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    # Bot settings
    BOT_TOKEN: str = Field(..., env='BOT_TOKEN')
    USER_ID: Optional[int] = Field(None, env='USER_ID')
    
    # Redis settings
    REDIS_URL: Optional[str] = Field(None, env='REDIS_URL')
    REDIS_HOST: str = Field(
        default='redis',
        env='REDIS_HOST'
    )
    REDIS_PORT: int = Field(
        default=6379,
        env='REDIS_PORT'
    )
    REDIS_DB: int = Field(
        default=0,
        env='REDIS_DB'
    )
    REDIS_PASSWORD: Optional[str] = Field(
        default=None,
        env='REDIS_PASSWORD'
    )
    REDIS_USER: str = Field(
        default='default',
        env='REDIS_USER'
    )
    
    @property
    def redis_url(self) -> str:
        """Get Redis URL from environment or construct from components"""
        if self.REDIS_URL:
            # Clean up the URL if it contains template variables
            url = self.REDIS_URL.replace('${{', '').replace('}}', '')
            return url
            
        # Construct Redis URL from components
        auth = f"{self.REDIS_USER}:{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
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