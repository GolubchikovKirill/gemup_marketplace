"""
Базовые классы для интеграций с внешними сервисами.

Определяет общий интерфейс и функциональность для всех интеграций.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)


class IntegrationError(Exception):
    """Базовое исключение для ошибок интеграций."""

    def __init__(self, message: str, provider: str = None, error_code: str = None):
        self.message = message
        self.provider = provider
        self.error_code = error_code
        super().__init__(self.message)


class BaseIntegration(ABC):
    """
    Базовый класс для всех интеграций.

    Определяет общий интерфейс и предоставляет базовую функциональность
    для работы с внешними API.
    """

    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.logger = logging.getLogger(f"{__name__}.{provider_name}")
        self.timeout = 30.0
        self.max_retries = 3

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Базовый URL API."""
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Тестирование подключения к API.

        Returns:
            bool: True если подключение успешно
        """
        pass

    async def make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Выполнение HTTP запроса к API.

        Args:
            method: HTTP метод (GET, POST, PUT, DELETE)
            endpoint: Endpoint API
            data: Данные для отправки
            headers: HTTP заголовки
            timeout: Таймаут запроса

        Returns:
            Dict[str, Any]: Ответ API

        Raises:
            IntegrationError: При ошибках API или сети
        """
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        timeout = timeout or self.timeout

        request_headers = {
            "User-Agent": f"Gemup-Marketplace/1.0 ({self.provider_name})",
            "Content-Type": "application/json"
        }

        if headers:
            request_headers.update(headers)

        for attempt in range(self.max_retries):
            try:
                self.logger.debug(f"Making {method} request to {url} (attempt {attempt + 1})")

                async with httpx.AsyncClient() as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        json=data if method in ["POST", "PUT", "PATCH"] else None,
                        params=data if method == "GET" else None,
                        headers=request_headers,
                        timeout=timeout
                    )

                    # Логируем ответ
                    self.logger.debug(f"Response status: {response.status_code}")

                    # Проверяем статус ответа
                    if response.status_code >= 400:
                        error_text = response.text
                        self.logger.error(f"{self.provider_name} API error: {response.status_code} - {error_text}")
                        raise IntegrationError(
                            f"{self.provider_name} API returned {response.status_code}: {error_text}",
                            provider=self.provider_name,
                            error_code=str(response.status_code)
                        )

                    # Парсим JSON ответ
                    try:
                        result = response.json()
                        self.logger.debug(f"Successful response from {self.provider_name}")
                        return result
                    except ValueError as e:
                        self.logger.error(f"Invalid JSON response from {self.provider_name}: {e}")
                        raise IntegrationError(
                            f"{self.provider_name} returned invalid JSON response",
                            provider=self.provider_name
                        )

            except httpx.TimeoutException:
                self.logger.warning(f"{self.provider_name} API timeout (attempt {attempt + 1})")
                if attempt == self.max_retries - 1:
                    raise IntegrationError(
                        f"{self.provider_name} API timeout after {self.max_retries} attempts",
                        provider=self.provider_name
                    )
                continue

            except httpx.HTTPError as e:
                self.logger.error(f"{self.provider_name} HTTP error: {e}")
                if attempt == self.max_retries - 1:
                    raise IntegrationError(
                        f"{self.provider_name} connection error: {str(e)}",
                        provider=self.provider_name
                    )
                continue

            except IntegrationError:
                # Переброс наших ошибок без повторов
                raise

            except Exception as e:
                self.logger.error(f"Unexpected error with {self.provider_name}: {e}")
                if attempt == self.max_retries - 1:
                    raise IntegrationError(
                        f"Unexpected {self.provider_name} error: {str(e)}",
                        provider=self.provider_name
                    )
                continue
        return None

    def log_operation(self, operation: str, details: Dict[str, Any] = None):
        """
        Логирование операции интеграции.

        Args:
            operation: Название операции
            details: Дополнительные детали
        """
        log_data = {
            "provider": self.provider_name,
            "operation": operation,
            "timestamp": datetime.now().isoformat()
        }

        if details:
            log_data.update(details)

        self.logger.info(f"{self.provider_name} operation: {operation}", extra=log_data)
