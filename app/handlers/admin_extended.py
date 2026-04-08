"""
Обработчик расширенной админ-панели
"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func
from app.core.logger import log
from app.core.settings import settings
from app.database.adapter import db_adapter
from app.services.analytics_service import analytics_service
from app.services.faq_service import faq_service
from app.services.lead_service import lead_service
from app.database.models import Lead, LeadStatus, FAQ

router = Router()


class FAQAdd(StatesGroup):
    """Состояния для добавления FAQ"""
    waiting_for_question_ru = State()
    waiting_for_answer_ru = State()
    waiting_for_question_en = State()
    waiting_for_answer_en = State()
    waiting_for_keywords = State()


class FAQEdit(StatesGroup):
    """Состояния для редактирования FAQ"""
    waiting_for_faq_id = State()
    waiting_for_new_question_ru = State()
    waiting_for_new_answer_ru = State()
    waiting_for_new_question_en = State()
    waiting_for_new_answer_en = State()
    waiting_for_new_keywords = State()


class Broadcast(StatesGroup):
    """Состояния для рассылки"""
    waiting_for_broadcast_text = State()
    waiting_for_broadcast_confirm = State()


# ========== СТАТИСТИКА ==========

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Расширенная статистика"""
    if message.from_user.id not in settings.admin_ids:
        await message.answer("⛔ У вас нет прав администратора.")
        return
    
    await message.answer("⏳ Загрузка статистики...")
    
    async for db_session in db_adapter.get_session():
        try:
            # Воронка конверсии
            funnel = await analytics_service.get_conversion_funnel(db_session, days=7)
            funnel_text = analytics_service.format_funnel_text(funnel)
            
            await message.answer(funnel_text, parse_mode="HTML")
            
        except Exception as e:
            log.error(f"Error getting stats: {e}")
            await message.answer("⚠️ Ошибка при загрузке статистики")
        
        break


@router.message(Command("analytics"))
async def cmd_analytics(message: Message):
    """Полная аналитика"""
    if message.from_user.id not in settings.admin_ids:
        await message.answer("⛔ У вас нет прав администратора.")
        return
    
    await message.answer("⏳ Загрузка аналитики...")
    
    async for db_session in db_adapter.get_session():
        try:
            # Дневная статистика
            daily_stats = await analytics_service.get_daily_stats(db_session, days=30)
            daily_text = analytics_service.format_daily_stats_text(daily_stats)
            
            await message.answer(daily_text, parse_mode="HTML")
            
            # Экономия времени
            time_stats = await analytics_service.get_time_saved_stats(db_session, days=7)
            time_text = analytics_service.format_time_saved_text(time_stats)
            
            await message.answer(time_text, parse_mode="HTML")
            
            # Активность пользователей
            user_stats = await analytics_service.get_user_activity_stats(db_session, days=7)
            user_text = (
                f"👥 <b>Активность пользователей ({user_stats['period_days']} дн.)</b>\n\n"
                f"👤 Уникальных пользователей: {user_stats['unique_users']}\n"
                f"🆕 Новых пользователей: {user_stats['new_users']}\n"
                f"🔄 Возвращающихся: {user_stats['returning_users']}\n"
                f"📊 Среднее заявок на пользователя: {user_stats['avg_leads_per_user']}"
            )
            
            await message.answer(user_text, parse_mode="HTML")
            
        except Exception as e:
            log.error(f"Error getting analytics: {e}")
            await message.answer("⚠️ Ошибка при загрузке аналитики")
        
        break


@router.message(Command("top_faq"))
async def cmd_top_faq(message: Message):
    """Топ вопросов FAQ"""
    if message.from_user.id not in settings.admin_ids:
        await message.answer("⛔ У вас нет прав администратора.")
        return
    
    async for db_session in db_adapter.get_session():
        try:
            top_faqs = await analytics_service.get_top_faq_questions(db_session, limit=10)
            
            if not top_faqs:
                await message.answer("📋 База знаний пуста")
                return
            
            text = "🔥 <b>Топ-10 частых вопросов</b>\n\n"
            
            for i, faq in enumerate(top_faqs, 1):
                text += f"{i}. {faq['question']}\n"
                text += f"   👁 Использовано: {faq['count']} раз\n\n"
            
            await message.answer(text, parse_mode="HTML")
            
        except Exception as e:
            log.error(f"Error getting top FAQ: {e}")
            await message.answer("⚠️ Ошибка при загрузке топа вопросов")
        
        break


# ========== УПРАВЛЕНИЕ FAQ ==========

@router.message(F.text == "📝 Управление FAQ")
async def faq_management(message: Message):
    """Управление базой знаний FAQ"""
    if message.from_user.id not in settings.admin_ids:
        return
    
    await message.answer(
        "📝 <b>Управление базой знаний</b>\n\n"
        "Выберите действие:\n\n"
        "• ➕ Добавить вопрос\n"
        "• 📋 Список вопросов\n"
        "• ✏️ Редактировать\n"
        "• 🗑 Удалить вопрос\n\n"
        "Или используйте команды:\n"
        "<code>/add_faq</code> - добавить\n"
        "<code>/list_faq</code> - список\n"
        "<code>/edit_faq</code> - редактировать\n"
        "<code>/delete_faq</code> - удалить",
        parse_mode="HTML"
    )


@router.message(Command("add_faq"))
async def cmd_add_faq(message: Message, state: FSMContext):
    """Начать добавление FAQ"""
    if message.from_user.id not in settings.admin_ids:
        await message.answer("⛔ У вас нет прав администратора.")
        return
    
    await message.answer(
        "➕ <b>Добавление нового вопроса FAQ</b>\n\n"
        "Введите вопрос на русском:\n"
        "(или /cancel для отмены)"
    )
    await state.set_state(FAQAdd.waiting_for_question_ru)


@router.message(FAQAdd.waiting_for_question_ru)
async def process_question_ru(message: Message, state: FSMContext):
    """Обработка вопроса на русском"""
    if message.text and message.text.lower() in ['/cancel', 'отмена']:
        await state.clear()
        await message.answer("❌ Отменено")
        return
    
    await state.update_data(question_ru=message.text)
    await message.answer("✅ Теперь введите ответ на русском:")
    await state.set_state(FAQAdd.waiting_for_answer_ru)


@router.message(FAQAdd.waiting_for_answer_ru)
async def process_answer_ru(message: Message, state: FSMContext):
    """Обработка ответа на русском"""
    if message.text and message.text.lower() in ['/cancel', 'отмена']:
        await state.clear()
        await message.answer("❌ Отменено")
        return
    
    await state.update_data(answer_ru=message.text)
    await message.answer("✅ Теперь введите вопрос на английском:")
    await state.set_state(FAQAdd.waiting_for_question_en)


@router.message(FAQAdd.waiting_for_question_en)
async def process_question_en(message: Message, state: FSMContext):
    """Обработка вопроса на английском"""
    if message.text and message.text.lower() in ['/cancel', 'отмена']:
        await state.clear()
        await message.answer("❌ Отменено")
        return
    
    await state.update_data(question_en=message.text)
    await message.answer("✅ Теперь введите ответ на английском:")
    await state.set_state(FAQAdd.waiting_for_answer_en)


@router.message(FAQAdd.waiting_for_answer_en)
async def process_answer_en(message: Message, state: FSMContext):
    """Обработка ответа на английском"""
    if message.text and message.text.lower() in ['/cancel', 'отмена']:
        await state.clear()
        await message.answer("❌ Отменено")
        return
    
    await state.update_data(answer_en=message.text)
    await message.answer("✅ Теперь введите ключевые слова (через запятую):")
    await state.set_state(FAQAdd.waiting_for_keywords)


@router.message(FAQAdd.waiting_for_keywords)
async def process_keywords(message: Message, state: FSMContext):
    """Обработка ключевых слов и сохранение FAQ"""
    if message.text and message.text.lower() in ['/cancel', 'отмена']:
        await state.clear()
        await message.answer("❌ Отменено")
        return
    
    data = await state.get_data()
    
    async for db_session in db_adapter.get_session():
        try:
            faq = await faq_service.add_faq(
                db_session=db_session,
                question_ru=data['question_ru'],
                question_en=data['question_en'],
                answer_ru=data['answer_ru'],
                answer_en=data['answer_en'],
                keywords=message.text
            )
            
            await message.answer(
                f"✅ FAQ успешно добавлен!\n\n"
                f"🆔 ID: {faq.id}\n"
                f"❓ Вопрос: {faq.question_ru}\n"
                f"🔑 Ключевые слова: {message.text}"
            )
            
            log.info(f"FAQ added via admin: #{faq.id}")
            
        except Exception as e:
            log.error(f"Error adding FAQ: {e}")
            await message.answer("⚠️ Ошибка при добавлении FAQ")
        
        break
    
    await state.clear()


@router.message(Command("list_faq"))
async def cmd_list_faq(message: Message):
    """Список всех FAQ"""
    if message.from_user.id not in settings.admin_ids:
        await message.answer("⛔ У вас нет прав администратора.")
        return
    
    async for db_session in db_adapter.get_session():
        try:
            result = await db_session.execute(
                select(FAQ).order_by(FAQ.usage_count.desc()).limit(20)
            )
            faqs = result.scalars().all()
            
            if not faqs:
                await message.answer("📋 База знаний пуста")
                return
            
            text = "📋 <b>Список вопросов (топ-20)</b>\n\n"
            
            for faq in faqs:
                status = "✅" if faq.is_active else "❌"
                text += (
                    f"{status} <b>#{faq.id}</b> - {faq.question_ru}\n"
                    f"   👁 {faq.usage_count} использований\n"
                    f"   🔑 {faq.keywords[:50]}...\n\n"
                )
            
            await message.answer(text, parse_mode="HTML")
            
        except Exception as e:
            log.error(f"Error listing FAQs: {e}")
            await message.answer("⚠️ Ошибка при загрузке списка FAQ")
        
        break


@router.message(Command("delete_faq"))
async def cmd_delete_faq(message: Message):
    """Удаление FAQ по ID"""
    if message.from_user.id not in settings.admin_ids:
        await message.answer("⛔ У вас нет прав администратора.")
        return
    
    # Проверяем аргумент
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(
            "🗑 Использование: <code>/delete_faq [ID]</code>\n\n"
            "Пример: <code>/delete_faq 5</code>",
            parse_mode="HTML"
        )
        return
    
    try:
        faq_id = int(parts[1])
    except ValueError:
        await message.answer("⚠️ ID должен быть числом")
        return
    
    async for db_session in db_adapter.get_session():
        try:
            success = await faq_service.delete_faq(db_session, faq_id)
            
            if success:
                await message.answer(f"✅ FAQ #{faq_id} удален")
            else:
                await message.answer(f"⚠️ FAQ #{faq_id} не найден")
            
        except Exception as e:
            log.error(f"Error deleting FAQ #{faq_id}: {e}")
            await message.answer("⚠️ Ошибка при удалении FAQ")
        
        break


# ========== РАССЫЛКА ==========

@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext):
    """Начать рассылку всем пользователям"""
    if message.from_user.id not in settings.admin_ids:
        await message.answer("⛔ У вас нет прав администратора.")
        return
    
    await message.answer(
        "📢 <b>Рассылка сообщений</b>\n\n"
        "Введите текст для рассылки всем пользователям:\n"
        "(или /cancel для отмены)\n\n"
        "⚠️ Сообщение получат все пользователи, которые когда-либо писали боту"
    )
    await state.set_state(Broadcast.waiting_for_broadcast_text)


@router.message(Broadcast.waiting_for_broadcast_text)
async def process_broadcast_text(message: Message, state: FSMContext):
    """Обработка текста рассылки"""
    if message.text and message.text.lower() in ['/cancel', 'отмена']:
        await state.clear()
        await message.answer("❌ Отменено")
        return
    
    await state.update_data(broadcast_text=message.text)
    
    # Показываем предпросмотр и просим подтверждение
    await message.answer(
        f"📢 <b>Предпросмотр рассылки:</b>\n\n"
        f"{message.text}\n\n"
        f"Отправить всем пользователям?",
        parse_mode="HTML"
    )
    
    # TODO: Добавить inline кнопки для подтверждения
    await message.answer("✅ Для отправки напишите: <code>подтверждаю</code>")
    await state.set_state(Broadcast.waiting_for_broadcast_confirm)


@router.message(Broadcast.waiting_for_broadcast_confirm)
async def process_broadcast_confirm(message: Message, state: FSMContext):
    """Обработка подтверждения рассылки"""
    if message.text and message.text.lower() in ['/cancel', 'отмена', 'нет']:
        await state.clear()
        await message.answer("❌ Рассылка отменена")
        return
    
    if message.text.lower() not in ['подтверждаю', 'да', 'confirm', 'yes']:
        await message.answer("⚠️ Напишите 'подтверждаю' для отправки или /cancel для отмены")
        return
    
    data = await state.get_data()
    broadcast_text = data.get('broadcast_text')
    
    if not broadcast_text:
        await state.clear()
        await message.answer("⚠️ Ошибка. Начните заново через /broadcast")
        return
    
    await message.answer("⏳ Отправка рассылки...")
    
    async for db_session in db_adapter.get_session():
        try:
            # Получаем все уникальные Telegram ID
            result = await db_session.execute(
                select(func.distinct(Lead.telegram_id))
            )
            telegram_ids = [row[0] for row in result.all()]
            
            if not telegram_ids:
                await message.answer("⚠️ Нет пользователей для рассылки")
                await state.clear()
                return
            
            # Отправляем сообщение
            sent_count = 0
            failed_count = 0
            
            from app.services.notification_service import manager_notification_service
            
            for tg_id in telegram_ids:
                try:
                    success = await manager_notification_service.send_message_to_user(
                        telegram_id=tg_id,
                        text=broadcast_text
                    )
                    if success:
                        sent_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    log.error(f"Broadcast error for user {tg_id}: {e}")
                    failed_count += 1
            
            await message.answer(
                f"✅ Рассылка завершена!\n\n"
                f"📤 Отправлено: {sent_count}\n"
                f"❌ Ошибок: {failed_count}\n"
                f"👥 Всего пользователей: {len(telegram_ids)}"
            )
            
            log.info(f"Broadcast completed: {sent_count} sent, {failed_count} failed")
            
        except Exception as e:
            log.error(f"Error during broadcast: {e}")
            await message.answer("⚠️ Ошибка при рассылке")
        
        break
    
    await state.clear()


# ========== НАСТРОЙКИ ==========

@router.message(Command("settings"))
async def cmd_settings(message: Message):
    """Настройки бота"""
    if message.from_user.id not in settings.admin_ids:
        await message.answer("⛔ У вас нет прав администратора.")
        return
    
    text = (
        f"⚙️ <b>Настройки бота</b>\n\n"
        f"🤖 <b>Бот:</b>\n"
        f"• Токен: {settings.BOT_TOKEN[:20]}...\n"
        f"• Админы: {settings.ADMIN_IDS}\n"
        f"• Чат менеджера: {settings.MANAGER_CHAT_ID}\n\n"
        f"🗄 <b>База данных:</b>\n"
        f"• Тип: {settings.DATABASE_TYPE}\n"
        f"• Путь: {settings.SQLITE_PATH if settings.DATABASE_TYPE == 'sqlite' else settings.POSTGRES_HOST}\n\n"
        f"💾 <b>Кэш:</b>\n"
        f"• Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}\n"
        f"• FAQ TTL: {settings.FAQ_CACHE_TTL} сек\n\n"
        f"📊 <b>CRM:</b>\n"
        f"• Google Sheets: {'✅' if settings.GOOGLE_SHEETS_ENABLED else '❌'}\n"
        f"• Sheet ID: {settings.GOOGLE_SHEETS_ID or 'Не указан'}\n\n"
        f"📝 <b>Логирование:</b>\n"
        f"• Уровень: {settings.LOG_LEVEL}\n"
        f"• Файл: {settings.LOG_FILE}"
    )
    
    await message.answer(text, parse_mode="HTML")


@router.message(Command("restart"))
async def cmd_restart(message: Message):
    """Перезапуск бота"""
    if message.from_user.id not in settings.admin_ids:
        await message.answer("⛔ У вас нет прав администратора.")
        return
    
    await message.answer("🔄 Бот перезапускается...")
    log.info("Bot restart requested by admin")
    
    # TODO: Реализовать перезапуск
    # Пока просто сообщение
    await message.answer("✅ Команда принята. Перезапуск вручную через Docker или systemctl")
