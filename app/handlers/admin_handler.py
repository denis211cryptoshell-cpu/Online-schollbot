"""
Админ-панель для управления ботом
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from app.core.logger import log
from app.core.settings import settings
from app.keyboards.manager_kb import get_admin_main_keyboard
from app.keyboards.admin_faq_kb import (
    get_faq_management_inline_keyboard,
    get_faq_edit_select_keyboard,
    get_faq_delete_select_keyboard,
    get_faq_fsm_back_keyboard,
    get_faq_list_keyboard,
    get_faq_view_keyboard,
    get_faq_edit_keyboard,
    get_faq_delete_confirm_keyboard,
    get_faq_list_back_keyboard,
)
from app.services.lead_service import lead_service
from app.database.adapter import db_adapter
from app.services.faq_service import faq_service
from app.services.google_sheets_service import google_sheets_service
from app.database.models import FAQ
from app.handlers.admin_extended import FAQAdd
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
    """Управление базой знаний FAQ — показывает inline кнопки"""
    if message.from_user.id not in settings.admin_ids:
        return

    log.info(f"FAQ management opened by admin {message.from_user.id}")
    await message.answer(
        "📝 <b>Управление базой знаний</b>\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=get_faq_management_inline_keyboard()
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


# ========== INLINE КНОПКИ УПРАВЛЕНИЯ FAQ ==========

@router.callback_query(F.data == "faq_management")
async def callback_faq_management(callback: CallbackQuery):
    """Главное меню управления FAQ"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    log.info(f"[FAQ] Admin {callback.from_user.id} opened FAQ management menu")
    try:
        await callback.message.edit_text(
            "📝 <b>Управление базой знаний</b>\n\n"
            "Выберите действие:",
            parse_mode="HTML",
            reply_markup=get_faq_management_inline_keyboard()
        )
    except Exception:
        # Если сообщение нельзя отредактировать (например, это не то же самое сообщение)
        await callback.message.answer(
            "📝 <b>Управление базой знаний</b>\n\n"
            "Выберите действие:",
            parse_mode="HTML",
            reply_markup=get_faq_management_inline_keyboard()
        )
    await callback.answer()


@router.callback_query(F.data == "faq_add")
async def callback_faq_add(callback: CallbackQuery, state: FSMContext):
    """Inline кнопка — добавить FAQ"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    log.info(f"[FAQ] Admin {callback.from_user.id} clicked: faq_add")
    try:
        await callback.message.edit_text(
            "➕ <b>Добавление нового вопроса FAQ</b>\n\n"
            "Введите вопрос на русском:",
            parse_mode="HTML",
            reply_markup=get_faq_fsm_back_keyboard()
        )
    except Exception:
        await callback.message.answer(
            "➕ <b>Добавление нового вопроса FAQ</b>\n\n"
            "Введите вопрос на русском:",
            parse_mode="HTML",
            reply_markup=get_faq_fsm_back_keyboard()
        )
    await state.set_state(FAQAdd.waiting_for_question_ru)
    await callback.answer()


@router.callback_query(F.data == "faq_list")
async def callback_faq_list(callback: CallbackQuery):
    """Inline кнопка — список FAQ"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    log.info(f"[FAQ] Admin {callback.from_user.id} clicked: faq_list")
    await callback.answer("Загружаю список FAQ...")

    async for db_session in db_adapter.get_session():
        try:
            result = await db_session.execute(
                select(FAQ).order_by(FAQ.usage_count.desc()).limit(20)
            )
            faqs = result.scalars().all()

            if not faqs:
                try:
                    await callback.message.edit_text("📋 База знаний пуста")
                except Exception:
                    await callback.message.answer("📋 База знаний пуста")
                break

            text = "📋 <b>Список вопросов (топ-20)</b>\n\n"

            for faq in faqs:
                status = "✅" if faq.is_active else "❌"
                text += (
                    f"{status} <b>#{faq.id}</b> - {faq.question_ru}\n"
                    f"   👁 {faq.usage_count} использований\n"
                    f"   🔑 {faq.keywords[:50]}...\n\n"
                )

            try:
                await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_faq_list_back_keyboard())
            except Exception:
                await callback.message.answer(text, parse_mode="HTML", reply_markup=get_faq_list_back_keyboard())

            log.info(f"[FAQ] List shown to admin {callback.from_user.id}: {len(faqs)} items")

        except Exception as e:
            log.error(f"[FAQ] Error listing FAQs via inline button: {e}")
            try:
                await callback.message.edit_text("⚠️ Ошибка при загрузке списка FAQ")
            except Exception:
                await callback.message.answer("⚠️ Ошибка при загрузке списка FAQ")

        break


@router.callback_query(F.data == "faq_edit_select")
async def callback_faq_edit_select(callback: CallbackQuery):
    """Inline кнопка — редактировать FAQ (список с кнопками на каждый)"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    log.info(f"[FAQ] Admin {callback.from_user.id} clicked: faq_edit_select")

    async for db_session in db_adapter.get_session():
        try:
            result = await db_session.execute(
                select(FAQ).order_by(FAQ.id.desc()).limit(10)
            )
            faqs = result.scalars().all()

            if not faqs:
                try:
                    await callback.message.edit_text("📋 База знаний пуста")
                except Exception:
                    await callback.message.answer("📋 База знаний пуста")
                await callback.answer("База знаний пуста", show_alert=True)
                break

            # Показываем inline-кнопки для каждого FAQ
            try:
                await callback.message.edit_text(
                    "✏️ <b>Редактирование FAQ</b>\n\n"
                    "Выберите вопрос для редактирования:",
                    parse_mode="HTML",
                    reply_markup=get_faq_edit_select_keyboard(
                        [{"id": f.id, "question_ru": f.question_ru, "is_active": f.is_active} for f in faqs]
                    )
                )
            except Exception:
                await callback.message.answer(
                    "✏️ <b>Редактирование FAQ</b>\n\n"
                    "Выберите вопрос для редактирования:",
                    parse_mode="HTML",
                    reply_markup=get_faq_edit_select_keyboard(
                        [{"id": f.id, "question_ru": f.question_ru, "is_active": f.is_active} for f in faqs]
                    )
                )

            log.info(f"[FAQ] Edit select shown to admin {callback.from_user.id}: {len(faqs)} items")
            await callback.answer()

        except Exception as e:
            log.error(f"[FAQ] Error showing FAQ edit select: {e}")
            try:
                await callback.message.edit_text("⚠️ Ошибка при загрузке списка FAQ")
            except Exception:
                await callback.message.answer("⚠️ Ошибка при загрузке списка FAQ")
            await callback.answer("Ошибка", show_alert=True)

        break


@router.callback_query(F.data == "faq_delete_select")
async def callback_faq_delete_select(callback: CallbackQuery):
    """Inline кнопка — удалить FAQ (список с кнопками на каждый)"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    log.info(f"[FAQ] Admin {callback.from_user.id} clicked: faq_delete_select")

    async for db_session in db_adapter.get_session():
        try:
            result = await db_session.execute(
                select(FAQ).order_by(FAQ.id.desc()).limit(10)
            )
            faqs = result.scalars().all()

            if not faqs:
                try:
                    await callback.message.edit_text("📋 База знаний пуста")
                except Exception:
                    await callback.message.answer("📋 База знаний пуста")
                await callback.answer("База знаний пуста", show_alert=True)
                break

            # Показываем inline-кнопки для каждого FAQ
            try:
                await callback.message.edit_text(
                    "🗑 <b>Удаление FAQ</b>\n\n"
                    "Выберите вопрос для удаления:",
                    parse_mode="HTML",
                    reply_markup=get_faq_delete_select_keyboard(
                        [{"id": f.id, "question_ru": f.question_ru, "is_active": f.is_active} for f in faqs]
                    )
                )
            except Exception:
                await callback.message.answer(
                    "🗑 <b>Удаление FAQ</b>\n\n"
                    "Выберите вопрос для удаления:",
                    parse_mode="HTML",
                    reply_markup=get_faq_delete_select_keyboard(
                        [{"id": f.id, "question_ru": f.question_ru, "is_active": f.is_active} for f in faqs]
                    )
                )

            log.info(f"[FAQ] Delete select shown to admin {callback.from_user.id}: {len(faqs)} items")
            await callback.answer()

        except Exception as e:
            log.error(f"[FAQ] Error showing FAQ delete select: {e}")
            try:
                await callback.message.edit_text("⚠️ Ошибка при загрузке списка FAQ")
            except Exception:
                await callback.message.answer("⚠️ Ошибка при загрузке списка FAQ")
            await callback.answer("Ошибка", show_alert=True)

        break


@router.callback_query(F.data == "faq_back_to_admin")
async def callback_faq_back_to_admin(callback: CallbackQuery, state: FSMContext):
    """Inline кнопка — назад в главное меню админа (из FAQ управления)"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    await state.clear()
    log.info(f"[FAQ] Admin {callback.from_user.id} clicked: faq_back_to_admin")
    try:
        await callback.message.edit_text(
            "🛠 Админ-панель бота\n\nВыберите действие:",
            reply_markup=get_admin_main_keyboard()
        )
    except Exception:
        await callback.message.answer(
            "🛠 Админ-панель бота\n\nВыберите действие:",
            reply_markup=get_admin_main_keyboard()
        )
    await callback.answer()


@router.callback_query(F.data == "faq_back_to_menu")
async def callback_faq_back_to_menu(callback: CallbackQuery):
    """Inline кнопка — назад к управлению FAQ (из списка)"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    log.info(f"[FAQ] Admin {callback.from_user.id} clicked: faq_back_to_menu")
    try:
        await callback.message.edit_text(
            "📝 <b>Управление базой знаний</b>\n\nВыберите действие:",
            parse_mode="HTML",
            reply_markup=get_faq_management_inline_keyboard()
        )
    except Exception:
        await callback.message.answer(
            "📝 <b>Управление базой знаний</b>\n\nВыберите действие:",
            parse_mode="HTML",
            reply_markup=get_faq_management_inline_keyboard()
        )
    await callback.answer()


@router.callback_query(F.data.startswith("faq_list_page_"))
async def callback_faq_list_page(callback: CallbackQuery):
    """Пагинация списка FAQ"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    try:
        page = int(callback.data.split("_")[3])
    except (ValueError, IndexError):
        await callback.answer("⚠️ Ошибка", show_alert=True)
        return

    log.info(f"[FAQ] Admin {callback.from_user.id} viewing FAQ list page {page}")

    async for db_session in db_adapter.get_session():
        try:
            result = await db_session.execute(
                select(FAQ).order_by(FAQ.usage_count.desc()).limit(20)
            )
            faqs = result.scalars().all()

            if not faqs:
                await callback.answer("Список пуст", show_alert=True)
                break

            # Пагинация на клиенте
            page_size = 5
            start = (page - 1) * page_size
            end = start + page_size
            page_faqs = faqs[start:end]

            text = f"📋 <b>Список (стр. {page})</b>\n\n"
            for faq in page_faqs:
                status = "✅" if faq.is_active else "❌"
                text += f"{status} <b>#{faq.id}</b> - {faq.question_ru}\n"
                text += f"   👁 {faq.usage_count} | 🔑 {faq.keywords[:40]}...\n\n"

            kb = get_faq_list_keyboard(faqs, page=page)
            try:
                await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
            except Exception:
                await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)

            await callback.answer()

        except Exception as e:
            log.error(f"[FAQ] Error on FAQ list page: {e}")
            await callback.answer("⚠️ Ошибка", show_alert=True)

        break


# ========== ПРОСМОТР FAQ ==========

@router.callback_query(F.data.startswith("faq_view_"))
async def callback_faq_view(callback: CallbackQuery):
    """Просмотр конкретного FAQ"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    try:
        faq_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("⚠️ Ошибка", show_alert=True)
        return

    log.info(f"[FAQ] Admin {callback.from_user.id} viewing FAQ #{faq_id}")

    async for db_session in db_adapter.get_session():
        try:
            result = await db_session.execute(select(FAQ).where(FAQ.id == faq_id))
            faq = result.scalar_one_or_none()

            if not faq:
                await callback.answer("⚠️ FAQ не найден", show_alert=True)
                break

            status = "✅ Активен" if faq.is_active else "❌ Неактивен"
            text = (
                f"📖 <b>FAQ #{faq.id}</b> — {status}\n\n"
                f"🇷🇺 Вопрос: {faq.question_ru}\n"
                f"🇷🇺 Ответ: {faq.answer_ru[:300]}\n\n"
                f"🇬🇧 Question: {faq.question_en}\n"
                f"🇬🇧 Answer: {faq.answer_en[:300]}\n\n"
                f"🔑 {faq.keywords} | 👁 {faq.usage_count}"
            )

            try:
                await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_faq_view_keyboard(faq_id))
            except Exception:
                await callback.message.answer(text, parse_mode="HTML", reply_markup=get_faq_view_keyboard(faq_id))

            await callback.answer()

        except Exception as e:
            log.error(f"[FAQ] Error viewing FAQ #{faq_id}: {e}")
            await callback.answer("⚠️ Ошибка", show_alert=True)

        break


# ========== РЕДАКТИРОВАНИЕ FAQ ==========

class FAQEditField(StatesGroup):
    """FSM для редактирования поля FAQ"""
    waiting_for_new_value = State()


@router.callback_query(F.data.startswith("faq_edit_") & ~F.data.startswith("faq_edit_field_") & ~F.data.startswith("faq_edit_select"))
async def callback_faq_edit_start(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование конкретного FAQ"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    try:
        faq_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("⚠️ Ошибка", show_alert=True)
        return

    log.info(f"[FAQ] Admin {callback.from_user.id} editing FAQ #{faq_id}")

    async for db_session in db_adapter.get_session():
        try:
            result = await db_session.execute(select(FAQ).where(FAQ.id == faq_id))
            faq = result.scalar_one_or_none()

            if not faq:
                await callback.answer("⚠️ FAQ не найден", show_alert=True)
                break

            status = "✅ Активен" if faq.is_active else "❌ Неактивен"
            text = (
                f"✏️ <b>FAQ #{faq.id}</b> — {status}\n\n"
                f"RU: {faq.question_ru[:40]}...\n"
                f"EN: {faq.question_en[:40]}...\n"
                f"🔑 {faq.keywords[:40]}...\n\n"
                f"Выберите поле:"
            )

            try:
                await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_faq_edit_keyboard(faq_id))
            except Exception:
                await callback.message.answer(text, parse_mode="HTML", reply_markup=get_faq_edit_keyboard(faq_id))

            await callback.answer()

        except Exception as e:
            log.error(f"[FAQ] Error opening edit FAQ #{faq_id}: {e}")
            await callback.answer("⚠️ Ошибка", show_alert=True)

        break


@router.callback_query(F.data.startswith("faq_edit_field_"))
async def callback_faq_edit_field(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование конкретного поля FAQ"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    parts = callback.data.split("_")
    try:
        faq_id = int(parts[3])
        field_name = parts[4]
    except (ValueError, IndexError):
        await callback.answer("⚠️ Ошибка", show_alert=True)
        return

    log.info(f"[FAQ] Admin {callback.from_user.id} editing field '{field_name}' of FAQ #{faq_id}")

    async for db_session in db_adapter.get_session():
        try:
            result = await db_session.execute(select(FAQ).where(FAQ.id == faq_id))
            faq = result.scalar_one_or_none()

            if not faq:
                await callback.answer("⚠️ FAQ не найден", show_alert=True)
                break

            # Toggle активности
            if field_name == "toggle_active":
                new_active = not faq.is_active
                faq.is_active = new_active
                await db_session.commit()

                status = "✅ Активен" if new_active else "❌ Неактивен"
                log.info(f"[FAQ] FAQ #{faq_id} toggled active={new_active}")

                try:
                    await callback.message.edit_text(
                        f"✅ Статус FAQ #{faq_id}: {status}",
                        reply_markup=get_faq_edit_keyboard(faq_id)
                    )
                except Exception:
                    await callback.message.answer(
                        f"✅ Статус FAQ #{faq_id}: {status}",
                        reply_markup=get_faq_edit_keyboard(faq_id)
                    )
                await callback.answer()
                break

            current_value = getattr(faq, field_name, "N/A")
            labels = {
                "question_ru": "🇷🇺 Вопрос RU",
                "answer_ru": "🇷🇺 Ответ RU",
                "question_en": "🇬🇧 Вопрос EN",
                "answer_en": "🇬🇧 Ответ EN",
                "keywords": "🔑 Ключевые слова",
            }
            label = labels.get(field_name, field_name)

            await state.update_data(faq_id=faq_id, field_name=field_name)
            await state.set_state(FAQEditField.waiting_for_new_value)

            try:
                await callback.message.edit_text(
                    f"✏️ <b>{label}</b>\n\n"
                    f"Текущее:\n<pre>{str(current_value)[:300]}</pre>\n\n"
                    f"Введите новое:",
                    parse_mode="HTML",
                    reply_markup=get_faq_fsm_back_keyboard()
                )
            except Exception:
                await callback.message.answer(
                    f"✏️ <b>{label}</b>\n\nВведите новое значение:",
                    parse_mode="HTML",
                    reply_markup=get_faq_fsm_back_keyboard()
                )

            await callback.answer()

        except Exception as e:
            log.error(f"[FAQ] Error editing field: {e}")
            await callback.answer("⚠️ Ошибка", show_alert=True)

        break


@router.message(FAQEditField.waiting_for_new_value)
async def process_faq_edit_field(message: Message, state: FSMContext):
    """Сохранение нового значения поля FAQ"""
    if message.from_user.id not in settings.admin_ids:
        return

    data = await state.get_data()
    faq_id = data.get("faq_id")
    field_name = data.get("field_name")

    if not faq_id or not field_name:
        await state.clear()
        return

    log.info(f"[FAQ] Admin {message.from_user.id} saving FAQ #{faq_id} field '{field_name}'")

    async for db_session in db_adapter.get_session():
        try:
            result = await db_session.execute(select(FAQ).where(FAQ.id == faq_id))
            faq = result.scalar_one_or_none()

            if not faq:
                await message.answer("⚠️ FAQ не найден")
                await state.clear()
                break

            setattr(faq, field_name, message.text)
            await db_session.commit()

            labels = {
                "question_ru": "🇷🇺 Вопрос RU",
                "answer_ru": "🇷🇺 Ответ RU",
                "question_en": "🇬🇧 Вопрос EN",
                "answer_en": "🇬🇧 Ответ EN",
                "keywords": "🔑 Ключевые слова",
            }
            label = labels.get(field_name, field_name)

            await message.answer(
                f"✅ {label} обновлён!\n\n<pre>{message.text[:300]}</pre>",
                parse_mode="HTML",
                reply_markup=get_faq_edit_keyboard(faq_id)
            )

            log.info(f"[FAQ] FAQ #{faq_id} field '{field_name}' saved")
            await state.clear()

        except Exception as e:
            log.error(f"[FAQ] Error saving FAQ field: {e}")
            await message.answer("⚠️ Ошибка при сохранении")

        break


# ========== УДАЛЕНИЕ FAQ ==========

@router.callback_query(F.data.startswith("faq_delete_confirm_"))
async def callback_faq_delete_confirm(callback: CallbackQuery):
    """Подтверждение удаления FAQ"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    try:
        faq_id = int(callback.data.split("_")[3])
    except (ValueError, IndexError):
        await callback.answer("⚠️ Ошибка", show_alert=True)
        return

    log.info(f"[FAQ] Admin {callback.from_user.id} confirming delete FAQ #{faq_id}")

    async for db_session in db_adapter.get_session():
        try:
            result = await db_session.execute(select(FAQ).where(FAQ.id == faq_id))
            faq = result.scalar_one_or_none()

            if not faq:
                await callback.answer("⚠️ FAQ не найден", show_alert=True)
                break

            text = (
                f"⚠️ <b>Удалить FAQ #{faq.id}?</b>\n\n"
                f"❓ {faq.question_ru}\n"
                f"👁 {faq.usage_count} использований"
            )

            try:
                await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_faq_delete_confirm_keyboard(faq_id))
            except Exception:
                await callback.message.answer(text, parse_mode="HTML", reply_markup=get_faq_delete_confirm_keyboard(faq_id))

            await callback.answer()

        except Exception as e:
            log.error(f"[FAQ] Error confirming delete: {e}")
            await callback.answer("⚠️ Ошибка", show_alert=True)

        break


@router.callback_query(F.data.startswith("faq_delete_yes_"))
async def callback_faq_delete_yes(callback: CallbackQuery):
    """Удалить FAQ"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    try:
        faq_id = int(callback.data.split("_")[3])
    except (ValueError, IndexError):
        await callback.answer("⚠️ Ошибка", show_alert=True)
        return

    log.warning(f"[FAQ] Admin {callback.from_user.id} DELETING FAQ #{faq_id}")

    async for db_session in db_adapter.get_session():
        try:
            success = await faq_service.delete_faq(db_session, faq_id)

            if success:
                try:
                    await callback.message.edit_text(
                        f"✅ FAQ #{faq_id} удалён!",
                        reply_markup=get_faq_management_inline_keyboard()
                    )
                except Exception:
                    await callback.message.answer(
                        f"✅ FAQ #{faq_id} удалён!",
                        reply_markup=get_faq_management_inline_keyboard()
                    )
                log.info(f"[FAQ] FAQ #{faq_id} deleted")
            else:
                await callback.answer("⚠️ FAQ не найден", show_alert=True)

        except Exception as e:
            log.error(f"[FAQ] Error deleting FAQ #{faq_id}: {e}")
            await callback.answer("⚠️ Ошибка", show_alert=True)

        break


@router.callback_query(F.data.startswith("faq_delete_no_"))
async def callback_faq_delete_no(callback: CallbackQuery):
    """Отмена удаления FAQ"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    try:
        faq_id = int(callback.data.split("_")[3])
    except (ValueError, IndexError):
        await callback.answer("⚠️ Ошибка", show_alert=True)
        return

    log.info(f"[FAQ] Admin {callback.from_user.id} cancelled delete FAQ #{faq_id}")

    try:
        await callback.message.edit_reply_markup(reply_markup=get_faq_view_keyboard(faq_id))
    except Exception:
        await callback.message.answer("❌ Отменено", reply_markup=get_faq_view_keyboard(faq_id))
    await callback.answer() 
