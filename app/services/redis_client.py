"""
Redis клиент для кэширования
"""
import json
from typing import Optional, Any
import redis.asyncio as redis
from app.core.settings import settings
from app.core.logger import log


class RedisClient:
    """Клиент для работы с Redis"""
    
    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self._initialized = False
    
    async def initialize(self):
        """Инициализация Redis подключения"""
        if self._initialized:
            log.warning("Redis already initialized")
            return
        
        try:
            self.client = redis.Redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Проверка подключения
            await self.client.ping()
            self._initialized = True
            log.info("Redis connected successfully")
            
        except redis.ConnectionError as e:
            log.error(f"Redis connection error: {e}")
            log.warning("Continuing without Redis cache")
            self.client = None
        except Exception as e:
            log.error(f"Redis initialization error: {e}")
            self.client = None
    
    async def close(self):
        """Закрытие Redis подключения"""
        if self.client:
            await self.client.aclose()
            self._initialized = False
            log.info("Redis connection closed")
    
    async def get(self, key: str) -> Optional[Any]:
        """Получение значения из кэша"""
        if not self.client:
            return None
        
        try:
            value = await self.client.get(key)
            if value:
                log.debug(f"Cache HIT for key: {key}")
                return json.loads(value)
            log.debug(f"Cache MISS for key: {key}")
            return None
        except Exception as e:
            log.error(f"Redis GET error: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Установка значения в кэш"""
        if not self.client:
            return False
        
        try:
            serialized = json.dumps(value, ensure_ascii=False)
            if ttl:
                await self.client.setex(key, ttl, serialized)
            else:
                await self.client.set(key, serialized)
            log.debug(f"Cache SET for key: {key}, TTL: {ttl}")
            return True
        except Exception as e:
            log.error(f"Redis SET error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Удаление значения из кэша"""
        if not self.client:
            return False
        
        try:
            await self.client.delete(key)
            log.debug(f"Cache DELETE for key: {key}")
            return True
        except Exception as e:
            log.error(f"Redis DELETE error: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> bool:
        """Очистка ключей по паттерну"""
        if not self.client:
            return False
        
        try:
            keys = await self.client.keys(pattern)
            if keys:
                await self.client.delete(*keys)
                log.debug(f"Cache CLEAR pattern: {pattern}, keys: {len(keys)}")
            return True
        except Exception as e:
            log.error(f"Redis CLEAR pattern error: {e}")
            return False
    
    @property
    def is_available(self) -> bool:
        """Проверка доступности Redis"""
        return self._initialized and self.client is not None


# Глобальный экземпляр
redis_client = RedisClient()
