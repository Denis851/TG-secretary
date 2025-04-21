from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os
from dotenv import load_dotenv
from pydantic import Field, field_validator
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

def get_env_or_default(key: str, default: any) -> any:
    """Get environment variable or return default value"""
    value = os.getenv(key)
    if value is None:
        return default
    return value

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
    
    @field_validator('REDIS_PORT', 'REDIS_DB', mode='before')
    @classmethod
    def parse_int_fields(cls, v, info):
        # If value is None or empty, return default
        if v is None or v == '':
            return 6379 if info.field_name == 'REDIS_PORT' else 0
            
        # If it's already an integer, return it
        if isinstance(v, int):
            return v
            
        # If it's a string, try to parse it
        if isinstance(v, str):
            # Remove any shell-style variable substitution and get the first part
            v = v.replace('${', '').replace('}', '').split(':')[0]
            # If the value is the variable name itself, return default
            if v in ['REDIS_PORT', 'REDIS_DB']:
                return 6379 if info.field_name == 'REDIS_PORT' else 0
            try:
                return int(v)
            except ValueError:
                # If conversion fails, return default
                return 6379 if info.field_name == 'REDIS_PORT' else 0
                
        # For any other type, return default
        return 6379 if info.field_name == 'REDIS_PORT' else 0
    
    @property
    def redis_url(self) -> str:
        """Get Redis URL from environment or construct from components"""
        if self.REDIS_URL:
            # Clean up the URL if it contains template variables
            url = self.REDIS_URL.replace('${', '').replace('}', '')
            # If the URL is just the variable name, construct from components
            if url == 'REDIS_URL':
                auth = f"{self.REDIS_USER}:{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
                return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
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
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )

# Create global settings instance
settings = Settings()

# Ensure data directory exists
os.makedirs(settings.DATA_DIR, exist_ok=True)