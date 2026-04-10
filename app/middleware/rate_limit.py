"""
Middleware для ограничения частоты сообщений (Rate Limiting)
"""
import time
from typing import Dict, Tuple
from aiogram.types import Message
from aiogram.filters import BaseFilter
from aiogram.fsm.context import FSMContext
from app.core.settings import settings
from app.core.logger import log
from app.services.redis_client import redis_client


class RateLimiter:
    """
    Rate limiter с поддержкой Redis и in-memory fallback.
    
    Хранит счётчики сообщений пользователей и блокирует при превышении лимита.
    Окно ограничения — 60 секунд (скользящее).
    """

    def __init__(self):
        # In-memory хранилище: {user_id: [(timestamp, type), ...]}
        self._memory_store: Dict[int, list] = {}

    async def _get_user_events(self, user_id: int) -> list:
        """Получить события пользователя за последний период"""
        now = time.time()
        window = 60  # окно в секундах

        if redis_client.is_available:
            try:
                events_raw = await redis_client.client.lrange(
                    f"rate_limit:{user_id}", 0, -1
                )
                events = []
                for ts_str in events_raw:
                    ts = float(ts_str)
                    if now - ts < window:
                        events.append(ts)
                return events
            except Exception as e:
                log.error(f"Redis rate limit read error: {e}")

        # Fallback: in-memory
        if user_id in self._memory_store:
            self._memory_store[user_id] = [
                ts for ts in self._memory_store[user_id] if now - ts < window
            ]
            return self._memory_store[user_id]
        return []

    async def _add_event(self, user_id: int, event_type: str = "message"):
        """Добавить событие пользователя"""
        now = time.time()
        key = f"rate_limit:{user_id}"

        if redis_client.is_available:
            try:
                pipe = redis_client.client.pipeline()
                pipe.lpush(key, str(now))
                pipe.expire(key, 120)  # TTL с запасом
                await pipe.execute()
                return
            except Exception as e:
                log.error(f"Redis rate limit write error: {e}")

        # Fallback: in-memory
        if user_id not in self._memory_store:
            self._memory_store[user_id] = []
        self._memory_store[user_id].append(now)

        # Очистка старых записей (раз в 5 минут)
        if len(self._memory_store) > 10000:
            self._cleanup_old()

    def _cleanup_old(self):
        """Очистка старых записей из in-memory"""
        now = time.time()
        to_remove = []
        for user_id, events in self._memory_store.items():
            self._memory_store[user_id] = [ts for ts in events if now - ts < 60]
            if not self._memory_store[user_id]:
                to_remove.append(user_id)
        for user_id in to_remove:
            del self._memory_store[user_id]

    async def check_rate_limit(
        self, user_id: int, event_type: str = "message"
    ) -> Tuple[bool, int, int]:
        """
        Проверить, не превысил ли пользователь лимит.
        
        Args:
            user_id: ID пользователя
            event_type: тип события ("message" или "lead")
            
        Returns:
            (allowed, current_count, limit) — можно ли отправить, текущий счётчик, лимит
        """
        limit = (
            settings.RATE_LIMIT_MESSAGES
            if event_type == "message"
            else settings.RATE_LIMIT_LEADS
        )

        events = await self._get_user_events(user_id)
        current_count = len(events)

        if current_count >= limit:
            log.warning(
                f"Rate limit exceeded for user {user_id}: "
                f"{current_count}/{limit} ({event_type})"
            )
            return False, current_count, limit

        return True, current_count, limit

    async def record_event(self, user_id: int, event_type: str = "message"):
        """Записать событие"""
        await self._add_event(user_id, event_type)

    async def get_remaining(self, user_id: int, event_type: str = "message") -> int:
        """Получить оставшееся количество запросов"""
        limit = (
            settings.RATE_LIMIT_MESSAGES
            if event_type == "message"
            else settings.RATE_LIMIT_LEADS
        )
        events = await self._get_user_events(user_id)
        remaining = limit - len(events)
        return max(0, remaining)


# Глобальный экземпляр
rate_limiter = RateLimiter()


class RateLimitFilter(BaseFilter):
    """
    Фильтр для проверки rate limiting.
    
    Используется в обработчиках для автоматической проверки лимитов.
    """

    event_type: str = "message"

    async def __call__(self, message: Message) -> bool:
        allowed, current, limit = await rate_limiter.check_rate_limit(
            message.from_user.id, self.event_type
        )

        if not allowed:
            remaining_time = 60  # секунд до сброса
            await message.answer(
                f"⏳ Пожалуйста, не отправляйте слишком много сообщений.\n"
                f"Лимит: {limit} сообщений в минуту.\n"
                f"Попробуйте через {remaining_time} секунд."
            )
            log.warning(
                f"Rate limit blocked for user {message.from_user.id}: "
                f"{current}/{limit} ({self.event_type})"
            )
            return False

        # Записываем событие
        await rate_limiter.record_event(message.from_user.id, self.event_type)
        return True
