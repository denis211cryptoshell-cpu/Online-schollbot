"""
CRM адаптер для переключения между Google Sheets и локальной БД
"""
from typing import Optional, Dict, List
from app.core.settings import settings
from app.core.logger import log
from app.services.google_sheets_service import google_sheets_service


class CRMAdapter:
    """
    Адаптер для работы с CRM
    
    Поддерживаемые бэкенды:
    - google_sheets: Google Sheets
    - database: Локальная БД (SQLite/PostgreSQL)
    """
    
    def __init__(self, backend: str = "database"):
        self.backend = backend
        log.info(f"CRM Adapter initialized with backend: {backend}")
    
    async def initialize(self) -> bool:
        """Инициализация CRM"""
        if self.backend == "google_sheets":
            return await google_sheets_service.initialize()
        return True
    
    async def add_lead(
        self,
        lead_id: int,
        telegram_id: int,
        username: str,
        full_name: str,
        contact: str,
        message_text: str,
        status: str,
        language: str
    ) -> bool:
        """
        Добавление заявки в CRM
        
        Args:
            lead_id: ID заявки
            telegram_id: Telegram ID
            username: Username
            full_name: Полное имя
            contact: Контакт
            message_text: Текст сообщения
            status: Статус
            language: Язык
            
        Returns:
            bool: True если успешно
        """
        if self.backend == "google_sheets":
            return await google_sheets_service.add_lead(
                lead_id=lead_id,
                telegram_id=telegram_id,
                username=username,
                full_name=full_name,
                contact=contact,
                message_text=message_text,
                status=status,
                language=language
            )
        
        # Для database - ничего не делаем (заявка уже в БД)
        log.debug(f"Lead #{lead_id} saved to database (no CRM action needed)")
        return True
    
    async def update_lead_contact(self, lead_id: int, new_contact: str) -> bool:
        """Обновление контакта заявки в CRM"""
        if self.backend == "google_sheets":
            return await google_sheets_service.update_lead_contact(
                lead_id=lead_id,
                new_contact=new_contact
            )
        
        log.debug(f"Lead #{lead_id} contact updated in database")
        return True
    
    async def update_lead_status(self, lead_id: int, new_status: str) -> bool:
        """
        Обновление статуса заявки в CRM
        
        Args:
            lead_id: ID заявки
            new_status: Новый статус
            
        Returns:
            bool: True если успешно
        """
        if self.backend == "google_sheets":
            return await google_sheets_service.update_lead_status(
                lead_id=lead_id,
                new_status=new_status
            )
        
        # Для database - ничего не делаем (статус уже в БД)
        log.debug(f"Lead #{lead_id} status updated in database")
        return True
    
    async def get_statistics(self) -> Dict:
        """
        Получение статистики из CRM
        
        Returns:
            Dict: Статистика
        """
        if self.backend == "google_sheets":
            return await google_sheets_service.get_statistics()
        
        # Для database - возвращаем пустую статистику
        # (статистика берется из локальной БД через lead_service)
        return {}


# Глобальный экземпляр
# Бэкенд выбирается из настроек
crm_adapter = CRMAdapter(
    backend="google_sheets" if settings.GOOGLE_SHEETS_ENABLED else "database"
)
