"""
Circuit Breaker для защиты от каскадных сбоев.
"""

import time
from enum import Enum
from typing import Callable, Any


class CircuitState(Enum):
    CLOSED = "closed"  # Нормальная работа
    OPEN = "open"  # Защита активна
    HALF_OPEN = "half_open"  # Тестирование восстановления


class CircuitBreaker:
    """Circuit Breaker для защиты внешних сервисов."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Выполняет функцию с защитой Circuit Breaker.
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise ServiceUnavailableError("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result

        except Exception:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Проверяет можно ли попробовать сброс."""
        return (time.time() - self.last_failure_time) >= self.recovery_timeout

    def _on_success(self):
        """Обработка успешного вызова."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def _on_failure(self):
        """Обработка неудачного вызова."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN


class ServiceUnavailableError(Exception):
    """Ошибка недоступности сервиса."""
    pass
