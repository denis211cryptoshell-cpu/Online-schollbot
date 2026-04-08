"""
Адаптер базы данных - поддержка SQLite и PostgreSQL
"""
from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.settings import settings
from app.core.logger import log

Base = declarative_base()

class DatabaseAdapter:
    """Адаптер для работы с базой данных"""
    
    def __init__(self):
        self.engine = None
        self.session_factory: Optional[async_sessionmaker] = None
        self._initialized = False
    
    async def initialize(self):
        """Инициализация подключения к БД"""
        if self._initialized:
            log.warning("Database already initialized")
            return
        
        db_url = settings.database_url
        log.info(f"Initializing database: {settings.DATABASE_TYPE}")
        log.debug(f"Database URL: {db_url}")
        
        # Создаем движок с оптимальными настройками
        if settings.DATABASE_TYPE == "postgresql":
            self.engine = create_async_engine(
                db_url,
                pool_size=20,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=3600,
                echo=settings.LOG_LEVEL == "DEBUG"
            )
        else:
            self.engine = create_async_engine(
                db_url,
                echo=settings.LOG_LEVEL == "DEBUG"
            )
        
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        self._initialized = True
        log.info("Database initialized successfully")
    
    async def close(self):
        """Закрытие подключения к БД"""
        if self.engine:
            await self.engine.dispose()
            self._initialized = False
            log.info("Database connection closed")
    
    async def get_session(self) -> AsyncSession:
        """Получить сессию базы данных"""
        if not self._initialized:
            await self.initialize()
        
        async with self.session_factory() as session:
            try:
                yield session
            except Exception as e:
                log.error(f"Database session error: {e}")
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def create_tables(self):
        """Создание всех таблиц"""
        if not self._initialized:
            await self.initialize()
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        log.info("Database tables created")


# Глобальный экземпляр
db_adapter = DatabaseAdapter()
