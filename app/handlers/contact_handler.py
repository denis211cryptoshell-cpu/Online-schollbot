"""
Обработчик для сбора контактов и распознавания намерений
"""
import re
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from app.core.logger import log
from app.services.lead_service import lead_service
from app.services.notification_service import manager_notification_service
from app.database.adapter import db_adapter
from app.database.models import Lead

router = Router()


class ContactCollection(StatesGroup):
    """Состояния для сбора контактов"""
    waiting_for_phone = State()
    waiting_for_name = State()


def extract_phone_number(text: str) -> str:
    """
    Извлечение номера телефона из текста
    
    Поддерживаемые форматы:
    +7 (999) 123-45-67
    8 (999) 123-45-67
    +7 999 123 45 67
    89991234567
    +79991234567
    """
    # Паттерн для российских номеров
    phone_patterns = [
        r'(\+7|8)\s*\(?[0-9]{3}\)?\s*[0-9]{3}[-\s]?[0-9]{2}[-\s]?[0-9]{2}',
        r'(\+7|8)[0-9]{9}',
        r'\+[0-9]{1,3}\s*[0-9\s\-]{7,15}'
    ]
    
    for pattern in phone_patterns:
        match = re.search(pattern, text)
        if match:
            phone = match.group(0).strip()
            # Очищаем от лишних символов
            phone = re.sub(r'[^\d+]', '', phone)
            return phone
    
    return ""


def extract_email(text: str) -> str:
    """Извлечение email из текста"""
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    match = re.search(email_pattern, text)
    return match.group(0) if match else ""


def is_enrollment_intent(text: str) -> bool:
    """
    Определение намерения записаться на курс
    
    Args:
        text: Текст сообщения
        
    Returns:
        bool: True если пользователь хочет записаться
    """
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
        'ready to start'
    ]
    
    return any(phrase in text_lower for phrase in enrollment_phrases)


def is_contact_message(text: str) -> bool:
    """
    Проверка, является ли сообщение контактной информацией
    
    Args:
        text: Текст сообщения
        
    Returns:
        bool: True если сообщение содержит контакт
    """
    # Проверяем наличие телефона
    if extract_phone_number(text):
        return True
    
    # Проверяем наличие email
    if extract_email(text):
        return True
    
    return False


@router.message(F.text, ContactCollection.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    """Обработка введенного телефона"""
    text = message.text
    user_id = message.from_user.id
    
    # Проверяем команду отмены
    if text.lower() in ['/cancel', 'отмена', 'отменить']:
        await state.clear()
        await message.answer("❌ Заявка отменена.\n\nЕсли передумаете - просто напишите 'хочу записаться'")
        log.info(f"Lead collection cancelled for user {user_id}")
        return
    
    # Пытаемся извлечь телефон
    phone = extract_phone_number(text)
    
    if not phone:
        # Пробуем email
        email = extract_email(text)
        if email:
            phone = email  # Сохраняем email как контакт
        else:
            await message.answer(
                "⚠️ Я не смог распознать номер телефона или email.\n\n"
                "Пожалуйста, напишите:\n"
                "• Телефон: +7 (999) 123-45-67\n"
                "• Или email: example@mail.ru\n\n"
                "Или напишите /cancel для отмены."
            )
            return
    
    # Получаем сохраненный lead_id
    data = await state.get_data()
    lead_id = data.get('lead_id')
    
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
                
                # Отправляем уведомление менеджеру
                if manager_notification_service:
                    message_id = await manager_notification_service.send_new_lead_notification(lead)
                    
                    # Сохраняем ID сообщения
                    result = await db_session.execute(
                        select(Lead).where(Lead.id == lead_id)
                    )
                    lead = result.scalar_one()
                    lead.manager_chat_message_id = message_id
                    await db_session.commit()
                
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


@router.message(F.text)
async def handle_message_with_intent(message: Message, state: FSMContext):
    """
    Обработка сообщений с распознаванием намерений
    
    Этот обработчик проверяет:
    1. Хочет ли пользователь записаться на курс
    2. Оставляет ли пользователь контакт
    3. Если нет - пропускает для основного обработчика (FAQ)
    """
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name
    user_message = message.text
    
    log.info(f"Intent check from {user_id} ({username}): {user_message[:50]}...")
    
    # Проверяем, хочет ли пользователь записаться
    if is_enrollment_intent(user_message):
        log.info(f"Enrollment intent detected from user {user_id}")
        
        async for db_session in db_adapter.get_session():
            try:
                # Проверяем, есть ли уже контакт в сообщении
                contact = extract_phone_number(user_message) or extract_email(user_message)
                
                language = 'ru' if re.search('[а-яА-ЯёЁ]', user_message) else 'en'
                
                if contact:
                    # Создаем заявку сразу с контактом
                    lead = await lead_service.create_lead(
                        db_session=db_session,
                        telegram_id=user_id,
                        username=username,
                        full_name=full_name,
                        contact=contact,
                        message_text=user_message,
                        language=language
                    )
                    
                    # Отправляем уведомление менеджеру
                    if manager_notification_service:
                        message_id = await manager_notification_service.send_new_lead_notification(lead)
                        
                        # Сохраняем ID сообщения
                        result = await db_session.execute(
                            select(Lead).where(Lead.id == lead.id)
                        )
                        lead = result.scalar_one()
                        lead.manager_chat_message_id = message_id
                        await db_session.commit()
                    
                    await message.answer(
                        "✅ Заявка создана! Менеджер свяжется с вами в ближайшее время.\n\n"
                        f"📞 Ваш контакт: {contact}\n"
                        f"🆔 Номер заявки: #{lead.id}"
                    )
                else:
                    # Создаем заявку без контакта и просим телефон
                    lead = await lead_service.create_lead(
                        db_session=db_session,
                        telegram_id=user_id,
                        username=username,
                        full_name=full_name,
                        message_text=user_message,
                        language=language
                    )
                    
                    # Сохраняем lead_id в состоянии
                    await state.set_data({'lead_id': lead.id})
                    await state.set_state(ContactCollection.waiting_for_phone)
                    
                    await message.answer(
                        "📝 Отлично! Для оформления заявки мне нужен ваш контактный телефон.\n\n"
                        "Пожалуйста, напишите ваш номер телефона:\n"
                        "• +7 (999) 123-45-67\n"
                        "• +79991234567\n"
                        "• 8 999 123-45-67\n\n"
                        "Или напишите /cancel для отмены."
                    )
                    
                    log.info(f"Waiting for phone from user {user_id}, lead #{lead.id}")
                
                return  # Важно! Не передаем дальше
                
            except Exception as e:
                log.error(f"Error handling enrollment: {e}")
                await message.answer("⚠️ Произошла ошибка. Пожалуйста, попробуйте позже.")
                return
    
    # Проверяем, является ли сообщение контактом (без намерения записаться)
    if is_contact_message(user_message):
        log.info(f"Contact message detected from user {user_id}")
        
        async for db_session in db_adapter.get_session():
            try:
                contact = extract_phone_number(user_message) or extract_email(user_message)
                
                if contact:
                    # Создаем заявку с контактом
                    lead = await lead_service.create_lead(
                        db_session=db_session,
                        telegram_id=user_id,
                        username=username,
                        full_name=full_name,
                        contact=contact,
                        message_text=user_message,
                        language='ru' if re.search('[а-яА-ЯёЁ]', user_message) else 'en'
                    )
                    
                    # Отправляем уведомление менеджеру
                    if manager_notification_service:
                        message_id = await manager_notification_service.send_new_lead_notification(lead)
                        
                        # Сохраняем ID сообщения
                        result = await db_session.execute(
                            select(Lead).where(Lead.id == lead.id)
                        )
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
    
    # Если не распознали намерение - ничего не делаем
    # (основной обработчик в main_handler сработает через роутер)
    # Важно: не возвращаем ничего, чтобы другие роутеры могли обработать
    return
