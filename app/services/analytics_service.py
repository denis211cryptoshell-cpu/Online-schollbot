"""
Сервис расширенной статистики и аналитики
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Lead, LeadStatus, LeadStatusHistory, FAQ, Statistic
from app.core.logger import log


class AnalyticsService:
    """Сервис для аналитики и статистики"""
    
    async def get_conversion_funnel(self, db_session: AsyncSession, days: int = 7) -> Dict:
        """
        Воронка конверсии
        
        Returns:
            Dict: Данные воронки
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Всего сообщений (примерно - по количеству заявок + FAQ ответов)
        total_messages_result = await db_session.execute(
            select(func.count(Lead.id)).where(
                Lead.created_at >= start_date,
                Lead.created_at <= end_date
            )
        )
        total_messages = total_messages_result.scalar() or 0
        
        # Количество заявок
        total_leads_result = await db_session.execute(
            select(func.count(Lead.id)).where(
                Lead.created_at >= start_date,
                Lead.created_at <= end_date
            )
        )
        total_leads = total_leads_result.scalar() or 0
        
        # Заявки по статусам
        status_result = await db_session.execute(
            select(Lead.status, func.count(Lead.id)).where(
                Lead.created_at >= start_date,
                Lead.created_at <= end_date
            ).group_by(Lead.status)
        )
        status_counts = {status.value if status else 'unknown': count for status, count in status_result.all()}
        
        # Конверсия в принятые
        accepted = status_counts.get('accepted', 0)
        conversion_rate = (accepted / total_leads * 100) if total_leads > 0 else 0
        
        # Среднее время обработки
        history_result = await db_session.execute(
            select(LeadStatusHistory).where(
                LeadStatusHistory.changed_at >= start_date,
                LeadStatusHistory.changed_at <= end_date,
                LeadStatusHistory.old_status == LeadStatus.NEW.value
            ).order_by(LeadStatusHistory.changed_at)
        )
        history_records = history_result.scalars().all()
        
        avg_processing_time = "N/A"
        if history_records:
            # Примерный расчет: время от создания до первой смены статуса
            processing_times = []
            for h in history_records:
                # Находим заявку
                lead_result = await db_session.execute(
                    select(Lead).where(Lead.id == h.lead_id)
                )
                lead = lead_result.scalar_one_or_none()
                if lead:
                    time_diff = h.changed_at - lead.created_at
                    processing_times.append(time_diff.total_seconds() / 60)  # в минутах
            
            if processing_times:
                avg_minutes = sum(processing_times) / len(processing_times)
                if avg_minutes < 60:
                    avg_processing_time = f"{avg_minutes:.0f} мин"
                else:
                    avg_processing_time = f"{avg_minutes/60:.1f} ч"
        
        return {
            'period_days': days,
            'total_messages': total_messages,
            'total_leads': total_leads,
            'status_breakdown': status_counts,
            'accepted': accepted,
            'callback': status_counts.get('callback', 0),
            'rejected': status_counts.get('rejected', 0),
            'new': status_counts.get('new', 0),
            'conversion_rate': f"{conversion_rate:.1f}%",
            'avg_processing_time': avg_processing_time
        }
    
    async def get_daily_stats(self, db_session: AsyncSession, days: int = 30) -> List[Dict]:
        """
        Получить статистику по дням
        
        Args:
            db_session: Сессия БД
            days: Количество дней
            
        Returns:
            List[Dict]: Статистика по дням
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Группировка по дням
        result = await db_session.execute(
            select(
                func.date(Lead.created_at).label('date'),
                func.count(Lead.id).label('total'),
                func.sum(func.case((Lead.status == LeadStatus.ACCEPTED, 1), else_=0)).label('accepted'),
                func.sum(func.case((Lead.status == LeadStatus.CALLBACK, 1), else_=0)).label('callback'),
                func.sum(func.case((Lead.status == LeadStatus.REJECTED, 1), else_=0)).label('rejected'),
                func.sum(func.case((Lead.status == LeadStatus.NEW, 1), else_=0)).label('new')
            ).where(
                Lead.created_at >= start_date,
                Lead.created_at <= end_date
            ).group_by(
                func.date(Lead.created_at)
            ).order_by(
                func.date(Lead.created_at)
            )
        )
        
        daily_stats = []
        for row in result.all():
            daily_stats.append({
                'date': row.date,
                'total': row.total or 0,
                'accepted': row.accepted or 0,
                'callback': row.callback or 0,
                'rejected': row.rejected or 0,
                'new': row.new or 0
            })
        
        return daily_stats
    
    async def get_top_faq_questions(self, db_session: AsyncSession, limit: int = 10) -> List[Dict]:
        """
        Топ используемых вопросов FAQ
        
        Args:
            db_session: Сессия БД
            limit: Количество записей
            
        Returns:
            List[Dict]: Топ вопросов
        """
        result = await db_session.execute(
            select(FAQ.question_ru, FAQ.usage_count)
            .where(FAQ.is_active == True)
            .order_by(desc(FAQ.usage_count))
            .limit(limit)
        )
        
        return [{'question': q, 'count': c} for q, c in result.all()]
    
    async def get_time_saved_stats(self, db_session: AsyncSession, days: int = 7) -> Dict:
        """
        Статистика сэкономленного времени
        
        Args:
            db_session: Сессия БД
            days: Количество дней
            
        Returns:
            Dict: Статистика экономии времени
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Считаем FAQ ответы
        faq_result = await db_session.execute(
            select(func.sum(FAQ.usage_count)).where(FAQ.is_active == True)
        )
        total_faq_answers = faq_result.scalar() or 0
        
        # Примерная экономия: каждый FAQ ответ = 3 минуты
        time_saved_minutes = total_faq_answers * 3
        time_saved_hours = time_saved_minutes / 60
        
        # Заявки обработанные автоматически
        leads_result = await db_session.execute(
            select(func.count(Lead.id)).where(
                Lead.created_at >= start_date,
                Lead.created_at <= end_date
            )
        )
        total_leads = leads_result.scalar() or 0
        
        # Экономия на заявках: каждая заявка = 5 минут на обработку
        leads_time_saved = total_leads * 5
        leads_time_hours = leads_time_saved / 60
        
        return {
            'period_days': days,
            'faq_answers': total_faq_answers,
            'time_saved_faq_minutes': time_saved_minutes,
            'time_saved_faq_hours': f"{time_saved_hours:.1f}",
            'total_leads': total_leads,
            'time_saved_leads_minutes': leads_time_saved,
            'time_saved_leads_hours': f"{leads_time_hours:.1f}",
            'total_time_saved_hours': f"{time_saved_hours + leads_time_hours:.1f}"
        }
    
    async def get_user_activity_stats(self, db_session: AsyncSession, days: int = 7) -> Dict:
        """
        Статистика активности пользователей
        
        Args:
            db_session: Сессия БД
            days: Количество дней
            
        Returns:
            Dict: Статистика активности
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Уникальные пользователи
        unique_users_result = await db_session.execute(
            select(func.count(func.distinct(Lead.telegram_id))).where(
                Lead.created_at >= start_date,
                Lead.created_at <= end_date
            )
        )
        unique_users = unique_users_result.scalar() or 0
        
        # Новые пользователи (первая заявка)
        new_users_result = await db_session.execute(
            select(func.count(func.distinct(Lead.telegram_id))).where(
                Lead.created_at >= start_date,
                Lead.created_at <= end_date
            )
        )
        new_users = new_users_result.scalar() or 0
        
        # Возвращающиеся пользователи
        returning_users = unique_users - new_users
        
        # Средняя частота заявок на пользователя
        total_leads_result = await db_session.execute(
            select(func.count(Lead.id)).where(
                Lead.created_at >= start_date,
                Lead.created_at <= end_date
            )
        )
        total_leads = total_leads_result.scalar() or 0
        avg_leads_per_user = (total_leads / unique_users) if unique_users > 0 else 0
        
        return {
            'period_days': days,
            'unique_users': unique_users,
            'new_users': new_users,
            'returning_users': returning_users,
            'total_leads': total_leads,
            'avg_leads_per_user': f"{avg_leads_per_user:.2f}"
        }
    
    def format_funnel_text(self, funnel: Dict) -> str:
        """
        Форматировать воронку в текст
        
        Args:
            funnel: Данные воронки
            
        Returns:
            str: Отформатированный текст
        """
        total = funnel['total_leads']
        
        # Создаем текстовую диаграмму
        def bar(value, max_value, width=20):
            if max_value == 0:
                return ""
            filled = int((value / max_value) * width)
            return "█" * filled + "░" * (width - filled)
        
        text = (
            f"📊 <b>Воронка конверсии ({funnel['period_days']} дн.)</b>\n\n"
            f"💬 Всего обращений: {funnel['total_messages']}\n"
            f"📝 Заявок создано: {total}\n\n"
            f"<b>Статусы заявок:</b>\n"
            f"🆕 Новые:      {bar(funnel['new'], total)} {funnel['new']}\n"
            f"✅ Принятые:   {bar(funnel['accepted'], total)} {funnel['accepted']}\n"
            f"📞 Перезвон:   {bar(funnel['callback'], total)} {funnel['callback']}\n"
            f"❌ Отказ:      {bar(funnel['rejected'], total)} {funnel['rejected']}\n\n"
            f"📈 <b>Конверсия:</b> {funnel['conversion_rate']}\n"
            f"⏱ <b>Среднее время обработки:</b> {funnel['avg_processing_time']}"
        )
        
        return text
    
    def format_daily_stats_text(self, daily_stats: List[Dict]) -> str:
        """
        Форматировать дневную статистику в текст
        
        Args:
            daily_stats: Статистика по дням
            
        Returns:
            str: Отформатированный текст
        """
        if not daily_stats:
            return "📊 Нет данных за период"
        
        # Находим максимум для масштаба
        max_value = max(day['total'] for day in daily_stats) if daily_stats else 1
        
        text = "📈 <b>Динамика заявок (последние дни)</b>\n\n"
        
        for day in daily_stats[-14:]:  # Показываем последние 14 дней
            date_str = day['date'] if isinstance(day['date'], str) else str(day['date'])[5:]  # MM-DD
            bar_len = int((day['total'] / max_value) * 20) if max_value > 0 else 0
            bar = "█" * bar_len + "░" * (20 - bar_len)
            
            text += f"{date_str} {bar} {day['total']}\n"
        
        return text
    
    def format_time_saved_text(self, time_stats: Dict) -> str:
        """
        Форматировать статистику экономии времени в текст
        
        Args:
            time_stats: Данные экономии времени
            
        Returns:
            str: Отформатированный текст
        """
        text = (
            f"⏱ <b>Экономия времени ({time_stats['period_days']} дн.)</b>\n\n"
            f"💬 FAQ ответов: {time_stats['faq_answers']}\n"
            f"⏰ Экономия на FAQ: {time_stats['time_saved_faq_hours']} ч\n\n"
            f"📝 Заявок обработано: {time_stats['total_leads']}\n"
            f"⏰ Экономия на заявках: {time_stats['time_saved_leads_hours']} ч\n\n"
            f"🎯 <b>Всего сэкономлено: {time_stats['total_time_saved_hours']} часов</b>\n\n"
            f"💰 <b>Экономия в деньгах:</b>\n"
            f"При ставке менеджера 500 руб/ч:\n"
            f"Сэкономлено: {int(time_stats['total_time_saved_hours']) * 500} руб"
        )
        
        return text


# Глобальный экземпляр
analytics_service = AnalyticsService()
