"""
Модель для заблокированных пользователей
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from app.database.adapter import Base


class BannedUser(Base):
    """Модель заблокированных пользователей"""
    __tablename__ = "banned_users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, nullable=False, unique=True, index=True, comment="Telegram ID пользователя")
    username = Column(String(100), comment="Username Telegram")
    full_name = Column(String(200), comment="Полное имя")
    reason = Column(String(500), comment="Причина блокировки")
    banned_by = Column(String(100), comment="Кто заблокировал (admin)")
    is_banned = Column(Boolean, default=True, comment="Активна ли блокировка")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    unbanned_at = Column(DateTime(timezone=True), comment="Дата разблокировки")
    
    def __repr__(self):
        return f"<BannedUser(telegram_id={self.telegram_id}, banned={self.is_banned})>"
