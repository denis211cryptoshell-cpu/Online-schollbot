"""
Обработчик для экспорта заявок в Google Sheets
"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from app.core.logger import log
from app.core.settings import settings
from app.services.google_sheets_service import google_sheets_service
from app.services.lead_service import lead_service
from app.database.adapter import db_adapter
from app.database.models import LeadStatus

router = Router()


@router.message(Command("export"))
async def cmd_export(message: Message):
    """Ручной экспорт заявок в Google Sheets"""
    if message.from_user.id not in settings.admin_ids:
        await message.answer("⛔ У вас нет прав администратора.")
        return
    
    await message.answer("⏳ Экспорт заявок в Google Sheets...")
    
    try:
        # Инициализируем Google Sheets
        initialized = await google_sheets_service.initialize()
        
        if not initialized:
            await message.answer(
                "⚠️ Google Sheets не настроен.\n\n"
                "Проверьте:\n"
                "• GOOGLE_SHEETS_ENABLED=true\n"
                "• GOOGLE_SHEETS_ID указан\n"
                "• Файл credentials существует"
            )
            return
        
        # Получаем все заявки из БД
        async for db_session in db_adapter.get_session():
            try:
                leads = await lead_service.get_leads_by_status(
                    db_session=db_session,
                    status=LeadStatus.NEW,
                    limit=1000
                )
                
                exported = 0
                for lead in leads:
                    success = await google_sheets_service.add_lead(
                        lead_id=lead.id,
                        telegram_id=lead.telegram_id,
                        username=lead.username or "",
                        full_name=lead.full_name or "",
                        contact=lead.contact or "",
                        message_text=lead.message_text or "",
                        status=lead.status.value if lead.status else "new",
                        language=lead.language or "ru"
                    )
                    if success:
                        exported += 1
                
                await message.answer(
                    f"✅ Экспорт завершен!\n\n"
                    f"📝 Экспортировано заявок: {exported}\n"
                    f"📊 Всего в таблице: {len(await google_sheets_service.get_all_leads())}"
                )
                
                log.info(f"Manual export completed: {exported} leads")
                
            except Exception as e:
                log.error(f"Error during export: {e}")
                await message.answer("⚠️ Ошибка при экспорте заявок")
            break
    
    except Exception as e:
        log.error(f"Error initializing Google Sheets: {e}")
        await message.answer("⚠️ Ошибка при инициализации Google Sheets")


@router.message(Command("sync"))
async def cmd_sync(message: Message):
    """Синхронизация статусов с Google Sheets"""
    if message.from_user.id not in settings.admin_ids:
        await message.answer("⛔ У вас нет прав администратора.")
        return
    
    await message.answer("⏳ Синхронизация с Google Sheets...")
    
    try:
        # Получаем статистику из Google Sheets
        stats = await google_sheets_service.get_statistics()
        
        if not stats:
            await message.answer("⚠️ Не удалось получить данные из Google Sheets")
            return
        
        text = (
            "📊 Статистика из Google Sheets:\n\n"
            f"📝 Всего заявок: {stats.get('total', 0)}\n"
            f"🆕 Новые: {stats.get('new', 0)}\n"
            f"✅ Принятые: {stats.get('accepted', 0)}\n"
            f"📞 Перезвонить: {stats.get('callback', 0)}\n"
            f"❌ Отказ: {stats.get('rejected', 0)}"
        )
        
        await message.answer(text)
        log.info("Sync completed")
        
    except Exception as e:
        log.error(f"Error during sync: {e}")
        await message.answer("⚠️ Ошибка при синхронизации")


@router.message(Command("crm"))
async def cmd_crm(message: Message):
    """Показать текущий CRM бэкенд"""
    if message.from_user.id not in settings.admin_ids:
        await message.answer("⛔ У вас нет прав администратора.")
        return
    
    backend = "Google Sheets" if settings.GOOGLE_SHEETS_ENABLED else "Локальная БД"
    
    text = (
        f"🔧 <b>Текущий CRM бэкенд:</b> {backend}\n\n"
        f"📋 <b>Доступные бэкенды:</b>\n"
        f"• database - Локальная БД (SQLite/PostgreSQL)\n"
        f"• google_sheets - Google Sheets\n\n"
        f"Для переключения измените в .env:\n"
        f"<code>GOOGLE_SHEETS_ENABLED=true/false</code>"
    )
    
    await message.answer(text)
