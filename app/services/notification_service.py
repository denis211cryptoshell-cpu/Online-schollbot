"""
Сервис уведомлений для менеджера
"""
from typing import Optional
from aiogram import Bot
from aiogram.types import ReplyKeyboardMarkup
from app.database.models import Lead, LeadStatus
from app.core.settings import settings
from app.core.logger import log
from app.keyboards.inline_kb import get_lead_status_keyboard
from app.utils.phone_formatter import format_phone_number


class ManagerNotificationService:
    """Сервис для отправки уведомлений менеджеру"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.manager_chat_id = settings.MANAGER_CHAT_ID
    
    async def send_new_lead_notification(self, lead: Lead) -> Optional[int]:
        """
        Отправка уведомления о новой заявке менеджеру
        
        Args:
            lead: Объект заявки
            
        Returns:
            int: ID отправленного сообщения (для обновления статуса позже)
        """
        try:
            # Формируем текст уведомления
            text = self._format_lead_notification(lead)
            
            # Отправляем сообщение с inline кнопками
            message = await self.bot.send_message(
                chat_id=self.manager_chat_id,
                text=text,
                reply_markup=get_lead_status_keyboard(lead.id),
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            
            log.info(f"Lead notification sent to manager: lead #{lead.id}, message #{message.message_id}")
            return message.message_id
            
        except Exception as e:
            log.error(f"Error sending lead notification to manager: {e}")
            log.error(f"Manager chat ID: {self.manager_chat_id}")
            log.error(f"Lead ID: {lead.id}")
            return None
    
    async def send_forwarded_message(self, user_message, original_sender) -> Optional[int]:
        """
        Пересылка нераспознанного вопроса менеджеру
        
        Args:
            user_message: Объект сообщения от пользователя
            original_sender: ID пользователя
            
        Returns:
            int: ID пересланного сообщения
        """
        try:
            # Пересылаем сообщение
            forwarded = await user_message.forward(self.manager_chat_id)
            
            # Отправляем пояснение
            await self.bot.send_message(
                chat_id=self.manager_chat_id,
                text=(
                    f"⚠️ <b>Нераспознанный вопрос</b>\n\n"
                    f"👤 От: {original_sender}\n"
                    f"Бот не нашел ответа в базе знаний.\n"
                    f"Пожалуйста, ответьте вручную."
                )
            )
            
            log.info(f"Message forwarded to manager from user {original_sender}")
            return forwarded.message_id
            
        except Exception as e:
            log.error(f"Error forwarding message to manager: {e}")
            return None
    
    async def update_lead_status_message(
        self,
        message_id: int,
        lead: Lead,
        new_status: LeadStatus
    ) -> bool:
        """
        Обновление сообщения с заявкой после изменения статуса
        
        Args:
            message_id: ID сообщения в чате менеджера
            lead: Объект заявки
            new_status: Новый статус
            
        Returns:
            bool: True если успешно
        """
        try:
            # Формируем обновленный текст
            text = self._format_lead_notification(lead, updated=True)
            
            # Убираем кнопки после изменения статуса
            await self.bot.edit_message_text(
                text=text,
                chat_id=self.manager_chat_id,
                message_id=message_id,
                parse_mode="HTML",
                reply_markup=None
            )
            
            log.info(f"Lead message updated in manager chat: message #{message_id}, status: {new_status.value}")
            return True
            
        except Exception as e:
            log.error(f"Error updating lead status message: {e}")
            return False
    
    def _format_lead_notification(self, lead: Lead, updated: bool = False) -> str:
        """
        Форматирование текста уведомления о заявке
        
        Args:
            lead: Объект заявки
            updated: True если это обновленное уведомление
            
        Returns:
            str: Отформатированный текст
        """
        # Статус с эмодзи
        status_emoji = {
            LeadStatus.NEW: "🆕",
            LeadStatus.ACCEPTED: "✅",
            LeadStatus.CALLBACK: "📞",
            LeadStatus.REJECTED: "❌"
        }.get(lead.status, "📋")
        
        status_text = {
            LeadStatus.NEW: "Новая",
            LeadStatus.ACCEPTED: "Принята",
            LeadStatus.CALLBACK: "Перезвонить",
            LeadStatus.REJECTED: "Отказ"
        }.get(lead.status, lead.status.value if lead.status else "Неизвестно")
        
        # Формируем текст
        text = (
            f"{status_emoji} <b>Заявка #{lead.id}</b>\n\n"
            f"👤 <b>Имя:</b> {lead.full_name or 'Не указано'}\n"
            f"🆔 <b>Telegram:</b> @{lead.username or 'N/A'} (ID: <code>{lead.telegram_id}</code>)\n"
        )
        
        if lead.contact:
            text += f"📞 <b>Контакт:</b> <code>{format_phone_number(lead.contact)}</code>\n"
        
        text += (
            f"\n💬 <b>Сообщение:</b>\n"
            f"<i>{lead.message_text[:500] if lead.message_text else 'Не указано'}</i>\n\n"
            f"📅 <b>Дата:</b> {lead.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"🌐 <b>Язык:</b> {'🇷🇺 Русский' if lead.language == 'ru' else '🇬🇧 English'}\n"
        )
        
        if updated:
            text += f"\n✅ <b>Статус:</b> {status_text}"
        
        return text
    
    async def send_statistics_report(self, stats_text: str) -> bool:
        """
        Отправка статистики менеджеру/админу
        
        Args:
            stats_text: Текст отчета
            
        Returns:
            bool: True если успешно
        """
        try:
            await self.bot.send_message(
                chat_id=self.manager_chat_id,
                text=stats_text,
                parse_mode="HTML"
            )
            log.info("Statistics report sent to manager")
            return True
        except Exception as e:
            log.error(f"Error sending statistics: {e}")
            return False
    
    async def send_message_to_user(self, telegram_id: int, text: str) -> bool:
        """
        Отправка сообщения пользователю от имени бота
        
        Args:
            telegram_id: Telegram ID пользователя
            text: Текст сообщения
            
        Returns:
            bool: True если успешно
        """
        try:
            await self.bot.send_message(
                chat_id=telegram_id,
                text=text,
                parse_mode="HTML"
            )
            log.info(f"Message sent to user {telegram_id}")
            return True
        except Exception as e:
            log.error(f"Error sending message to user {telegram_id}: {e}")
            return False


# Глобальный экземпляр (будет инициализирован при запуске)
manager_notification_service = None


def init_notification_service(bot: Bot):
    """Инициализация сервиса уведомлений"""
    global manager_notification_service
    manager_notification_service = ManagerNotificationService(bot)
    log.info("Manager notification service initialized")
    return manager_notification_service
