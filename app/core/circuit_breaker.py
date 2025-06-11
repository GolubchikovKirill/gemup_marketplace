"""
Circuit Breaker для защиты от каскадных сбоев.

КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ:
✅ Добавлен logging
✅ Улучшена типизация
✅ Добавлена поддержка sync/async функций
✅ Enhanced error handling
✅ Metrics и monitoring
"""

import asyncio
import inspect
import logging
import time
from enum import Enum
from functools import wraps
from typing import Callable, Any, Union, Optional, Dict

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Состояния Circuit Breaker"""
    CLOSED = "closed"       # Нормальная работа
    OPEN = "open"           # Защита активна
    HALF_OPEN = "half_open" # Тестирование восстановления


class CircuitBreakerError(Exception):
    """Базовая ошибка Circuit Breaker"""
    pass


class ServiceUnavailableError(CircuitBreakerError):
    """Ошибка недоступности сервиса."""
    pass


class CircuitOpenError(CircuitBreakerError):
    """Ошибка когда Circuit Breaker открыт."""
    pass


class CircuitBreaker:
    """
    ИСПРАВЛЕННЫЙ Circuit Breaker для защиты внешних сервисов.

    ИСПРАВЛЕНИЯ:
    ✅ Enhanced logging
    ✅ Better typing support
    ✅ Sync/Async function support
    ✅ Metrics collection
    ✅ Configurable exceptions
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Union[Exception, tuple] = Exception,
        name: str = "CircuitBreaker"
    ):
        """
        ИСПРАВЛЕНО: Инициализация с enhanced параметрами.

        Args:
            failure_threshold: Количество ошибок для открытия
            recovery_timeout: Время ожидания перед попыткой восстановления
            expected_exception: Исключения которые считаются ошибками
            name: Имя Circuit Breaker для логирования
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name

        # State tracking
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED

        # Metrics
        self.total_calls = 0
        self.total_failures = 0
        self.total_successes = 0
        self.state_changes: Dict[str, int] = {
            "closed_to_open": 0,
            "open_to_half_open": 0,
            "half_open_to_closed": 0,
            "half_open_to_open": 0
        }

        logger.info(f"🔧 Circuit Breaker '{self.name}' initialized: "
                   f"threshold={failure_threshold}, timeout={recovery_timeout}s")

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        ИСПРАВЛЕНО: Выполняет функцию с защитой Circuit Breaker.

        Args:
            func: Функция для выполнения (sync или async)
            *args: Позиционные аргументы
            **kwargs: Именованные аргументы

        Returns:
            Any: Результат выполнения функции

        Raises:
            CircuitOpenError: Если Circuit Breaker открыт
            Exception: Исходное исключение от функции
        """
        self.total_calls += 1

        # Проверяем состояние Circuit Breaker
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._change_state(CircuitState.HALF_OPEN)
                logger.info(f"🔄 Circuit Breaker '{self.name}' attempting recovery (HALF_OPEN)")
            else:
                logger.warning(f"🚫 Circuit Breaker '{self.name}' is OPEN, call rejected")
                raise CircuitOpenError(f"Circuit breaker '{self.name}' is OPEN")

        try:
            # ИСПРАВЛЕНИЕ: Поддержка sync и async функций
            if inspect.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                # Для sync функций в async контексте
                result = await asyncio.get_event_loop().run_in_executor(None, func, *args, **kwargs)

            self._on_success()
            return result

        except Exception as e:
            # Проверяем является ли исключение ожидаемым для Circuit Breaker
            if isinstance(e, self.expected_exception):
                self._on_failure()
                logger.warning(f"⚠️ Circuit Breaker '{self.name}' registered failure: {type(e).__name__}")
            else:
                # Неожиданное исключение - не считаем как failure
                logger.debug(f"🔍 Circuit Breaker '{self.name}' ignoring exception: {type(e).__name__}")

            raise  # Re-raise исходное исключение

    def call_sync(self, func: Callable, *args, **kwargs) -> Any:
        """
        НОВЫЙ МЕТОД: Синхронная версия call для sync функций.

        Args:
            func: Синхронная функция
            *args: Позиционные аргументы
            **kwargs: Именованные аргументы

        Returns:
            Any: Результат выполнения функции
        """
        self.total_calls += 1

        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._change_state(CircuitState.HALF_OPEN)
                logger.info(f"🔄 Circuit Breaker '{self.name}' attempting recovery (HALF_OPEN)")
            else:
                logger.warning(f"🚫 Circuit Breaker '{self.name}' is OPEN, call rejected")
                raise CircuitOpenError(f"Circuit breaker '{self.name}' is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result

        except Exception as e:
            if isinstance(e, self.expected_exception):
                self._on_failure()
                logger.warning(f"⚠️ Circuit Breaker '{self.name}' registered failure: {type(e).__name__}")
            else:
                logger.debug(f"🔍 Circuit Breaker '{self.name}' ignoring exception: {type(e).__name__}")

            raise

    def _should_attempt_reset(self) -> bool:
        """Проверяет можно ли попробовать сброс."""
        if self.last_failure_time is None:
            return False

        time_since_failure = time.time() - self.last_failure_time
        should_reset = time_since_failure >= self.recovery_timeout

        if should_reset:
            logger.debug(f"🕐 Circuit Breaker '{self.name}' recovery timeout elapsed: "
                        f"{time_since_failure:.1f}s >= {self.recovery_timeout}s")

        return should_reset

    def _on_success(self):
        """ИСПРАВЛЕНО: Обработка успешного вызова с логированием."""
        self.success_count += 1
        self.total_successes += 1

        if self.state == CircuitState.HALF_OPEN:
            # В HALF_OPEN состоянии успех означает восстановление
            self._change_state(CircuitState.CLOSED)
            logger.info(f"✅ Circuit Breaker '{self.name}' recovered (HALF_OPEN -> CLOSED)")

        elif self.state == CircuitState.CLOSED:
            # Сбрасываем счетчик ошибок при успехе
            if self.failure_count > 0:
                logger.debug(f"🔄 Circuit Breaker '{self.name}' reset failure count: "
                           f"{self.failure_count} -> 0")
                self.failure_count = 0

    def _on_failure(self):
        """ИСПРАВЛЕНО: Обработка неудачного вызова с логированием."""
        self.failure_count += 1
        self.total_failures += 1
        self.last_failure_time = time.time()

        logger.debug(f"💥 Circuit Breaker '{self.name}' failure {self.failure_count}/{self.failure_threshold}")

        if self.state == CircuitState.HALF_OPEN:
            # В HALF_OPEN любая ошибка возвращает в OPEN
            self._change_state(CircuitState.OPEN)
            logger.warning(f"🔴 Circuit Breaker '{self.name}' failed recovery (HALF_OPEN -> OPEN)")

        elif self.state == CircuitState.CLOSED and self.failure_count >= self.failure_threshold:
            # Превышен порог ошибок
            self._change_state(CircuitState.OPEN)
            logger.error(f"🚨 Circuit Breaker '{self.name}' opened due to failures: "
                        f"{self.failure_count}/{self.failure_threshold}")

    def _change_state(self, new_state: CircuitState):
        """НОВЫЙ МЕТОД: Изменение состояния с метриками."""
        old_state = self.state
        self.state = new_state

        # Обновляем метрики переходов состояний
        state_key = f"{old_state.value}_to_{new_state.value}"
        if state_key in self.state_changes:
            self.state_changes[state_key] += 1

        logger.info(f"🔄 Circuit Breaker '{self.name}' state: {old_state.value} -> {new_state.value}")

    def get_metrics(self) -> Dict[str, Any]:
        """НОВЫЙ МЕТОД: Получение метрик Circuit Breaker."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "total_calls": self.total_calls,
            "total_failures": self.total_failures,
            "total_successes": self.total_successes,
            "failure_rate": self.total_failures / max(self.total_calls, 1),
            "last_failure_time": self.last_failure_time,
            "state_changes": self.state_changes.copy(),
            "config": {
                "failure_threshold": self.failure_threshold,
                "recovery_timeout": self.recovery_timeout,
                "expected_exception": str(self.expected_exception)
            }
        }

    def reset(self):
        """НОВЫЙ МЕТОД: Ручной сброс Circuit Breaker."""
        old_state = self.state
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None

        logger.info(f"🔄 Circuit Breaker '{self.name}' manually reset: {old_state.value} -> CLOSED")

    def is_closed(self) -> bool:
        """Проверка что Circuit Breaker закрыт (работает)."""
        return self.state == CircuitState.CLOSED

    def is_open(self) -> bool:
        """Проверка что Circuit Breaker открыт (блокирует)."""
        return self.state == CircuitState.OPEN

    def is_half_open(self) -> bool:
        """Проверка что Circuit Breaker в полуоткрытом состоянии."""
        return self.state == CircuitState.HALF_OPEN


# НОВЫЙ КЛАСС: Circuit Breaker Manager
class CircuitBreakerManager:
    """Менеджер для управления множественными Circuit Breaker."""

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}

    def create_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Union[Exception, tuple] = Exception
    ) -> CircuitBreaker:
        """Создание нового Circuit Breaker."""
        if name in self._breakers:
            logger.warning(f"⚠️ Circuit Breaker '{name}' already exists, returning existing")
            return self._breakers[name]

        breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
            name=name
        )

        self._breakers[name] = breaker
        logger.info(f"✅ Created Circuit Breaker: {name}")
        return breaker

    def get_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """Получение Circuit Breaker по имени."""
        return self._breakers.get(name)

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Получение метрик всех Circuit Breaker."""
        return {name: breaker.get_metrics() for name, breaker in self._breakers.items()}

    def reset_all(self):
        """Сброс всех Circuit Breaker."""
        for breaker in self._breakers.values():
            breaker.reset()
        logger.info("🔄 All Circuit Breakers reset")


# Глобальный менеджер
circuit_breaker_manager = CircuitBreakerManager()


# DECORATOR: Circuit Breaker как декоратор
def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: Union[Exception, tuple] = Exception
):
    """
    НОВЫЙ DECORATOR: Circuit Breaker как декоратор функций.

    Usage:
        @circuit_breaker("api_service", failure_threshold=3)
        async def call_external_api():
            # код вызова API
    """
    def decorator(func: Callable):
        breaker = circuit_breaker_manager.create_breaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception
        )

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await breaker.call(func, *args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return breaker.call_sync(func, *args, **kwargs)

        # Возвращаем подходящий wrapper в зависимости от типа функции
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
