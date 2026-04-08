"""
Сервис для управления блокировками пользователей
"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models_ban import BannedUser
from app.core.logger import log


class BanService:
    """Сервис для блокировки/разблокировки пользователей"""
    
    async def ban_user(
        self,
        db_session: AsyncSession,
        telegram_id: int,
        username: str,
        full_name: str,
        reason: str,
        banned_by: str
    ) -> BannedUser:
        """
        Заблокировать пользователя
        
        Args:
            db_session: Сессия БД
            telegram_id: Telegram ID
            username: Username
            full_name: Полное имя
            reason: Причина
            banned_by: Кто заблокировал
            
        Returns:
            BannedUser: Объект блокировки
        """
        try:
            # Проверяем, не заблокирован ли уже
            existing = await self.is_banned(db_session, telegram_id)
            if existing:
                log.warning(f"User {telegram_id} is already banned")
                return existing
            
            banned_user = BannedUser(
                telegram_id=telegram_id,
                username=username,
                full_name=full_name,
                reason=reason,
                banned_by=banned_by,
                is_banned=True
            )
            
            db_session.add(banned_user)
            await db_session.commit()
            await db_session.refresh(banned_user)
            
            log.info(f"User {telegram_id} banned by {banned_by}. Reason: {reason}")
            return banned_user
            
        except Exception as e:
            log.error(f"Error banning user {telegram_id}: {e}")
            await db_session.rollback()
            raise
    
    async def unban_user(
        self,
        db_session: AsyncSession,
        telegram_id: int,
        unbanned_by: str
    ) -> bool:
        """
        Разблокировать пользователя
        
        Args:
            db_session: Сессия БД
            telegram_id: Telegram ID
            unbanned_by: Кто разблокировал
            
        Returns:
            bool: True если успешно
        """
        try:
            result = await db_session.execute(
                select(BannedUser).where(
                    BannedUser.telegram_id == telegram_id,
                    BannedUser.is_banned == True
                )
            )
            banned_user = result.scalar_one_or_none()
            
            if not banned_user:
                log.warning(f"User {telegram_id} is not banned")
                return False
            
            banned_user.is_banned = False
            banned_user.unbanned_at = datetime.now()
            await db_session.commit()
            
            log.info(f"User {telegram_id} unbanned by {unbanned_by}")
            return True
            
        except Exception as e:
            log.error(f"Error unbanning user {telegram_id}: {e}")
            await db_session.rollback()
            raise
    
    async def is_banned(self, db_session: AsyncSession, telegram_id: int) -> Optional[BannedUser]:
        """
        Проверка, заблокирован ли пользователь
        
        Args:
            db_session: Сессия БД
            telegram_id: Telegram ID
            
        Returns:
            Optional[BannedUser]: Объект блокировки или None
        """
        try:
            result = await db_session.execute(
                select(BannedUser).where(
                    BannedUser.telegram_id == telegram_id,
                    BannedUser.is_banned == True
                )
            )
            return result.scalar_one_or_none()
            
        except Exception as e:
            log.error(f"Error checking ban status for {telegram_id}: {e}")
            return None
    
    async def get_banned_users(
        self,
        db_session: AsyncSession,
        limit: int = 50
    ) -> List[BannedUser]:
        """
        Получить список заблокированных пользователей
        
        Args:
            db_session: Сессия БД
            limit: Количество записей
            
        Returns:
            List[BannedUser]: Список заблокированных пользователей
        """
        try:
            result = await db_session.execute(
                select(BannedUser)
                .where(BannedUser.is_banned == True)
                .order_by(BannedUser.created_at.desc())
                .limit(limit)
            )
            return result.scalars().all()
            
        except Exception as e:
            log.error(f"Error getting banned users: {e}")
            return []


# Глобальный экземпляр
ban_service = BanService()
