"""
Сервис для работы с заявками (Leads)
"""
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Lead, LeadStatus, LeadStatusHistory, Statistic, FAQ
from app.services.crm_adapter import crm_adapter
from app.core.logger import log


class LeadService:
    """Сервис для работы с заявками"""
    
    async def create_lead(
        self,
        db_session: AsyncSession,
        telegram_id: int,
        username: Optional[str] = None,
        full_name: Optional[str] = None,
        contact: Optional[str] = None,
        message_text: Optional[str] = None,
        language: str = "ru"
    ) -> Lead:
        """Создание новой заявки"""
        try:
            lead = Lead(
                telegram_id=telegram_id,
                username=username,
                full_name=full_name,
                contact=contact,
                message_text=message_text,
                language=language
            )
            
            db_session.add(lead)
            await db_session.flush()
            
            # Создаем запись в истории статусов
            history = LeadStatusHistory(
                lead_id=lead.id,
                old_status=None,
                new_status=LeadStatus.NEW.value,
                changed_by="bot"
            )
            db_session.add(history)
            
            await db_session.commit()
            await db_session.refresh(lead)
            
            # Сохраняем в CRM (Google Sheets или БД)
            try:
                await crm_adapter.add_lead(
                    lead_id=lead.id,
                    telegram_id=lead.telegram_id,
                    username=lead.username or "",
                    full_name=lead.full_name or "",
                    contact=lead.contact or "",
                    message_text=lead.message_text or "",
                    status=LeadStatus.NEW.value,
                    language=lead.language or "ru"
                )
            except Exception as e:
                log.error(f"CRM add_lead error (non-critical): {e}")
            
            log.info(f"Lead created: #{lead.id} (telegram_id={telegram_id})")
            return lead
            
        except Exception as e:
            log.error(f"Error creating lead: {e}")
            await db_session.rollback()
            raise
    
    async def update_status(
        self,
        db_session: AsyncSession,
        lead_id: int,
        new_status: LeadStatus,
        changed_by: str = "manager"
    ) -> Optional[Lead]:
        """Обновление статуса заявки"""
        try:
            result = await db_session.execute(
                select(Lead).where(Lead.id == lead_id)
            )
            lead = result.scalar_one_or_none()
            
            if not lead:
                log.warning(f"Lead #{lead_id} not found")
                return None
            
            old_status = lead.status
            
            # Сохраняем старый статус для истории
            old_status_value = old_status.value if old_status else None
            
            lead.status = new_status
            await db_session.flush()
            
            # Создаем запись в истории
            history = LeadStatusHistory(
                lead_id=lead_id,
                old_status=old_status_value,
                new_status=new_status.value,
                changed_by=changed_by
            )
            db_session.add(history)
            
            await db_session.commit()
            await db_session.refresh(lead)
            
            # Обновляем статус в CRM
            try:
                await crm_adapter.update_lead_status(
                    lead_id=lead_id,
                    new_status=new_status.value
                )
            except Exception as e:
                log.error(f"CRM update_lead_status error (non-critical): {e}")
            
            log.info(f"Lead #{lead_id} status updated: {old_status_value} -> {new_status.value}")
            return lead
            
        except Exception as e:
            log.error(f"Error updating lead status: {e}")
            await db_session.rollback()
            raise
    
    async def get_lead(self, db_session: AsyncSession, lead_id: int) -> Optional[Lead]:
        """Получение заявки по ID"""
        result = await db_session.execute(
            select(Lead).where(Lead.id == lead_id)
        )
        return result.scalar_one_or_none()
    
    async def get_leads_by_status(
        self,
        db_session: AsyncSession,
        status: LeadStatus,
        limit: int = 50
    ) -> List[Lead]:
        """Получение заявок по статусу"""
        result = await db_session.execute(
            select(Lead)
            .where(Lead.status == status)
            .order_by(desc(Lead.created_at))
            .limit(limit)
        )
        return result.scalars().all()
    
    async def get_leads_by_date_range(
        self,
        db_session: AsyncSession,
        start_date: datetime,
        end_date: datetime
    ) -> List[Lead]:
        """Получение заявок за период"""
        result = await db_session.execute(
            select(Lead)
            .where(Lead.created_at >= start_date, Lead.created_at <= end_date)
            .order_by(desc(Lead.created_at))
        )
        return result.scalars().all()
    
    async def get_statistics(
        self,
        db_session: AsyncSession,
        days: int = 7
    ) -> Dict:
        """Получение статистики за период"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Общее количество заявок
        total_result = await db_session.execute(
            select(func.count(Lead.id))
            .where(Lead.created_at >= start_date, Lead.created_at <= end_date)
        )
        total_leads = total_result.scalar() or 0
        
        # Заявки по статусам
        status_result = await db_session.execute(
            select(Lead.status, func.count(Lead.id))
            .where(Lead.created_at >= start_date, Lead.created_at <= end_date)
            .group_by(Lead.status)
        )
        status_counts = {status.value: count for status, count in status_result.all()}
        
        # Топ FAQ вопросов
        faq_result = await db_session.execute(
            select(FAQ.question_ru, FAQ.usage_count)
            .order_by(desc(FAQ.usage_count))
            .limit(10)
        )
        top_faqs = faq_result.all()
        
        return {
            'period_days': days,
            'total_leads': total_leads,
            'status_breakdown': status_counts,
            'top_faqs': [{'question': q, 'count': c} for q, c in top_faqs],
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        }


# Глобальный экземпляр
lead_service = LeadService()
