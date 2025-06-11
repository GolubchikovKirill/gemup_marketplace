"""
Базовый класс для интеграций с внешними сервисами.

Предоставляет общую функциональность для всех интеграций:
HTTP клиент, логирование, обработка ошибок.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

import aiohttp

logger = logging.getLogger(__name__)


class IntegrationError(Exception):
    """Исключение для ошибок интеграций."""

    def __init__(self, message: str, provider: str = "", error_code: str = "", status_code: Optional[int] = None):
        self.message = message
        self.provider = provider
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(self.message)


class BaseIntegration(ABC):
    """
    Базовый класс для всех интеграций с внешними сервисами.

    Предоставляет общую функциональность:
    - HTTP клиент с retry логикой
    - Логирование операций
    - Обработка ошибок
    - Валидация конфигурации
    """

    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.logger = logging.getLogger(f"integrations.{provider_name}")
        self._session: Optional[aiohttp.ClientSession] = None
        self.timeout = aiohttp.ClientTimeout(total=30)
        self.max_retries = 3
        self.retry_delay = 1.0

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Базовый URL API."""
        pass

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _ensure_session(self):
        """Создание HTTP сессии если её нет."""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=30,
                ttl_dns_cache=300,
                use_dns_cache=True,
            )
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=self.timeout,
                headers={
                    "User-Agent": f"ProxyService/{self.provider_name}",
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
            )

    async def close(self):
        """Закрытие HTTP сессии."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        retries: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Выполнение HTTP запроса с retry логикой.

        Args:
            method: HTTP метод
            endpoint: Endpoint API
            data: Данные запроса
            headers: Дополнительные заголовки
            timeout: Таймаут запроса
            retries: Количество повторов

        Returns:
            Dict[str, Any]: Ответ API

        Raises:
            IntegrationError: При ошибках запроса
        """
        await self._ensure_session()

        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        retries = retries or self.max_retries

        request_headers = {}
        if headers:
            request_headers.update(headers)

        for attempt in range(retries + 1):
            try:
                start_time = time.time()

                async with self._session.request(
                    method=method.upper(),
                    url=url,
                    json=data if data else None,
                    headers=request_headers,
                    timeout=aiohttp.ClientTimeout(total=timeout or 30)
                ) as response:

                    duration = time.time() - start_time

                    # Логируем запрос
                    self.logger.debug(
                        f"{method.upper()} {url} -> {response.status} ({duration:.3f}s)"
                    )

                    response_text = await response.text()

                    # Обработка успешных ответов
                    if 200 <= response.status < 300:
                        try:
                            return await response.json()
                        except Exception:
                            # Если не JSON, возвращаем как текст
                            return {"data": response_text, "status": "success"}

                    # Обработка ошибок
                    error_data = {}
                    try:
                        error_data = await response.json() if response_text else {}
                    except Exception:
                        error_data = {"message": response_text}

                    error_message = error_data.get("message", f"HTTP {response.status}")
                    error_code = error_data.get("error_code", str(response.status))

                    # Проверяем нужно ли повторить запрос
                    if attempt < retries and self._should_retry(response.status):
                        delay = self.retry_delay * (2 ** attempt)
                        self.logger.warning(
                            f"Request failed (attempt {attempt + 1}/{retries + 1}), "
                            f"retrying in {delay}s: {error_message}"
                        )
                        await asyncio.sleep(delay)
                        continue

                    # Финальная ошибка
                    raise IntegrationError(
                        message=error_message,
                        provider=self.provider_name,
                        error_code=error_code,
                        status_code=response.status
                    )

            except aiohttp.ClientError as e:
                if attempt < retries:
                    delay = self.retry_delay * (2 ** attempt)
                    self.logger.warning(
                        f"Network error (attempt {attempt + 1}/{retries + 1}), "
                        f"retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                    continue

                raise IntegrationError(
                    message=f"Network error: {str(e)}",
                    provider=self.provider_name,
                    error_code="NETWORK_ERROR"
                )

            except Exception as e:
                self.logger.error(f"Unexpected error in request: {e}")
                raise IntegrationError(
                    message=f"Request failed: {str(e)}",
                    provider=self.provider_name,
                    error_code="UNKNOWN_ERROR"
                )
        return None

    def _should_retry(self, status_code: int) -> bool:
        """
        Определяет нужно ли повторить запрос для данного статуса.

        Args:
            status_code: HTTP статус код

        Returns:
            bool: True если нужно повторить
        """
        # Повторяем для серверных ошибок и rate limiting
        return status_code in [429, 500, 502, 503, 504]

    def log_operation(self, operation: str, data: Dict[str, Any]):
        """
        Логирование операции интеграции.

        Args:
            operation: Название операции
            data: Данные операции
        """
        self.logger.info(
            f"Operation: {operation}",
            extra={
                "provider": self.provider_name,
                "operation": operation,
                **data
            }
        )

    # Абстрактные методы для покупки прокси
    @abstractmethod
    async def purchase_proxies(
        self,
        product_id: int,
        quantity: int,
        duration_days: int = 30,
        country: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Покупка прокси у провайдера.

        Args:
            product_id: ID продукта
            quantity: Количество
            duration_days: Длительность в днях
            country: Код страны
            **kwargs: Дополнительные параметры

        Returns:
            Dict[str, Any]: Данные купленных прокси
        """
        pass

    @abstractmethod
    async def get_proxy_status(self, order_id: str) -> Dict[str, Any]:
        """
        Получение статуса заказа прокси.

        Args:
            order_id: ID заказа у провайдера

        Returns:
            Dict[str, Any]: Статус заказа
        """
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Тестирование подключения к API.

        Returns:
            bool: True если подключение успешно
        """
        pass
