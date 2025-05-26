import json
import logging
from typing import Optional, Any, Dict, List

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self._connection_pool: Optional[redis.ConnectionPool] = None

    async def connect(self):
        """Подключение к Redis с пулом соединений"""
        try:
            self._connection_pool = redis.ConnectionPool.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )

            self.redis = redis.Redis(connection_pool=self._connection_pool)

            # Проверка подключения
            await self.redis.ping()
            logger.info("✅ Redis connection established successfully")

        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        """Отключение от Redis"""
        try:
            if self.redis:
                await self.redis.close()
            if self._connection_pool:
                await self._connection_pool.disconnect()
            logger.info("✅ Redis connection closed")
        except Exception as e:
            logger.error(f"❌ Error closing Redis connection: {e}")

    async def ping(self) -> bool:
        """Проверка соединения с Redis"""
        try:
            if self.redis:
                await self.redis.ping()
                return True
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
        return False

    # Базовые операции
    async def get(self, key: str) -> Optional[str]:
        """Получение значения по ключу"""
        try:
            if self.redis:
                return await self.redis.get(key)
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
        return None

    async def set(
            self,
            key: str,
            value: str,
            expire: Optional[int] = 3600,
            nx: bool = False,
            xx: bool = False
    ) -> bool:
        """
        Установка значения с опциональным TTL
        nx: установить только если ключ не существует
        xx: установить только если ключ существует
        """
        try:
            if self.redis:
                if expire:
                    return await self.redis.setex(key, expire, value)
                else:
                    return await self.redis.set(key, value, nx=nx, xx=xx)
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
        return False

    async def delete(self, key: str) -> bool:
        """Удаление ключа"""
        try:
            if self.redis:
                return bool(await self.redis.delete(key))
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
        return False

    async def exists(self, key: str) -> bool:
        """Проверка существования ключа"""
        try:
            if self.redis:
                return bool(await self.redis.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
        return False

    async def expire(self, key: str, seconds: int) -> bool:
        """Установка TTL для ключа"""
        try:
            if self.redis:
                return await self.redis.expire(key, seconds)
        except Exception as e:
            logger.error(f"Redis EXPIRE error for key {key}: {e}")
        return False

    async def ttl(self, key: str) -> int:
        """Получение TTL ключа"""
        try:
            if self.redis:
                return await self.redis.ttl(key)
        except Exception as e:
            logger.error(f"Redis TTL error for key {key}: {e}")
        return -1

    # JSON операции
    async def set_json(
            self,
            key: str,
            value: Any,
            expire: Optional[int] = 3600
    ) -> bool:
        """Сохранение JSON объекта"""
        try:
            json_value = json.dumps(value, default=str)
            return await self.set(key, json_value, expire)
        except Exception as e:
            logger.error(f"Redis SET_JSON error for key {key}: {e}")
        return False

    async def get_json(self, key: str) -> Optional[Any]:
        """Получение JSON объекта"""
        try:
            value = await self.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.error(f"Redis GET_JSON error for key {key}: {e}")
        return None

    # Операции со списками
    async def lpush(self, key: str, *values: str) -> int:
        """Добавление элементов в начало списка"""
        try:
            if self.redis:
                return await self.redis.lpush(key, *values)
        except Exception as e:
            logger.error(f"Redis LPUSH error for key {key}: {e}")
        return 0

    async def rpush(self, key: str, *values: str) -> int:
        """Добавление элементов в конец списка"""
        try:
            if self.redis:
                return await self.redis.rpush(key, *values)
        except Exception as e:
            logger.error(f"Redis RPUSH error for key {key}: {e}")
        return 0

    async def lrange(self, key: str, start: int = 0, end: int = -1) -> List[str]:
        """Получение элементов списка"""
        try:
            if self.redis:
                return await self.redis.lrange(key, start, end)
        except Exception as e:
            logger.error(f"Redis LRANGE error for key {key}: {e}")
        return []

    async def llen(self, key: str) -> int:
        """Получение длины списка"""
        try:
            if self.redis:
                return await self.redis.llen(key)
        except Exception as e:
            logger.error(f"Redis LLEN error for key {key}: {e}")
        return 0

    # Операции с множествами
    async def sadd(self, key: str, *values: str) -> int:
        """Добавление элементов в множество"""
        try:
            if self.redis:
                return await self.redis.sadd(key, *values)
        except Exception as e:
            logger.error(f"Redis SADD error for key {key}: {e}")
        return 0

    async def srem(self, key: str, *values: str) -> int:
        """Удаление элементов из множества"""
        try:
            if self.redis:
                return await self.redis.srem(key, *values)
        except Exception as e:
            logger.error(f"Redis SREM error for key {key}: {e}")
        return 0

    async def smembers(self, key: str) -> set:
        """Получение всех элементов множества"""
        try:
            if self.redis:
                return await self.redis.smembers(key)
        except Exception as e:
            logger.error(f"Redis SMEMBERS error for key {key}: {e}")
        return set()

    async def sismember(self, key: str, value: str) -> bool:
        """Проверка принадлежности элемента множеству"""
        try:
            if self.redis:
                return await self.redis.sismember(key, value)
        except Exception as e:
            logger.error(f"Redis SISMEMBER error for key {key}: {e}")
        return False

    # Специальные методы для маркетплейса
    async def cache_user_session(
            self,
            session_id: str,
            user_data: Dict[str, Any],
            expire_hours: int = 24
    ) -> bool:
        """Кэширование пользовательской сессии"""
        key = f"session:{session_id}"
        expire_seconds = expire_hours * 3600
        return await self.set_json(key, user_data, expire_seconds)

    async def get_user_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Получение данных пользовательской сессии"""
        key = f"session:{session_id}"
        return await self.get_json(key)

    async def invalidate_user_session(self, session_id: str) -> bool:
        """Инвалидация пользовательской сессии"""
        key = f"session:{session_id}"
        return await self.delete(key)

    async def cache_cart(
            self,
            cart_id: str,
            cart_data: Dict[str, Any],
            expire_hours: int = 2
    ) -> bool:
        """Кэширование корзины"""
        key = f"cart:{cart_id}"
        expire_seconds = expire_hours * 3600
        return await self.set_json(key, cart_data, expire_seconds)

    async def get_cart(self, cart_id: str) -> Optional[Dict[str, Any]]:
        """Получение данных корзины"""
        key = f"cart:{cart_id}"
        return await self.get_json(key)

    async def clear_cart(self, cart_id: str) -> bool:
        """Очистка корзины"""
        key = f"cart:{cart_id}"
        return await self.delete(key)

    async def cache_proxy_list(
            self,
            purchase_id: int,
            proxy_data: List[Dict[str, Any]],
            expire_days: int = 30
    ) -> bool:
        """Кэширование списка прокси"""
        key = f"proxies:{purchase_id}"
        expire_seconds = expire_days * 24 * 3600
        return await self.set_json(key, proxy_data, expire_seconds)

    async def get_proxy_list(self, purchase_id: int) -> Optional[List[Dict[str, Any]]]:
        """Получение списка прокси"""
        key = f"proxies:{purchase_id}"
        return await self.get_json(key)

    async def cache_payment_data(
            self,
            transaction_id: str,
            payment_data: Dict[str, Any],
            expire_hours: int = 1
    ) -> bool:
        """Кэширование данных платежа"""
        key = f"payment:{transaction_id}"
        expire_seconds = expire_hours * 3600
        return await self.set_json(key, payment_data, expire_seconds)

    async def get_payment_data(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Получение данных платежа"""
        key = f"payment:{transaction_id}"
        return await self.get_json(key)

    async def rate_limit_check(
            self,
            identifier: str,
            limit: int = 100,
            window_seconds: int = 3600
    ) -> bool:
        """
        Проверка rate limiting
        Возвращает True если запрос разрешен, False если превышен лимит
        """
        key = f"rate_limit:{identifier}"
        try:
            if self.redis:
                current = await self.redis.get(key)
                if current is None:
                    # Первый запрос в окне
                    await self.redis.setex(key, window_seconds, 1)
                    return True
                elif int(current) < limit:
                    # Увеличиваем счетчик
                    await self.redis.incr(key)
                    return True
                else:
                    # Лимит превышен
                    return False
        except Exception as e:
            logger.error(f"Rate limit check error for {identifier}: {e}")
            # В случае ошибки разрешаем запрос
            return True
        return False

    async def increment_counter(self, key: str, expire: Optional[int] = None) -> int:
        """Инкремент счетчика"""
        try:
            if self.redis:
                value = await self.redis.incr(key)
                if expire and value == 1:  # Устанавливаем TTL только для нового ключа
                    await self.redis.expire(key, expire)
                return value
        except Exception as e:
            logger.error(f"Redis INCR error for key {key}: {e}")
        return 0

    async def get_keys_by_pattern(self, pattern: str) -> List[str]:
        """Получение ключей по паттерну"""
        try:
            if self.redis:
                return await self.redis.keys(pattern)
        except Exception as e:
            logger.error(f"Redis KEYS error for pattern {pattern}: {e}")
        return []

    async def cleanup_expired_sessions(self) -> int:
        """Очистка просроченных сессий"""
        try:
            session_keys = await self.get_keys_by_pattern("session:*")
            expired_count = 0

            for key in session_keys:
                ttl = await self.ttl(key)
                if ttl == -2:  # Ключ не существует
                    expired_count += 1
                elif ttl == -1:  # Ключ без TTL (не должно быть)
                    await self.delete(key)
                    expired_count += 1

            return expired_count
        except Exception as e:
            logger.error(f"Cleanup expired sessions error: {e}")
        return 0


# Глобальный экземпляр Redis клиента
redis_client = RedisClient()


# Dependency для получения Redis клиента
async def get_redis() -> RedisClient:
    if not redis_client.redis:
        await redis_client.connect()
    return redis_client


# Dependency для проверки подключения Redis
async def get_redis_health() -> bool:
    try:
        return await redis_client.ping()
    except:
        return False
