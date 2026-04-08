"""
Логирование приложения
"""
import sys
from loguru import logger
from app.core.settings import settings


def setup_logger():
    """Настройка логгера"""
    # Удаляем стандартный обработчик
    logger.remove()
    
    # Консольный вывод
    logger.add(
        sys.stderr,
        level=settings.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        colorize=True,
        enqueue=True
    )
    
    # Файловый вывод с ротацией
    logger.add(
        settings.LOG_FILE,
        level=settings.LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        compression="zip",
        enqueue=True,
        encoding="utf-8"
    )
    
    # Отдельный файл для ошибок
    logger.add(
        "./logs/error.log",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="50 MB",
        retention="90 days",
        compression="zip",
        enqueue=True,
        encoding="utf-8",
        backtrace=True,
        diagnose=True
    )
    
    return logger


# Инициализация логгера
log = setup_logger()
