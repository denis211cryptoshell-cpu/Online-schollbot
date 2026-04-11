"""
Основной обработчик сообщений
"""
import re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select
from app.core.logger import log
from app.core.settings import settings
from app.services.faq_service import faq_service
from app.services.lead_service import lead_service
import app.services.notification_service as notification_service
from app.services.ban_service import ban_service
from app.database.adapter import db_adapter
from app.database.models import Lead
from app.keyboards.inline_kb import get_cancel_keyboard

router = Router()


# ========== FSM для сбора контактов ==========

class ContactCollection(StatesGroup):
    """Состояния для сбора контактов"""
    waiting_for_phone = State()


# ========== Функции распознавания намерений ==========

def extract_phone_number(text: str) -> str:
    """Извлечение номера телефона из текста"""
    phone_patterns = [
        r'(\+7|8)\s*\(?[0-9]{3}\)?\s*[0-9]{3}[-\s]?[0-9]{2}[-\s]?[0-9]{2}',
        r'(\+7|8)[0-9]{9}',
        r'\+[0-9]{1,3}\s*[0-9\s\-]{7,15}'
    ]
    
    for pattern in phone_patterns:
        match = re.search(pattern, text)
        if match:
            phone = match.group(0).strip()
            phone = re.sub(r'[^\d+]', '', phone)
            return phone
    
    return ""


def extract_email(text: str) -> str:
    """Извлечение email из текста"""
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    match = re.search(email_pattern, text)
    return match.group(0) if match else ""


def is_enrollment_intent(text: str) -> bool:
    """Определение намерения записаться на курс"""
    text_lower = text.lower()
    
    enrollment_phrases = [
        'хочу записаться',
        'записаться на курс',
        'записаться',
        'хочу на курс',
        'запиши меня',
        'запишите меня',
        'я хочу купить',
        'хочу купить',
        'готов купить',
        'как оплатить',
        'хочу оплатить',
        'давайте начнем',
        'я готов',
        'i want to enroll',
        'i want to join',
        'sign me up',
        'i want to buy',
        'ready to start',
        'оставить заявку',
        'подать заявку',
        'оформить заявку',
        'создать заявку',
        'хочу оставить заявку',
        'хочу подать заявку',
        'заявка на курс',
        'записаться на обучение',
        'хочу на обучение'
    ]
    
    return any(phrase in text_lower for phrase in enrollment_phrases)


def is_contact_message(text: str) -> bool:
    """Проверка, является ли сообщение контактной информацией"""
    if extract_phone_number(text):
        return True
    if extract_email(text):
        return True
    return False


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработка команды /start"""
    # Проверяем, не заблокирован ли пользователь
    async for db_session in db_adapter.get_session():
        try:
            banned = await ban_service.is_banned(db_session, message.from_user.id)
            if banned:
                await message.answer(
                    "🚫 Вы заблокированы и не можете использовать бота.\n\n"
                    f"Причина: {banned.reason}\n"
                    f"Дата: {banned.created_at.strftime('%d.%m.%Y %H:%M')}"
                )
                return
        except Exception as e:
            log.error(f"Error checking ban status: {e}")
        break
    
    log.info(f"User {message.from_user.id} started bot")
    
    await message.answer(
        "👋 Привет! Я бот-менеджер онлайн-школы.\n\n"
        "📚 <b>Чем могу помочь?</b>\n\n"
        "Вы можете спросить о:\n"
        "• 💰 Стоимости курса\n"
        "• 📝 Записи на курс\n"
        "• 💳 Рассрочке\n"
        "• 📚 Программе обучения\n"
        "• И другом...\n\n"
        "Просто напишите ваш вопрос!"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработка команды /help"""
    await message.answer(
        "📚 <b>Доступные команды:</b>\n\n"
        "/start - Начать работу\n"
        "/help - Показать справку\n"
        "/admin - Админ-панель (только для админов)\n\n"
        "💡 <b>Популярные вопросы:</b>\n\n"
        "• Сколько стоит курс?\n"
        "• Как записаться?\n"
        "• Есть ли рассрочка?\n"
        "• Что входит в курс?\n\n"
        "Просто напишите ваш вопрос!"
    )


@router.message(ContactCollection.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    """Обработка введенного телефона"""
    text = message.text
    user_id = message.from_user.id

    # Пытаемся извлечь телефон
    phone = extract_phone_number(text)

    if not phone:
        # Пробуем email
        email = extract_email(text)
        if email:
            phone = email
        else:
            # Отправляем новое сообщение с подсказкой и кнопкой отмены
            await message.answer(
                "⚠️ Я не смог распознать номер телефона или email.\n\n"
                "Пожалуйста, напишите:\n"
                "• Телефон: +7 (999) 123-45-67\n"
                "• Или email: example@mail.ru",
                reply_markup=get_cancel_keyboard()
            )
            return

    # Получаем сохраненные данные
    data = await state.get_data()
    lead_id = data.get('lead_id')
    message_id = data.get('message_id')

    if not lead_id:
        await state.clear()
        await message.answer("⚠️ Произошла ошибка. Пожалуйста, напишите 'хочу записаться' снова")
        return

    async for db_session in db_adapter.get_session():
        try:
            # Находим заявку и обновляем контакт
            result = await db_session.execute(
                select(Lead).where(Lead.id == lead_id)
            )
            lead = result.scalar_one_or_none()

            if lead:
                lead.contact = phone
                await db_session.commit()

                # Обновляем контакт в CRM (Google Sheets)
                try:
                    from app.services.crm_adapter import crm_adapter
                    await crm_adapter.update_lead_contact(lead.id, phone)
                except Exception as e:
                    log.error(f"CRM update contact error (non-critical): {e}")

                # Отправляем уведомление менеджеру
                if notification_service.manager_notification_service:
                    msg_id = await notification_service.manager_notification_service.send_new_lead_notification(lead)

                    # Сохраняем ID сообщения
                    result = await db_session.execute(
                        select(Lead).where(Lead.id == lead_id)
                    )
                    lead = result.scalar_one()
                    lead.manager_chat_message_id = msg_id
                    await db_session.commit()

                # Редактируем исходное сообщение с запросом телефона
                if message_id:
                    try:
                        await message.bot.edit_message_text(
                            text="✅ Отлично! Ваша заявка принята!\n\n"
                                 f"📞 Менеджер свяжется с вами в ближайшее время.\n"
                                 f"Обычно мы отвечаем в течение 1 часа.\n\n"
                                 f"🆔 Номер заявки: #{lead.id}\n"
                                 f"Спасибо за интерес к нашему курсу! 🎓",
                            chat_id=message.chat.id,
                            message_id=message_id,
                            reply_markup=None
                        )
                    except TelegramBadRequest as e:
                        log.error(f"Error editing message: {e}")
                        # Fallback: отправляем новое сообщение
                        await message.answer(
                            "✅ Отлично! Ваша заявка принята!\n\n"
                            f"📞 Менеджер свяжется с вами в ближайшее время.\n"
                            f"Обычно мы отвечаем в течение 1 часа.\n\n"
                            f"🆔 Номер заявки: #{lead.id}\n"
                            f"Спасибо за интерес к нашему курсу! 🎓"
                        )
                else:
                    # Если нет ID сообщения, отправляем новое
                    await message.answer(
                        "✅ Отлично! Ваша заявка принята!\n\n"
                        f"📞 Менеджер свяжется с вами в ближайшее время.\n"
                        f"Обычно мы отвечаем в течение 1 часа.\n\n"
                        f"🆔 Номер заявки: #{lead.id}\n"
                        f"Спасибо за интерес к нашему курсу! 🎓"
                    )

                log.info(f"Contact collected for lead #{lead_id}: {phone}")
            else:
                await message.answer("⚠️ Произошла ошибка. Пожалуйста, напишите /start")

        except Exception as e:
            log.error(f"Error processing phone: {e}")
            await message.answer("⚠️ Произошла ошибка. Попробуйте позже.")
        finally:
            await state.clear()


@router.callback_query(F.data == "cancel_lead_collection")
async def cancel_lead_collection(callback: CallbackQuery, state: FSMContext):
    """Обработка отмены сбора контактов через inline кнопку"""
    user_id = callback.from_user.id
    username = callback.from_user.username or "unknown"
    
    log.info(f"Cancel button pressed by user {user_id} (@{username})")
    
    try:
        # Получаем ID сообщения для редактирования
        data = await state.get_data()
        message_id = data.get('message_id')
        lead_id = data.get('lead_id')
        
        log.debug(f"State data for user {user_id}: message_id={message_id}, lead_id={lead_id}")
        
        # Очищаем состояние
        await state.clear()
        log.info(f"FSM state cleared for user {user_id}")
        
        # Определяем какое сообщение редактировать
        target_message_id = message_id if message_id else callback.message.message_id
        chat_id = callback.message.chat.id
        
        log.info(f"Editing message: chat_id={chat_id}, message_id={target_message_id}")
        
        # Редактируем сообщение
        await callback.bot.edit_message_text(
            text="❌ Заявка отменена.\n\n"
                 "Если передумаете - просто напишите 'хочу записаться'",
            chat_id=chat_id,
            message_id=target_message_id,
            reply_markup=None
        )
        
        log.info(f"Message successfully edited for user {user_id}")
        
    except TelegramBadRequest as e:
        log.error(
            f"TelegramBadRequest when editing message for user {user_id} "
            f"(@{username}): {e}\n"
            f"Details: chat_id={callback.message.chat.id}, "
            f"message_id={data.get('message_id', 'N/A')}"
        )
        # Пытаемся хотя бы показать уведомление
        try:
            await callback.answer("❌ Заявка отменена", show_alert=False)
            log.info(f"Fallback callback answer sent for user {user_id}")
        except Exception as inner_e:
            log.error(
                f"Critical error: even callback.answer failed for user {user_id}: {inner_e}"
            )
    except Exception as e:
        log.error(
            f"Unexpected error in cancel_lead_collection for user {user_id} "
            f"(@{username}): {type(e).__name__}: {e}",
            exc_info=True
        )
        try:
            await callback.answer(
                "⚠️ Произошла ошибка при отмене. Попробуйте ещё раз или напишите /start",
                show_alert=True
            )
        except Exception:
            log.error("Failed to send error callback answer")
    
    log.info(f"Cancel flow completed for user {user_id} (@{username})")


@router.message(F.text)
async def handle_message(message: Message, state: FSMContext):
    """Обработка обычных сообщений"""
    # Игнорируем сообщения из группы менеджера
    if str(message.chat.id) == str(settings.MANAGER_CHAT_ID):
        return
    
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name
    user_message = message.text

    # Проверяем, хочет ли пользователь записаться
    if is_enrollment_intent(user_message):
        log.info(f"Enrollment intent detected from user {user_id}")
        
        async for db_session in db_adapter.get_session():
            try:
                contact = extract_phone_number(user_message) or extract_email(user_message)
                language = 'ru' if re.search('[а-яА-ЯёЁ]', user_message) else 'en'
                
                if contact:
                    lead = await lead_service.create_lead(
                        db_session=db_session,
                        telegram_id=user_id,
                        username=username,
                        full_name=full_name,
                        contact=contact,
                        message_text=user_message,
                        language=language
                    )
                    
                    if notification_service.manager_notification_service:
                        message_id = await notification_service.manager_notification_service.send_new_lead_notification(lead)
                        result = await db_session.execute(select(Lead).where(Lead.id == lead.id))
                        lead = result.scalar_one()
                        lead.manager_chat_message_id = message_id
                        await db_session.commit()
                    
                    await message.answer(
                        "✅ Заявка создана! Менеджер свяжется с вами в ближайшее время.\n\n"
                        f"📞 Ваш контакт: {contact}\n"
                        f"🆔 Номер заявки: #{lead.id}"
                    )
                else:
                    lead = await lead_service.create_lead(
                        db_session=db_session,
                        telegram_id=user_id,
                        username=username,
                        full_name=full_name,
                        message_text=user_message,
                        language=language
                    )
                    
                    await state.set_data({'lead_id': lead.id, 'message_id': None})
                    await state.set_state(ContactCollection.waiting_for_phone)

                    # Отправляем сообщение и сохраняем его ID
                    sent_message = await message.answer(
                        "📝 Отлично! Для оформления заявки мне нужен ваш контактный телефон.\n\n"
                        "Пожалуйста, напишите ваш номер телефона:\n"
                        "• +7 (999) 123-45-67\n"
                        "• +79991234567",
                        reply_markup=get_cancel_keyboard()
                    )
                    
                    # Сохраняем ID сообщения для последующего редактирования
                    await state.set_data({'lead_id': lead.id, 'message_id': sent_message.message_id})
                    log.info(f"Waiting for phone from user {user_id}, lead #{lead.id}")
                
                return
                
            except Exception as e:
                log.error(f"Error handling enrollment: {e}")
                await message.answer("⚠️ Произошла ошибка. Пожалуйста, попробуйте позже.")
                return
    
    # Проверяем, является ли сообщение контактом
    if is_contact_message(user_message):
        log.info(f"Contact message detected from user {user_id}")
        
        async for db_session in db_adapter.get_session():
            try:
                contact = extract_phone_number(user_message) or extract_email(user_message)
                
                if contact:
                    lead = await lead_service.create_lead(
                        db_session=db_session,
                        telegram_id=user_id,
                        username=username,
                        full_name=full_name,
                        contact=contact,
                        message_text=user_message,
                        language='ru' if re.search('[а-яА-ЯёЁ]', user_message) else 'en'
                    )
                    
                    if notification_service.manager_notification_service:
                        message_id = await notification_service.manager_notification_service.send_new_lead_notification(lead)
                        result = await db_session.execute(select(Lead).where(Lead.id == lead.id))
                        lead = result.scalar_one()
                        lead.manager_chat_message_id = message_id
                        await db_session.commit()
                    
                    await message.answer(
                        "✅ Спасибо! Ваш контакт получен.\n\n"
                        f"🆔 Номер заявки: #{lead.id}\n"
                        "📞 Менеджер свяжется с вами в ближайшее время!"
                    )
                    return
            
            except Exception as e:
                log.error(f"Error handling contact: {e}")

    # Проверяем, не заблокирован ли пользователь
    async for db_session in db_adapter.get_session():
        try:
            banned = await ban_service.is_banned(db_session, user_id)
            if banned:
                await message.answer(
                    "🚫 Вы заблокированы и не можете использовать бота.\n\n"
                    f"Причина: {banned.reason}"
                )
                return
        except Exception as e:
            log.error(f"Error checking ban status: {e}")
        break
    
    log.info(f"Message from {user_id} ({username}): {user_message[:50]}...")
    
    async for db_session in db_adapter.get_session():
        try:
            # Проверяем, есть ли ответ в FAQ
            faq_response = await faq_service.find_answer(user_message, db_session)
            
            if faq_response:
                # Отправляем ответ из FAQ
                await message.answer(faq_response['answer'])
                log.info(f"FAQ answer sent to user {user_id} (faq_id: {faq_response['faq_id']})")
                return
            
            # Если нет ответа в FAQ - создаем заявку и пересылаем менеджеру
            lead = await lead_service.create_lead(
                db_session=db_session,
                telegram_id=user_id,
                username=username,
                full_name=full_name,
                message_text=user_message,
                language=faq_response['language'] if faq_response else 'ru'
            )
            
            await message.answer(
                "✅ Спасибо за ваш вопрос!\n\n"
                "Я пока не знаю ответа, но передал ваш вопрос менеджеру.\n"
                "Он свяжется с вами в ближайшее время!\n\n"
                "Если хотите записаться на курс, напишите: <b>«Хочу записаться»</b>"
            )
            
            # Отправляем уведомление менеджеру
            log.info(f"Attempting to send notification to manager. Service: {notification_service.manager_notification_service}")
            if notification_service.manager_notification_service:
                message_id = await notification_service.manager_notification_service.send_new_lead_notification(lead)
                log.info(f"Notification sent. Message ID: {message_id}")
                
                # Сохраняем ID сообщения для обновления статуса
                if message_id:
                    from sqlalchemy import select
                    from app.database.models import Lead
                    result = await db_session.execute(
                        select(Lead).where(Lead.id == lead.id)
                    )
                    lead = result.scalar_one()
                    lead.manager_chat_message_id = message_id
                    await db_session.commit()
            
            log.info(f"Lead #{lead.id} created and forwarded to manager")
            
        except Exception as e:
            log.error(f"Error handling message: {e}")
            await message.answer(
                "⚠️ Произошла ошибка. Пожалуйста, попробуйте позже."
            )
