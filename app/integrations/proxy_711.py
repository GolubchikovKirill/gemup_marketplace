"""
Интеграция с 711 Proxy API.

Обеспечивает покупку прокси, получение статуса и управление заказами
через API провайдера 711proxy. Оптимизировано для MVP.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from app.core.config import settings
from .base import BaseIntegration, IntegrationError

logger = logging.getLogger(__name__)


class Proxy711API(BaseIntegration):
    """
    API клиент для 711 Proxy - полная реализация для MVP.

    Обеспечивает:
    - Покупку прокси
    - Получение списка прокси
    - Проверку статуса заказов
    - Получение доступных продуктов
    """

    def __init__(self):
        super().__init__("711proxy")
        self._validate_configuration()

    @property
    def base_url(self) -> str:
        """Базовый URL 711 Proxy API."""
        return getattr(settings, 'proxy_711_base_url', "https://service.711proxy.com/api")

    @property
    def api_key(self) -> str:
        """API ключ 711 Proxy."""
        return getattr(settings, 'proxy_711_api_key', "")

    @property
    def username(self) -> str:
        """Username для 711 Proxy."""
        return getattr(settings, 'proxy_711_username', "")

    @property
    def password(self) -> str:
        """Password для 711 Proxy."""
        return getattr(settings, 'proxy_711_password', "")

    def _validate_configuration(self):
        """Валидация конфигурации 711 Proxy."""
        missing_configs = []

        if not self.api_key:
            missing_configs.append("proxy_711_api_key")
        if not self.username:
            missing_configs.append("proxy_711_username")
        if not self.password:
            missing_configs.append("proxy_711_password")

        if missing_configs:
            self.logger.warning(f"Missing 711Proxy configuration: {', '.join(missing_configs)}")

    def _get_auth_headers(self) -> Dict[str, str]:
        """Получение заголовков аутентификации."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "X-Username": self.username,
            "X-Password": self.password
        }

    async def purchase_proxies(
        self,
        product_id: int,
        quantity: int,
        duration_days: int = 30,
        country: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Покупка прокси у 711 провайдера - РЕАЛЬНАЯ РЕАЛИЗАЦИЯ для MVP.

        Args:
            product_id: ID продукта
            quantity: Количество прокси
            duration_days: Длительность в днях
            country: Код страны
            **kwargs: Дополнительные параметры

        Returns:
            Dict[str, Any]: Данные купленных прокси

        Raises:
            IntegrationError: При ошибках покупки
        """
        try:
            self.logger.info(f"Purchasing {quantity} proxies for product {product_id} from 711Proxy")

            if not self.api_key:
                raise IntegrationError("711Proxy API key not configured", provider="711proxy")

            # Валидация входных данных
            if quantity <= 0:
                raise IntegrationError("Quantity must be positive", provider="711proxy")

            if duration_days <= 0:
                raise IntegrationError("Duration must be positive", provider="711proxy")

            # Подготовка данных запроса
            payload = {
                "product_id": product_id,
                "quantity": quantity,
                "duration_days": duration_days,
                "format": kwargs.get("format", "ip:port:user:pass")
            }

            if country:
                payload["country"] = country.upper()

            # Дополнительные параметры
            optional_params = ["region", "isp", "protocol", "auth_type"]
            for param in optional_params:
                if param in kwargs:
                    payload[param] = kwargs[param]

            headers = self._get_auth_headers()

            # РЕАЛЬНЫЙ запрос к API
            result = await self.make_request("POST", "/purchase", data=payload, headers=headers)

            # Проверяем успешность
            if not result.get("success", True):
                error_msg = result.get("message", "Unknown error")
                raise IntegrationError(f"711Proxy purchase failed: {error_msg}", provider="711proxy")

            # Нормализуем ответ для нашей системы
            proxy_list = result.get("proxies", result.get("proxy_list", ""))
            if isinstance(proxy_list, list):
                proxy_list = "\n".join(str(proxy) for proxy in proxy_list)

            normalized_result = {
                "proxy_list": proxy_list,
                "username": result.get("username", result.get("auth", {}).get("username", "")),
                "password": result.get("password", result.get("auth", {}).get("password", "")),
                "provider_order_id": result.get("order_id", result.get("provider_order_id", f"711_{product_id}_{quantity}")),
                "expires_at": self._parse_expiry_date(result.get("expires_at", result.get("expiry_date"))),
                "status": result.get("status", "active"),
                "provider": "711proxy",
                "provider_metadata": {
                    "product_id": product_id,
                    "quantity": quantity,
                    "duration_days": duration_days,
                    "country": country,
                    "original_response": result
                }
            }

            self.log_operation("purchase_proxies", {
                "product_id": product_id,
                "quantity": quantity,
                "provider_order_id": normalized_result["provider_order_id"]
            })

            return normalized_result

        except IntegrationError:
            raise
        except Exception as e:
            self.logger.error(f"Error purchasing proxies from 711Proxy: {e}")
            raise IntegrationError(f"Purchase failed: {str(e)}", provider="711proxy")

    async def get_available_products(self) -> List[Dict[str, Any]]:
        """
        Получение списка доступных продуктов - РЕАЛЬНАЯ РЕАЛИЗАЦИЯ.

        Returns:
            List[Dict[str, Any]]: Список доступных продуктов

        Raises:
            IntegrationError: При ошибках получения продуктов
        """
        try:
            if not self.api_key:
                raise IntegrationError("711Proxy API key not configured", provider="711proxy")

            headers = self._get_auth_headers()
            result = await self.make_request("GET", "/products", headers=headers)

            if not result.get("success", True):
                raise IntegrationError(f"711Proxy API error: {result.get('message', 'Unknown error')}", provider="711proxy")

            products = result.get("data", result.get("products", []))

            self.log_operation("get_available_products", {
                "products_count": len(products)
            })

            return products

        except IntegrationError:
            raise
        except Exception as e:
            self.logger.error(f"Error getting available products from 711Proxy: {e}")
            raise IntegrationError(f"Failed to get products: {str(e)}", provider="711proxy")

    async def get_proxy_list(self, order_id: str) -> Dict[str, Any]:
        """
        Получение списка прокси по ID заказа - РЕАЛЬНАЯ РЕАЛИЗАЦИЯ.

        Args:
            order_id: ID заказа у провайдера

        Returns:
            Dict[str, Any]: Данные прокси

        Raises:
            IntegrationError: При ошибках получения списка
        """
        try:
            if not order_id:
                raise IntegrationError("Order ID is required", provider="711proxy")

            headers = self._get_auth_headers()
            result = await self.make_request("GET", f"/orders/{order_id}/proxies", headers=headers)

            if not result.get("success", True):
                error_msg = result.get("message", "Order not found")
                raise IntegrationError(f"711Proxy API error: {error_msg}", provider="711proxy")

            proxy_data = result.get("data", {})

            self.log_operation("get_proxy_list", {
                "order_id": order_id,
                "proxies_count": len(proxy_data.get("proxies", []))
            })

            return {
                "proxies": proxy_data.get("proxies", []),
                "username": proxy_data.get("username", ""),
                "password": proxy_data.get("password", ""),
                "expires_at": proxy_data.get("expires_at", ""),
                "status": proxy_data.get("status", "active")
            }

        except IntegrationError:
            raise
        except Exception as e:
            self.logger.error(f"Error getting proxy list for order {order_id}: {e}")
            raise IntegrationError(f"Failed to get proxy list: {str(e)}", provider="711proxy")

    async def get_proxy_status(self, order_id: str) -> Dict[str, Any]:
        """
        Получение статуса заказа прокси - РЕАЛЬНАЯ РЕАЛИЗАЦИЯ для MVP.

        Args:
            order_id: ID заказа у провайдера

        Returns:
            Dict[str, Any]: Статус заказа

        Raises:
            IntegrationError: При ошибках получения статуса
        """
        try:
            if not order_id:
                raise IntegrationError("Order ID is required", provider="711proxy")

            headers = self._get_auth_headers()
            result = await self.make_request("GET", f"/orders/{order_id}/status", headers=headers)

            if not result.get("success", True):
                error_msg = result.get("message", "Order not found")
                raise IntegrationError(f"711Proxy API error: {error_msg}", provider="711proxy")

            status_data = result.get("data", {})

            self.log_operation("get_proxy_status", {
                "order_id": order_id,
                "status": status_data.get("status", "unknown")
            })

            return {
                "order_id": order_id,
                "status": status_data.get("status", "unknown"),
                "expires_at": status_data.get("expires_at", ""),
                "traffic_used": status_data.get("traffic_used", "0.00 GB"),
                "traffic_limit": status_data.get("traffic_limit", "unlimited"),
                "proxies_count": status_data.get("proxies_count", 0),
                "last_updated": status_data.get("last_updated", datetime.now().isoformat())
            }

        except IntegrationError:
            raise
        except Exception as e:
            self.logger.error(f"Error getting status for order {order_id}: {e}")
            raise IntegrationError(f"Failed to get order status: {str(e)}", provider="711proxy")

    async def test_connection(self) -> bool:
        """
        Тестирование подключения к API.

        Returns:
            bool: True если подключение успешно
        """
        try:
            if not self.api_key:
                self.logger.warning("711Proxy API key not configured")
                return False

            headers = self._get_auth_headers()

            # Пытаемся получить список продуктов как тест
            try:
                result = await self.make_request("GET", "/health", headers=headers, timeout=10.0)

                if result.get("success", True):
                    self.logger.info("711Proxy API connection successful")
                    return True
                else:
                    self.logger.warning(f"711Proxy API health check failed: {result}")
                    return False

            except IntegrationError:
                # Если /health не существует, пробуем /products
                try:
                    await self.get_available_products()
                    self.logger.info("711Proxy API connection successful (via products)")
                    return True
                except Exception:
                    return False

        except Exception as e:
            self.logger.error(f"711Proxy connection test failed: {e}")
            return False

    def _parse_expiry_date(self, expiry_input: Any) -> Optional[str]:
        """
        Парсинг даты истечения от провайдера.

        Args:
            expiry_input: Дата в различных форматах

        Returns:
            Optional[str]: ISO дата или None
        """
        if not expiry_input:
            return None

        try:
            if isinstance(expiry_input, str):
                if "T" in expiry_input:  # ISO format
                    return expiry_input

                # Пытаемся парсить различные форматы
                try:
                    # Пробуем импортировать dateutil если доступен
                    try:
                        from dateutil import parser
                        parsed_date = parser.parse(expiry_input)
                        return parsed_date.isoformat()
                    except ImportError:
                        # Fallback если dateutil не установлен
                        from datetime import datetime
                        # Простой парсинг для основных форматов
                        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y']:
                            try:
                                parsed_date = datetime.strptime(expiry_input, fmt)
                                return parsed_date.isoformat()
                            except ValueError:
                                continue
                        return None

                except Exception:
                    return None

            elif isinstance(expiry_input, (int, float)):
                from datetime import datetime
                return datetime.fromtimestamp(expiry_input).isoformat()

            return None

        except Exception as e:
            self.logger.warning(f"Failed to parse expiry date '{expiry_input}': {e}")
            return None

    async def extend_proxy_order(
        self,
        order_id: str,
        extend_days: int
    ) -> Dict[str, Any]:
        """
        Продление заказа прокси - для продления услуг.

        Args:
            order_id: ID заказа
            extend_days: Количество дней для продления

        Returns:
            Dict[str, Any]: Результат продления

        Raises:
            IntegrationError: При ошибках продления
        """
        try:
            if not order_id:
                raise IntegrationError("Order ID is required", provider="711proxy")

            if extend_days <= 0:
                raise IntegrationError("Extension days must be positive", provider="711proxy")

            headers = self._get_auth_headers()
            payload = {
                "order_id": order_id,
                "extend_days": extend_days
            }

            result = await self.make_request("POST", f"/orders/{order_id}/extend", data=payload, headers=headers)

            if not result.get("success", True):
                error_msg = result.get("message", "Extension failed")
                raise IntegrationError(f"711Proxy extension error: {error_msg}", provider="711proxy")

            extension_data = result.get("data", {})

            self.log_operation("extend_proxy_order", {
                "order_id": order_id,
                "extend_days": extend_days,
                "new_expires_at": extension_data.get("expires_at")
            })

            return {
                "order_id": order_id,
                "extended_days": extend_days,
                "new_expires_at": extension_data.get("expires_at"),
                "status": extension_data.get("status", "extended"),
                "cost": extension_data.get("cost", "0.00")
            }

        except IntegrationError:
            raise
        except Exception as e:
            self.logger.error(f"Error extending proxy order {order_id}: {e}")
            raise IntegrationError(f"Failed to extend order: {str(e)}", provider="711proxy")

    async def get_account_balance(self) -> Dict[str, Any]:
        """
        Получение баланса аккаунта у провайдера.

        Returns:
            Dict[str, Any]: Информация о балансе

        Raises:
            IntegrationError: При ошибках получения баланса
        """
        try:
            headers = self._get_auth_headers()
            result = await self.make_request("GET", "/account/balance", headers=headers)

            if not result.get("success", True):
                error_msg = result.get("message", "Failed to get balance")
                raise IntegrationError(f"711Proxy balance error: {error_msg}", provider="711proxy")

            balance_data = result.get("data", {})

            self.log_operation("get_account_balance", {
                "balance": balance_data.get("balance", "0.00"),
                "currency": balance_data.get("currency", "USD")
            })

            return balance_data

        except IntegrationError:
            raise
        except Exception as e:
            self.logger.error(f"Error getting 711Proxy account balance: {e}")
            raise IntegrationError(f"Failed to get account balance: {str(e)}", provider="711proxy")


proxy_711_api = Proxy711API()
