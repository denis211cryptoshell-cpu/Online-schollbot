"""
Админ-панель для управления ботом
"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from app.core.logger import log
from app.core.settings import settings
from app.keyboards.manager_kb import get_admin_main_keyboard, get_faq_management_keyboard
from app.services.lead_service import lead_service
from app.database.adapter import db_adapter
from app.services.faq_service import faq_service
from app.services.google_sheets_service import google_sheets_service
from app.core.settings import settings
from datetime import datetime, timedelta

router = Router()


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Открыть админ-панель"""
    if message.from_user.id not in settings.admin_ids:
        log.warning(f"Unauthorized admin access attempt from {message.from_user.id}")
        await message.answer("⛔ У вас нет прав администратора.")
        return
    
    log.info(f"Admin panel opened by {message.from_user.id}")
    await message.answer(
        "🛠 Админ-панель бота\n\nВыберите действие:",
        reply_markup=get_admin_main_keyboard()
    )


@router.message(F.text == "📊 Статистика за день")
async def stats_day(message: Message):
    """Статистика за день"""
    if message.from_user.id not in settings.admin_ids:
        return
    
    async for db_session in db_adapter.get_session():
        try:
            stats = await lead_service.get_statistics(db_session, days=1)
            
            text = (
                f"📊 Статистика за день ({stats['start_date']})\n\n"
                f"📝 Всего заявок: {stats['total_leads']}\n"
            )
            
            for status, count in stats['status_breakdown'].items():
                emoji = {"new": "🆕", "accepted": "✅", "callback": "📞", "rejected": "❌"}.get(status, "📋")
                text += f"{emoji} {status}: {count}\n"
            
            await message.answer(text)
            
        except Exception as e:
            log.error(f"Error getting daily stats: {e}")
            await message.answer("⚠️ Ошибка при получении статистики")


@router.message(F.text == "📈 Статистика за неделю")
async def stats_week(message: Message):
    """Статистика за неделю"""
    if message.from_user.id not in settings.admin_ids:
        return
    
    async for db_session in db_adapter.get_session():
        try:
            stats = await lead_service.get_statistics(db_session, days=7)
            
            text = (
                f"📈 Статистика за неделю ({stats['start_date']} - {stats['end_date']})\n\n"
                f"📝 Всего заявок: {stats['total_leads']}\n"
            )
            
            for status, count in stats['status_breakdown'].items():
                emoji = {"new": "🆕", "accepted": "✅", "callback": "📞", "rejected": "❌"}.get(status, "📋")
                text += f"{emoji} {status}: {count}\n"
            
            await message.answer(text)
            
        except Exception as e:
            log.error(f"Error getting weekly stats: {e}")
            await message.answer("⚠️ Ошибка при получении статистики")


@router.message(F.text == "📅 Статистика за месяц")
async def stats_month(message: Message):
    """Статистика за месяц"""
    if message.from_user.id not in settings.admin_ids:
        return
    
    async for db_session in db_adapter.get_session():
        try:
            stats = await lead_service.get_statistics(db_session, days=30)
            
            text = (
                f"📅 Статистика за месяц ({stats['start_date']} - {stats['end_date']})\n\n"
                f"📝 Всего заявок: {stats['total_leads']}\n"
            )
            
            for status, count in stats['status_breakdown'].items():
                emoji = {"new": "🆕", "accepted": "✅", "callback": "📞", "rejected": "❌"}.get(status, "📋")
                text += f"{emoji} {status}: {count}\n"
            
            await message.answer(text)
            
        except Exception as e:
            log.error(f"Error getting monthly stats: {e}")
            await message.answer("⚠️ Ошибка при получении статистики")


@router.message(F.text == "🔥 Топ вопросов")
async def top_questions(message: Message):
    """Топ частых вопросов"""
    if message.from_user.id not in settings.admin_ids:
        return
    
    async for db_session in db_adapter.get_session():
        try:
            stats = await lead_service.get_statistics(db_session, days=30)
            
            text = "🔥 Топ-10 частых вопросов за месяц:\n\n"
            
            for i, faq in enumerate(stats['top_faqs'], 1):
                text += f"{i}. {faq['question']} ({faq['count']} раз)\n"
            
            await message.answer(text)
            
        except Exception as e:
            log.error(f"Error getting top questions: {e}")
            await message.answer("⚠️ Ошибка при получении топа вопросов")


@router.message(F.text == "⏱ Экономия времени")
async def time_saved(message: Message):
    """Статистика экономии времени"""
    if message.from_user.id not in settings.admin_ids:
        return
    
    async for db_session in db_adapter.get_session():
        try:
            # Примерный расчет: каждый FAQ ответ экономит ~3 минуты
            stats = await lead_service.get_statistics(db_session, days=7)
            faq_answers = sum(faq['count'] for faq in stats['top_faqs'])
            time_saved_minutes = faq_answers * 3
            time_saved_hours = time_saved_minutes / 60
            
            text = (
                f"⏱ Экономия времени за неделю:\n\n"
                f"💬 FAQ ответов: {faq_answers}\n"
                f"⏰ Сэкономлено времени: {time_saved_hours:.1f} часов\n\n"
                f"Средняя экономия: ~{time_saved_hours/7:.1f} часов в день"
            )
            
            await message.answer(text)
            
        except Exception as e:
            log.error(f"Error calculating time saved: {e}")
            await message.answer("⚠️ Ошибка при расчете экономии времени")


@router.message(F.text == "📝 Управление FAQ")
async def faq_management(message: Message):
    """Управление базой знаний FAQ"""
    if message.from_user.id not in settings.admin_ids:
        return
    
    await message.answer(
        "📝 Управление базой знаний\n\nВыберите действие:",
        reply_markup=get_faq_management_keyboard()
    )


@router.message(F.text == "🔄 Обновить кэш")
async def refresh_cache(message: Message):
    """Обновление кэша"""
    if message.from_user.id not in settings.admin_ids:
        return
    
    try:
        await faq_service.clear_cache()
        await message.answer("✅ Кэш FAQ успешно обновлен")
        log.info("FAQ cache refreshed by admin")
    except Exception as e:
        log.error(f"Error refreshing cache: {e}")
        await message.answer("⚠️ Ошибка при обновлении кэша")


@router.message(F.text == "📤 Экспорт в Google Sheets")
async def export_to_sheets(message: Message):
    """Экспорт заявок в Google Sheets"""
    if message.from_user.id not in settings.admin_ids:
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
                from app.database.models import Lead
                from sqlalchemy import select
                
                result = await db_session.execute(select(Lead))
                leads = result.scalars().all()
                
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
                    f"📝 Экспортировано заявок: {exported}"
                )
                
                log.info(f"Manual export completed: {exported} leads")
                
            except Exception as e:
                log.error(f"Error during export: {e}")
                await message.answer("⚠️ Ошибка при экспорте заявок")
            break
    
    except Exception as e:
        log.error(f"Error initializing Google Sheets: {e}")
        await message.answer("⚠️ Ошибка при инициализации Google Sheets")


@router.message(F.text == "🔧 CRM настройки")
async def crm_settings(message: Message):
    """Показать настройки CRM"""
    if message.from_user.id not in settings.admin_ids:
        return
    
    backend = "Google Sheets" if settings.GOOGLE_SHEETS_ENABLED else "Локальная БД"
    
    text = (
        f"🔧 <b>Текущий CRM бэкенд:</b> {backend}\n\n"
        f"📋 <b>Доступные бэкенды:</b>\n"
        f"• database - Локальная БД (SQLite/PostgreSQL)\n"
        f"• google_sheets - Google Sheets\n\n"
        f"⚙️ <b>Текущие настройки:</b>\n"
        f"• GOOGLE_SHEETS_ENABLED: {settings.GOOGLE_SHEETS_ENABLED}\n"
        f"• GOOGLE_SHEETS_ID: {settings.GOOGLE_SHEETS_ID or 'Не указан'}\n"
        f"• DATABASE_TYPE: {settings.DATABASE_TYPE}\n\n"
        f"Для переключения измените в .env:\n"
        f"<code>GOOGLE_SHEETS_ENABLED=true/false</code>"
    )
    
    await message.answer(text)
