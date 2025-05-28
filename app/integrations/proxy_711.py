import logging
import httpx
from typing import Dict, Any, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class Proxy711API:
    """Интеграция с 711 Proxy API"""

    def __init__(self):
        self.base_url = settings.provider_711_base_url
        self.api_key = settings.provider_711_api_key

    async def get_available_products(self) -> List[Dict[str, Any]]:
        """Получение доступных продуктов от 711 Proxy"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/products",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=30.0
                )
                response.raise_for_status()

                products = response.json()
                logger.info(f"Retrieved {len(products)} products from 711 Proxy")
                return products

        except Exception as e:
            logger.error(f"Error getting 711 Proxy products: {e}")
            return []

    async def purchase_proxies(
            self,
            product_id: str,
            quantity: int,
            duration_days: int,
            country_code: str,
            city: Optional[str] = None
    ) -> Dict[str, Any]:
        """Покупка прокси у 711 Proxy"""
        try:
            purchase_data = {
                "product_id": product_id,
                "quantity": quantity,
                "duration": duration_days,
                "country": country_code,
                "city": city,
                "format": "ip:port:user:pass"
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/purchase",
                    json=purchase_data,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=60.0
                )
                response.raise_for_status()

                result = response.json()
                logger.info(f"Successfully purchased {quantity} proxies from 711")
                return result

        except Exception as e:
            logger.error(f"Error purchasing proxies from 711: {e}")
            raise Exception(f"Failed to purchase proxies: {str(e)}")

    async def get_proxy_list(self, order_id: str) -> Dict[str, Any]:
        """Получение списка прокси по ID заказа"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/orders/{order_id}/proxies",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=30.0
                )
                response.raise_for_status()

                return response.json()

        except Exception as e:
            logger.error(f"Error getting proxy list from 711: {e}")
            raise Exception(f"Failed to get proxy list: {str(e)}")

    async def extend_proxies(self, order_id: str, days: int) -> Dict[str, Any]:
        """Продление прокси"""
        try:
            extend_data = {
                "order_id": order_id,
                "extend_days": days
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/extend",
                    json=extend_data,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=30.0
                )
                response.raise_for_status()

                return response.json()

        except Exception as e:
            logger.error(f"Error extending proxies: {e}")
            raise Exception(f"Failed to extend proxies: {str(e)}")


# Создаем экземпляр API
proxy_711_api = Proxy711API()
