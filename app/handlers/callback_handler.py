"""
Обработчик inline callback запросов для менеджера
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, desc
from app.core.logger import log
from app.core.settings import settings
from app.database.adapter import db_adapter
from app.database.models import Lead, LeadStatus, LeadStatusHistory
from app.services.lead_service import lead_service
import app.services.notification_service as notification_service
from app.keyboards.inline_kb import get_lead_status_keyboard, get_lead_actions_keyboard

router = Router()


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


@router.callback_query(F.data.startswith("crm_"))
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
