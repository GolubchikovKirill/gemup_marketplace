"""
Моки для внешних API провайдеров прокси
Используются только в тестах
"""

from typing import Dict, Any
from datetime import datetime, timedelta
import uuid


class MockProxy711API:
    """Мок для 711 Proxy API"""

    def __init__(self):
        self.orders = {}
        self.proxies = {}

    async def purchase_proxies(
        self,
        product_id: int,
        quantity: int,
        country: str = "US",
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
            "order_id": order_id,
            "proxies": proxies,
            "username": f"user_{order_id}",
            "password": f"pass_{order_id}",
            "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
            "status": "active"
        }

        self.orders[order_id] = result
        return result

    async def extend_proxies(
        self,
        order_id: str,
        days: int,
        **kwargs
    ) -> Dict[str, Any]:
        """Мок продления прокси"""
        if order_id not in self.orders:
            return {
                "success": False,
                "error": "Order not found"
            }

        # Продлеваем срок действия
        current_expiry = datetime.fromisoformat(self.orders[order_id]["expires_at"])
        new_expiry = current_expiry + timedelta(days=days)

        self.orders[order_id]["expires_at"] = new_expiry.isoformat()

        return {
            "success": True,
            "extended_until": new_expiry.isoformat(),
            "message": f"Proxies extended by {days} days"
        }


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

    def _verify_webhook_signature(self, data: Dict[str, Any], signature: str) -> bool:
        """Мок проверки подписи webhook"""
        # В тестах всегда возвращаем True
        return True

    def _generate_webhook_sign(self, data: Dict[str, Any]) -> str:
        """Мок генерации подписи webhook"""
        return "mock-signature"
