"""
Интеграция с 711 Proxy API.

Полная реализация без мок-данных, готовая к production.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from app.core.config import settings
from .base import BaseIntegration, IntegrationError

logger = logging.getLogger(__name__)


class Proxy711API(BaseIntegration):
    """API клиент для 711 Proxy - полная реализация."""

    def __init__(self):
        super().__init__("711proxy")
        self._validate_configuration()

    @property
    def base_url(self) -> str:
        """Базовый URL 711 Proxy API."""
        return settings.proxy_711_base_url or "https://service.711proxy.com/api"

    @property
    def api_key(self) -> str:
        """API ключ 711 Proxy."""
        return settings.proxy_711_api_key or ""

    @property
    def username(self) -> str:
        """Username для 711 Proxy."""
        return settings.proxy_711_username or ""

    @property
    def password(self) -> str:
        """Password для 711 Proxy."""
        return settings.proxy_711_password or ""

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
        Покупка прокси у 711 провайдера - РЕАЛЬНАЯ РЕАЛИЗАЦИЯ.
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

            # Нормализуем ответ
            normalized_result = {
                "proxy_list": result.get("proxies", result.get("proxy_list", "")),
                "username": result.get("username", result.get("auth", {}).get("username", "")),
                "password": result.get("password", result.get("auth", {}).get("password", "")),
                "provider_order_id": result.get("order_id", result.get("provider_order_id")),
                "expires_at": self._parse_expiry_date(result.get("expires_at", result.get("expiry_date"))),
                "status": result.get("status", "active"),
                "provider": "711proxy"
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
        """Получение списка доступных продуктов - РЕАЛЬНАЯ РЕАЛИЗАЦИЯ."""
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
        """Получение списка прокси по ID заказа - РЕАЛЬНАЯ РЕАЛИЗАЦИЯ."""
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
        """Получение статуса заказа прокси - РЕАЛЬНАЯ РЕАЛИЗАЦИЯ."""
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
        """Тестирование подключения к API."""
        try:
            if not self.api_key:
                self.logger.warning("711Proxy API key not configured")
                return False

            headers = self._get_auth_headers()
            result = await self.make_request("GET", "/health", headers=headers, timeout=10.0)

            if result.get("success", True):
                self.logger.info("711Proxy API connection successful")
                return True
            else:
                self.logger.warning(f"711Proxy API health check failed: {result}")
                return False

        except Exception as e:
            self.logger.error(f"711Proxy connection test failed: {e}")
            return False

    def _parse_expiry_date(self, expiry_input: Any) -> Optional[str]:
        """Парсинг даты истечения от провайдера."""
        if not expiry_input:
            return None

        try:
            if isinstance(expiry_input, str):
                if "T" in expiry_input:  # ISO format
                    return expiry_input
                from dateutil import parser
                parsed_date = parser.parse(expiry_input)
                return parsed_date.isoformat()
            elif isinstance(expiry_input, (int, float)):
                from datetime import datetime
                return datetime.fromtimestamp(expiry_input).isoformat()
            return None
        except Exception as e:
            self.logger.warning(f"Failed to parse expiry date '{expiry_input}': {e}")
            return None


proxy_711_api = Proxy711API()
