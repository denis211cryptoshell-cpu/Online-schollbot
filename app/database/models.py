"""
Модели базы данных
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.sql import func
import enum
from app.database.adapter import Base
from app.database.models_ban import BannedUser  # Импортируем для регистрации модели


class LeadStatus(str, enum.Enum):
    """Статусы заявок"""
    NEW = "new"
    ACCEPTED = "accepted"
    CALLBACK = "callback"
    REJECTED = "rejected"


class FAQ(Base):
    """Модель для часто задаваемых вопросов"""
    __tablename__ = "faqs"
    
    id = Column(Integer, primary_key=True, index=True)
    question_ru = Column(String(500), nullable=False, comment="Вопрос на русском")
    question_en = Column(String(500), nullable=False, comment="Вопрос на английском")
    answer_ru = Column(Text, nullable=False, comment="Ответ на русском")
    answer_en = Column(Text, nullable=False, comment="Ответ на английском")
    keywords = Column(String(1000), nullable=False, comment="Ключевые слова через запятую")
    is_active = Column(Boolean, default=True, comment="Активен ли вопрос")
    usage_count = Column(Integer, default=0, comment="Счетчик использований")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<FAQ(id={self.id}, question='{self.question_ru}')>"


class Lead(Base):
    """Модель для заявок"""
    __tablename__ = "leads"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, nullable=False, index=True, comment="Telegram ID пользователя")
    username = Column(String(100), comment="Username Telegram")
    full_name = Column(String(200), comment="Полное имя")
    contact = Column(String(500), comment="Контакт (телефон/email)")
    message_text = Column(Text, comment="Текст сообщения")
    status = Column(SQLEnum(LeadStatus), default=LeadStatus.NEW, comment="Статус заявки")
    language = Column(String(2), default="ru", comment="Язык пользователя")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    manager_chat_message_id = Column(Integer, comment="ID сообщения в чате менеджера")
    
    def __repr__(self):
        return f"<Lead(id={self.id}, telegram_id={self.telegram_id}, status={self.status})>"


class LeadStatusHistory(Base):
    """История изменений статусов заявок"""
    __tablename__ = "lead_status_history"
    
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, nullable=False, index=True, comment="ID заявки")
    old_status = Column(String(20), comment="Предыдущий статус")
    new_status = Column(String(20), nullable=False, comment="Новый статус")
    changed_by = Column(String(100), comment="Кто изменил (manager/admin)")
    changed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<LeadStatusHistory(lead_id={self.lead_id}, {self.old_status}->{self.new_status})>"


class Statistic(Base):
    """Модель для статистики"""
    __tablename__ = "statistics"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String(10), nullable=False, index=True, comment="Дата (YYYY-MM-DD)")
    total_messages = Column(Integer, default=0, comment="Всего сообщений")
    total_leads = Column(Integer, default=0, comment="Всего заявок")
    faq_answers = Column(Integer, default=0, comment="Ответов через FAQ")
    manager_forwards = Column(Integer, default=0, comment="Переслано менеджеру")
    time_saved_minutes = Column(Integer, default=0, comment="Сэкономлено времени (минуты)")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<Statistic(date={self.date}, leads={self.total_leads})>"
