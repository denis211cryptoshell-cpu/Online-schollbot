"""
Конфигурация приложения
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional
from pathlib import Path


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Bot
    BOT_TOKEN: str
    ADMIN_IDS: str
    MANAGER_CHAT_ID: str
    
    # Database
    DATABASE_TYPE: str = Field(default="sqlite", pattern="^(sqlite|postgresql)$")
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "school_bot"
    SQLITE_PATH: str = "./data/school_bot.db"
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    
    # Logging
    LOG_LEVEL: str = Field(default="DEBUG", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    LOG_FILE: str = "./logs/bot.log"
    LOG_ROTATION: str = "100 MB"
    LOG_RETENTION: str = "30 days"
    
    # Cache
    FAQ_CACHE_TTL: int = 3600
    LEAD_CACHE_TTL: int = 300
    
    # Backup
    BACKUP_ENABLED: bool = False
    BACKUP_SCHEDULE: str = "0 2 * * *"
    BACKUP_PROVIDER: str = Field(default="local", pattern="^(local|s3|gdrive)$")
    S3_BUCKET: Optional[str] = None
    S3_REGION: str = "eu-west-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    GDRIVE_FOLDER_ID: Optional[str] = None
    
    # Google Sheets
    GOOGLE_SHEETS_ENABLED: bool = False
    GOOGLE_SHEETS_ID: Optional[str] = None
    GOOGLE_CREDENTIALS_FILE: str = "./credentials/google_credentials.json"
    
    # Language
    DEFAULT_LANGUAGE: str = Field(default="ru", pattern="^(ru|en)$")
    
    # Rate Limiting
    RATE_LIMIT_MESSAGES: int = 5
    RATE_LIMIT_LEADS: int = 3
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
    
    @property
    def admin_ids(self) -> List[int]:
        """Получить список ID администраторов"""
        return [int(id.strip()) for id in self.ADMIN_IDS.split(",")]
    
    @property
    def database_url(self) -> str:
        """Получить URL базы данных"""
        if self.DATABASE_TYPE == "postgresql":
            return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        else:
            return f"sqlite+aiosqlite:///{self.SQLITE_PATH}"
    
    @property
    def redis_url(self) -> str:
        """Получить URL Redis"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


settings = Settings()
