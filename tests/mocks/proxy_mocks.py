"""
Моки для ProxyService и внешних API - ТОЛЬКО для тестов
"""

from typing import Dict, Any, List
import uuid
from datetime import datetime, timedelta


class MockProxyData:
    """Мок-данные для прокси"""

    @staticmethod
    def format_proxy_line_mock(proxy_line: str, format_type: str) -> str:
        """Мок форматирования строки прокси"""
        if format_type == "ip:port:user:pass":
            if ":" in proxy_line and len(proxy_line.split(":")) == 2:
                return f"{proxy_line}:testuser:testpass"
            return proxy_line
        elif format_type == "user:pass@ip:port":
            if ":" in proxy_line and len(proxy_line.split(":")) == 2:
                return f"testuser:testpass@{proxy_line}"
            return proxy_line
        else:
            return proxy_line

    @staticmethod
    def generate_mock_proxy_list(quantity: int, format_type: str = "ip:port") -> List[str]:
        """Генерация списка мок-прокси"""
        proxies = []
        for i in range(quantity):
            base_proxy = f"192.168.{i + 1}.{i + 1}:808{i}"
            formatted_proxy = MockProxyData.format_proxy_line_mock(base_proxy, format_type)
            proxies.append(formatted_proxy)
        return proxies


class MockProxy711API:
    """Мок для 711 Proxy API"""

    def __init__(self):
        self.orders = {}
        self.proxies = {}

    async def purchase_proxies(
        self,
        product_id: int,
        quantity: int,
        **kwargs
    ) -> Dict[str, Any]:
        """Мок покупки прокси"""
        order_id = f"mock-711-{uuid.uuid4().hex[:8]}"

        # Генерируем мок прокси
        proxies = []
        for i in range(quantity):
            proxy = f"192.168.{i+1}.{i+1}:808{i}"
            proxies.append(proxy)

        result = {
            "proxy_list": "\n".join(proxies),
            "username": f"user_{order_id}",
            "password": f"pass_{order_id}",
            "provider_order_id": order_id,
            "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
            "status": "active"
        }

        self.orders[order_id] = result
        return result


class MockCryptomusAPI:
    """Мок для Cryptomus Payment API"""

    def __init__(self):
        self.payments = {}
        self.webhook_secret = "test-webhook-secret"
        self.api_key = "test-api-key"
        self.merchant_id = "test-merchant"

    async def create_payment(
        self,
        amount,
        currency: str = "USD",
        order_id: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Мок создания платежа"""
        if not order_id:
            order_id = f"payment_{uuid.uuid4().hex[:16]}"

        payment_uuid = f"mock-uuid-{uuid.uuid4().hex[:8]}"
        payment_url = f"https://mock-cryptomus.com/pay/{payment_uuid}"

        payment_data = {
            "state": 0,
            "result": {
                "uuid": payment_uuid,
                "url": payment_url,
                "order_id": order_id,
                "amount": str(amount),
                "currency": currency,
                "status": "pending",
                "created_at": datetime.now().isoformat()
            }
        }

        self.payments[payment_uuid] = payment_data["result"]
        return payment_data
