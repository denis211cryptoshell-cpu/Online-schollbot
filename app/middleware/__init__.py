"""
Middleware для автоматического ограничения частоты сообщений
"""
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from app.middleware.rate_limit import rate_limiter
from app.core.settings import settings
from app.core.logger import log


class RateLimitMiddleware(BaseMiddleware):
    """
    Middleware для автоматического rate limiting.
    
    Перехватывает все сообщения и проверяет лимиты.
    При превышении — отправляет предупреждение и отклоняет сообщение.
    """

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        # Пропускаем rate limiting для админов
        if event.from_user.id in settings.admin_ids:
            return await handler(event, data)

        # Проверяем лимит сообщений
        allowed, current, limit = await rate_limiter.check_rate_limit(
            event.from_user.id, "message"
        )

        if not allowed:
            # Время до сброса (примерно)
            await event.answer(
                f"⏳ Пожалуйста, подождите перед отправкой следующего сообщения.\n"
                f"Лимит: {limit} сообщений в минуту.\n"
                f"Попробуйте через ~60 секунд."
            )
            log.warning(
                f"Rate limit blocked for user {event.from_user.id}: "
                f"{current}/{limit} messages/min"
            )
            return None

        # Записываем событие и передаём дальше
        await rate_limiter.record_event(event.from_user.id, "message")
        return await handler(event, data)


class CallbackRateLimitMiddleware(BaseMiddleware):
    """
    Middleware для rate limiting callback-запросов.
    Лимит для callback обычно выше, т.к. это клики по кнопкам.
    """

    async def __call__(
        self,
        handler: Callable[[CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Пропускаем rate limiting для админов
        if event.from_user.id in settings.admin_ids:
            return await handler(event, data)

        # Для callback используем лимит сообщений (можно вынести отдельно)
        allowed, current, limit = await rate_limiter.check_rate_limit(
            event.from_user.id, "message"
        )

        if not allowed:
            await event.answer(
                "⏳ Слишком много запросов. Подождите немного.",
                show_alert=True
            )
            log.warning(
                f"Callback rate limit blocked for user {event.from_user.id}: "
                f"{current}/{limit}"
            )
            return None

        await rate_limiter.record_event(event.from_user.id, "message")
        return await handler(event, data)
