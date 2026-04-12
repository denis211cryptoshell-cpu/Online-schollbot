"""
Обработчик inline callback запросов для менеджера и администратора
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, desc
from app.core.logger import log
from app.core.settings import settings
from app.database.adapter import db_adapter
from app.database.models import Lead, LeadStatus, LeadStatusHistory, FAQ
from app.services.lead_service import lead_service
from app.services.faq_service import faq_service
import app.services.notification_service as notification_service
from app.keyboards.inline_kb import get_lead_status_keyboard, get_lead_actions_keyboard
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
from app.keyboards.admin_ban_kb import get_admin_main_inline_keyboard
from app.handlers.admin_extended import FAQAdd

router = Router()


# ========== FSM состояния для FAQ ==========

class FAQEditField(StatesGroup):
    """FSM для редактирования поля FAQ"""
    waiting_for_new_value = State()


class ManagerReply(StatesGroup):
    """Состояния для ответа менеджера пользователю"""
    waiting_for_reply_text = State()


@router.callback_query(F.data.startswith("status_"))
async def handle_status_change(callback: CallbackQuery):
    """
    Обработка изменения статуса заявки через inline кнопки
    
    Callback формат: status_{lead_id}_{status}
    """
    # Проверяем, что запрос из чата менеджера
    if str(callback.message.chat.id) != str(settings.MANAGER_CHAT_ID):
        await callback.answer("⛔ Недоступно в этом чате", show_alert=True)
        return
    
    # Парсим callback_data
    parts = callback.data.split("_")
    if len(parts) != 3:
        await callback.answer("⚠️ Ошибка формата", show_alert=True)
        return
    
    lead_id = int(parts[1])
    new_status_str = parts[2]
    
    # Маппинг статусов
    status_map = {
        'accepted': LeadStatus.ACCEPTED,
        'callback': LeadStatus.CALLBACK,
        'rejected': LeadStatus.REJECTED
    }
    
    new_status = status_map.get(new_status_str)
    if not new_status:
        await callback.answer("⚠️ Неизвестный статус", show_alert=True)
        return
    
    # Обновляем статус
    async for db_session in db_adapter.get_session():
        try:
            lead = await lead_service.update_status(
                db_session=db_session,
                lead_id=lead_id,
                new_status=new_status,
                changed_by="manager"
            )
            
            if lead:
                # Обновляем сообщение в чате менеджера
                if lead.manager_chat_message_id:
                    await notification_service.manager_notification_service.update_lead_status_message(
                        message_id=lead.manager_chat_message_id,
                        lead=lead,
                        new_status=new_status
                    )
                
                # Показываем подтверждение
                status_emoji = {
                    LeadStatus.ACCEPTED: "✅",
                    LeadStatus.CALLBACK: "📞",
                    LeadStatus.REJECTED: "❌"
                }.get(new_status, "📋")
                
                status_text = {
                    LeadStatus.ACCEPTED: "принята",
                    LeadStatus.CALLBACK: "требует перезвона",
                    LeadStatus.REJECTED: "отклонена"
                }.get(new_status, "обновлена")
                
                await callback.answer(f"{status_emoji} Заявка #{lead_id} {status_text}!")
                log.info(f"Lead #{lead_id} status changed to {new_status.value} via inline button")
            else:
                await callback.answer(f"⚠️ Заявка #{lead_id} не найдена", show_alert=True)
        
        except Exception as e:
            log.error(f"Error changing status for lead #{lead_id}: {e}")
            await callback.answer("⚠️ Ошибка при обновлении статуса", show_alert=True)
        
        break


@router.callback_query(F.data.startswith("profile_"))
async def handle_profile_view(callback: CallbackQuery):
    """Просмотр профиля пользователя"""
    if str(callback.message.chat.id) != str(settings.MANAGER_CHAT_ID):
        await callback.answer("⛔ Недоступно в этом чате", show_alert=True)
        return
    
    parts = callback.data.split("_")
    if len(parts) != 2:
        await callback.answer("⚠️ Ошибка формата", show_alert=True)
        return
    
    lead_id = int(parts[1])
    
    async for db_session in db_adapter.get_session():
        try:
            result = await db_session.execute(
                select(Lead).where(Lead.id == lead_id)
            )
            lead = result.scalar_one_or_none()
            
            if not lead:
                await callback.answer(f"⚠️ Заявка #{lead_id} не найдена", show_alert=True)
                return
            
            # Получаем историю статусов
            history_result = await db_session.execute(
                select(LeadStatusHistory)
                .where(LeadStatusHistory.lead_id == lead_id)
                .order_by(desc(LeadStatusHistory.changed_at))
            )
            history = history_result.scalars().all()
            
            # Формируем текст профиля
            status_emoji = {
                LeadStatus.NEW: "🆕",
                LeadStatus.ACCEPTED: "✅",
                LeadStatus.CALLBACK: "📞",
                LeadStatus.REJECTED: "❌"
            }.get(lead.status, "📋")
            
            text = (
                f"👤 <b>Профиль пользователя</b>\n\n"
                f"🆔 <b>Telegram ID:</b> <code>{lead.telegram_id}</code>\n"
                f"📝 <b>Username:</b> @{lead.username or 'N/A'}\n"
                f"👤 <b>Имя:</b> {lead.full_name or 'Не указано'}\n"
                f"📞 <b>Контакт:</b> <code>{lead.contact or 'Не указано'}</code>\n"
                f"🌐 <b>Язык:</b> {'🇷🇺 Русский' if lead.language == 'ru' else '🇬🇧 English'}\n"
                f"📅 <b>Дата регистрации:</b> {lead.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
                f"{status_emoji} <b>Текущий статус:</b> {lead.status.value if lead.status else 'Неизвестно'}\n\n"
            )
            
            # Добавляем историю статусов
            if history:
                text += "📋 <b>История изменений:</b>\n"
                for h in history[:5]:  # Показываем последние 5
                    text += (
                        f"• {h.changed_at.strftime('%d.%m %H:%M')} - "
                        f"{h.old_status or 'None'} → {h.new_status} "
                        f"({h.changed_by})\n"
                    )
            
            await callback.message.answer(text, parse_mode="HTML")
            await callback.answer("Профиль загружен")
            
        except Exception as e:
            log.error(f"Error viewing profile for lead #{lead_id}: {e}")
            await callback.answer("⚠️ Ошибка при загрузке профиля", show_alert=True)
        
        break


@router.callback_query(F.data.startswith("reply_"))
async def handle_reply_request(callback: CallbackQuery, state: FSMContext):
    """Запрос на ответ пользователю"""
    if str(callback.message.chat.id) != str(settings.MANAGER_CHAT_ID):
        await callback.answer("⛔ Недоступно в этом чате", show_alert=True)
        return
    
    parts = callback.data.split("_")
    if len(parts) != 2:
        await callback.answer("⚠️ Ошибка формата", show_alert=True)
        return
    
    lead_id = int(parts[1])
    
    # Сохраняем lead_id в состоянии
    await state.set_data({'reply_lead_id': lead_id})
    await state.set_state(ManagerReply.waiting_for_reply_text)
    
    await callback.message.answer(
        f"💬 Напишите сообщение для пользователя (заявка #{lead_id}):\n\n"
        f"Или нажмите /cancel для отмены."
    )
    
    await callback.answer("Введите сообщение")


@router.message(ManagerReply.waiting_for_reply_text)
async def process_manager_reply(message: Message, state: FSMContext):
    """Обработка ответа менеджера пользователю"""
    # Проверяем, что сообщение из чата менеджера
    if str(message.chat.id) != str(settings.MANAGER_CHAT_ID):
        return
    
    # Проверяем команду отмены
    if message.text and message.text.lower() in ['/cancel', 'отмена', 'отменить']:
        await state.clear()
        await message.answer("❌ Отменено")
        return
    
    # Получаем lead_id из состояния
    data = await state.get_data()
    lead_id = data.get('reply_lead_id')
    
    if not lead_id:
        await state.clear()
        await message.answer("⚠️ Ошибка. Начните заново.")
        return
    
    async for db_session in db_adapter.get_session():
        try:
            # Находим заявку
            result = await db_session.execute(
                select(Lead).where(Lead.id == lead_id)
            )
            lead = result.scalar_one_or_none()
            
            if not lead:
                await message.answer(f"⚠️ Заявка #{lead_id} не найдена")
                await state.clear()
                return
            
            # Отправляем сообщение пользователю
            success = await notification_service.manager_notification_service.send_message_to_user(
                telegram_id=lead.telegram_id,
                text=message.text
            )
            
            if success:
                await message.answer(
                    f"✅ Сообщение отправлено пользователю @{lead.username or lead.telegram_id}"
                )
                log.info(f"Manager replied to lead #{lead_id} (user {lead.telegram_id})")
            else:
                await message.answer(
                    f"⚠️ Не удалось отправить сообщение.\n\n"
                    f"Возможно, пользователь заблокировал бота."
                )
            
            await state.clear()
            
        except Exception as e:
            log.error(f"Error sending reply to user for lead #{lead_id}: {e}")
            await message.answer("⚠️ Ошибка при отправке сообщения")
        
        break


@router.callback_query(F.data.startswith("actions_"))
async def handle_lead_actions(callback: CallbackQuery):
    """Показ дополнительных действий для заявки"""
    if str(callback.message.chat.id) != str(settings.MANAGER_CHAT_ID):
        await callback.answer("⛔ Недоступно в этом чате", show_alert=True)
        return
    
    parts = callback.data.split("_")
    if len(parts) != 2:
        await callback.answer("⚠️ Ошибка формата", show_alert=True)
        return
    
    lead_id = int(parts[1])
    
    await callback.message.edit_reply_markup(
        reply_markup=get_lead_actions_keyboard(lead_id)
    )
    
    await callback.answer()


@router.callback_query(F.data.startswith("back_"))
async def handle_back_to_status(callback: CallbackQuery):
    """Возврат к основному виду заявки"""
    if str(callback.message.chat.id) != str(settings.MANAGER_CHAT_ID):
        await callback.answer("⛔ Недоступно в этом чате", show_alert=True)
        return
    
    parts = callback.data.split("_")
    if len(parts) != 2:
        await callback.answer("⚠️ Ошибка формата", show_alert=True)
        return
    
    lead_id = int(parts[1])
    
    async for db_session in db_adapter.get_session():
        try:
            result = await db_session.execute(
                select(Lead).where(Lead.id == lead_id)
            )
            lead = result.scalar_one_or_none()
            
            if lead:
                await callback.message.edit_reply_markup(
                    reply_markup=get_lead_status_keyboard(lead_id)
                )
                await callback.answer()
        
        except Exception as e:
            log.error(f"Error in back action: {e}")
        
        break


@router.callback_query(F.data.startswith("note_"))
async def handle_add_note(callback: CallbackQuery, state: FSMContext):
    """Добавление заметки к заявке"""
    if str(callback.message.chat.id) != str(settings.MANAGER_CHAT_ID):
        await callback.answer("⛔ Недоступно в этом чате", show_alert=True)
        return
    
    parts = callback.data.split("_")
    if len(parts) != 2:
        await callback.answer("⚠️ Ошибка формата", show_alert=True)
        return
    
    lead_id = int(parts[1])
    
    await state.set_data({'note_lead_id': lead_id})
    # TODO: Добавить состояние для заметок
    
    await callback.message.answer(
        f"📝 Напишите заметку для заявки #{lead_id}:\n\n"
        f"Или нажмите /cancel для отмены."
    )
    
    await callback.answer()


@router.callback_query(F.data.startswith("crm_") & F.data.regexp(r"^crm_\d+$"))
async def handle_open_crm(callback: CallbackQuery):
    """Открыть заявку в CRM (Google Sheets)"""
    if str(callback.message.chat.id) != str(settings.MANAGER_CHAT_ID):
        await callback.answer("⛔ Недоступно в этом чате", show_alert=True)
        return

    parts = callback.data.split("_")
    if len(parts) != 2:
        await callback.answer("⚠️ Ошибка формата", show_alert=True)
        return

    lead_id = int(parts[1])

    # Формируем ссылку на Google Sheets
    sheets_url = f"https://docs.google.com/spreadsheets/d/{settings.GOOGLE_SHEETS_ID}"

    await callback.message.answer(
        f"🔗 <b>Открыть заявку #{lead_id} в CRM:</b>\n\n"
        f"<a href='{sheets_url}'>Google Sheets</a>",
        parse_mode="HTML",
        disable_web_page_preview=True
    )

    await callback.answer()


# ========== УПРАВЛЕНИЕ FAQ (АДМИН) ==========

@router.callback_query(F.data == "faq_management")
async def callback_faq_management_menu(callback: CallbackQuery):
    """Управление базой знаний FAQ — inline меню"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    log.info(f"[FAQ] Admin {callback.from_user.id} clicked: faq_management")
    try:
        await callback.message.edit_text(
            "📝 <b>Управление базой знаний</b>\n\n"
            "Выберите действие:",
            parse_mode="HTML",
            reply_markup=get_faq_management_inline_keyboard()
        )
    except Exception:
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
            reply_markup=get_admin_main_inline_keyboard()
        )
    except Exception:
        await callback.message.answer(
            "🛠 Админ-панель бота\n\nВыберите действие:",
            reply_markup=get_admin_main_inline_keyboard()
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


# ========== FAQ FSM ОТМЕНА ==========

@router.callback_query(F.data == "faq_cancel_fsm")
async def handle_faq_fsm_cancel(callback: CallbackQuery, state: FSMContext):
    """Отмена FSM состояния при добавлении/редактировании FAQ"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    await state.clear()
    log.info(f"[FAQ] Admin {callback.from_user.id} cancelled FSM state via inline button")
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
