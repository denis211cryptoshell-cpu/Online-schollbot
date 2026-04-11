"""
Главный файл запуска бота
"""
import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.core.settings import settings
from app.core.logger import log
from app.database.adapter import db_adapter
from app.services.redis_client import redis_client
from app.services.notification_service import init_notification_service
from app.services.crm_adapter import crm_adapter
from app.database.seed import seed_faqs
from app.handlers.main_handler import router as main_router
from app.handlers.admin_handler import router as admin_router
from app.handlers.admin_extended import router as admin_extended_router
from app.handlers.export_handler import router as export_router
from app.handlers.callback_handler import router as callback_router
from app.handlers.manager_commands import router as manager_commands_router
from app.handlers.ban_handler import router as ban_router
from app.handlers.ban_management import router as ban_management_router
from app.middleware import RateLimitMiddleware, CallbackRateLimitMiddleware


async def on_startup(bot: Bot):
    """Действия при запуске бота"""
    log.info("Bot is starting up...")
    
    # Инициализация базы данных
    await db_adapter.initialize()
    await db_adapter.create_tables()
    log.info("Database initialized")
    
    # Заполняем FAQ начальными данными
    async for db_session in db_adapter.get_session():
        try:
            count = await seed_faqs(db_session)
            if count > 0:
                log.info(f"Seeded {count} FAQs")
        except Exception as e:
            log.error(f"Error seeding FAQs: {e}")
        break
    
    # Инициализация Redis
    await redis_client.initialize()
    log.info("Redis initialized")
    
    # Инициализация CRM (Google Sheets если включен)
    await crm_adapter.initialize()
    log.info(f"CRM adapter initialized with backend: {crm_adapter.backend}")
    
    # Инициализация сервиса уведомлений
    init_notification_service(bot)
    log.info("Notification service initialized")
    
    # Отправляем сообщение о запуске
    try:
        for admin_id in settings.admin_ids:
            await bot.send_message(
                chat_id=admin_id,
                text="🚀 <b>Бот запущен!</b>\n\n"
                     "✅ База данных подключена\n"
                     "✅ Redis кэш активен\n"
                     "✅ FAQ загружены\n"
                     "✅ Уведомления менеджеру включены\n\n"
                     "Готов к работе!"
            )
    except Exception as e:
        log.warning(f"Could not send startup message to admins: {e}")
    
    log.info("Bot startup completed")


async def on_shutdown():
    """Действия при остановке бота"""
    log.info("Bot is shutting down...")
    
    # Закрытие Redis
    await redis_client.close()
    
    # Закрытие БД
    await db_adapter.close()
    
    log.info("Bot shutdown completed")


async def main():
    """Основная функция запуска"""
    # Создаем директорию для логов если нет
    os.makedirs("./logs", exist_ok=True)
    os.makedirs("./data", exist_ok=True)
    
    # Инициализация бота
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Инициализация диспетчера с FSM storage
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Подключение middleware для rate limiting
    dp.message.middleware(RateLimitMiddleware())
    dp.callback_query.middleware(CallbackRateLimitMiddleware())
    log.info("Rate limiting middleware enabled")

    # Регистрация роутеров (порядок важен!)
    dp.include_router(callback_router)             # Inline callback (первый!)
    dp.include_router(ban_router)                  # Бан/разбан (команды)
    dp.include_router(ban_management_router)       # Управление банами (UI)
    dp.include_router(admin_extended_router)       # Расширенная админка
    dp.include_router(manager_commands_router)     # Команды менеджера
    dp.include_router(export_router)               # Экспорт и CRM команды
    dp.include_router(admin_router)
    dp.include_router(main_router)                 # Основной обработчик (с проверкой намерений)
    
    # Регистрация обработчиков startup/shutdown
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Запуск polling
    log.info("Starting bot polling...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        log.error(f"Error during polling: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Bot stopped by user")
    except Exception as e:
        log.critical(f"Fatal error: {e}")
