"""
Production rate limiter с Redis.
"""

import time
from redis import Redis


class RateLimiter:
    """Распределенный rate limiter на основе Redis."""

    def __init__(self, max_requests: int, window_minutes: int):
        self.max_requests = max_requests
        self.window_seconds = window_minutes * 60

    def allow_request(self, redis: Redis, key: str) -> bool:
        """
        Проверяет разрешен ли запрос.

        Args:
            redis: Redis клиент
            key: Уникальный ключ для rate limiting

        Returns:
            bool: True если запрос разрешен
        """
        try:
            current_time = int(time.time())
            window_start = current_time - self.window_seconds

            # Удаляем старые записи
            redis.zremrangebyscore(key, 0, window_start)

            # Проверяем текущее количество запросов
            current_count = redis.zcard(key)

            if current_count >= self.max_requests:
                return False

            # Добавляем текущий запрос
            redis.zadd(key, {str(current_time): current_time})
            redis.expire(key, self.window_seconds)

            return True

        except Exception as e:
            # В случае ошибки Redis разрешаем запрос
            return True
