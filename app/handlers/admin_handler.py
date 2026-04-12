"""
Админ-панель для управления ботом
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy import select
from app.core.logger import log
from app.core.settings import settings
from app.keyboards.admin_ban_kb import get_admin_main_inline_keyboard
from app.services.lead_service import lead_service
from app.database.adapter import db_adapter
from app.services.faq_service import faq_service
from app.services.google_sheets_service import google_sheets_service
from app.database.models import FAQ
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
        reply_markup=get_admin_main_inline_keyboard()
    )


# ========== INLINE КНОПКИ АДМИН-ПАНЕЛИ ==========

@router.callback_query(F.data == "stats_day")
async def callback_stats_day(callback: CallbackQuery):
    """Статистика за день"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    log.info(f"[Admin] Admin {callback.from_user.id} clicked: stats_day")

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

            try:
                await callback.message.edit_text(text, reply_markup=get_admin_main_inline_keyboard())
            except Exception:
                await callback.message.answer(text, reply_markup=get_admin_main_inline_keyboard())

        except Exception as e:
            log.error(f"Error getting daily stats: {e}")
            await callback.answer("⚠️ Ошибка при получении статистики", show_alert=True)

        break

    await callback.answer()


@router.callback_query(F.data == "stats_week")
async def callback_stats_week(callback: CallbackQuery):
    """Статистика за неделю"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    log.info(f"[Admin] Admin {callback.from_user.id} clicked: stats_week")

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

            try:
                await callback.message.edit_text(text, reply_markup=get_admin_main_inline_keyboard())
            except Exception:
                await callback.message.answer(text, reply_markup=get_admin_main_inline_keyboard())

        except Exception as e:
            log.error(f"Error getting weekly stats: {e}")
            await callback.answer("⚠️ Ошибка при получении статистики", show_alert=True)

        break

    await callback.answer()


@router.callback_query(F.data == "stats_month")
async def callback_stats_month(callback: CallbackQuery):
    """Статистика за месяц"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    log.info(f"[Admin] Admin {callback.from_user.id} clicked: stats_month")

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

            try:
                await callback.message.edit_text(text, reply_markup=get_admin_main_inline_keyboard())
            except Exception:
                await callback.message.answer(text, reply_markup=get_admin_main_inline_keyboard())

        except Exception as e:
            log.error(f"Error getting monthly stats: {e}")
            await callback.answer("⚠️ Ошибка при получении статистики", show_alert=True)

        break

    await callback.answer()


@router.callback_query(F.data == "top_questions")
async def callback_top_questions(callback: CallbackQuery):
    """Топ частых вопросов"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    log.info(f"[Admin] Admin {callback.from_user.id} clicked: top_questions")

    async for db_session in db_adapter.get_session():
        try:
            stats = await lead_service.get_statistics(db_session, days=30)

            text = "🔥 Топ-10 частых вопросов за месяц:\n\n"

            for i, faq in enumerate(stats['top_faqs'], 1):
                text += f"{i}. {faq['question']} ({faq['count']} раз)\n"

            try:
                await callback.message.edit_text(text, reply_markup=get_admin_main_inline_keyboard())
            except Exception:
                await callback.message.answer(text, reply_markup=get_admin_main_inline_keyboard())

        except Exception as e:
            log.error(f"Error getting top questions: {e}")
            await callback.answer("⚠️ Ошибка при получении топа вопросов", show_alert=True)

        break

    await callback.answer()


@router.callback_query(F.data == "time_saved")
async def callback_time_saved(callback: CallbackQuery):
    """Статистика экономии времени"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    log.info(f"[Admin] Admin {callback.from_user.id} clicked: time_saved")

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

            try:
                await callback.message.edit_text(text, reply_markup=get_admin_main_inline_keyboard())
            except Exception:
                await callback.message.answer(text, reply_markup=get_admin_main_inline_keyboard())

        except Exception as e:
            log.error(f"Error calculating time saved: {e}")
            await callback.answer("⚠️ Ошибка при расчете экономии времени", show_alert=True)

        break

    await callback.answer()

  
# ========== FAQ ����������� ���������� � callback_handler.py ==========  
# �� callback'� ��� FAQ ⥯��� � callback_handler.py 
