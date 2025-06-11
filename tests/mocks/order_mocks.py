"""
Моки для OrderService - ТОЛЬКО для тестов
"""

from typing import Dict, Any, List
from decimal import Decimal
from datetime import datetime
import uuid


class MockOrderData:
    """Мок-данные для заказов"""

    @staticmethod
    def generate_mock_proxies(quantity: int) -> str:
        """Генерация мок-прокси для тестирования"""
        proxies = []
        for i in range(quantity):
            proxy = f"192.168.{i + 1}.{i + 1}:808{i}"
            proxies.append(proxy)
        return "\n".join(proxies)

    @staticmethod
    def generate_mock_proxy_purchase_data(quantity: int) -> Dict[str, Any]:
        """ИСПРАВЛЕНО: правильная структура для purchase_proxies_from_provider"""
        return {
            "proxy_list": MockOrderData.generate_mock_proxies(quantity),
            "username": f"test_user_{uuid.uuid4().hex[:8]}",
            "password": f"test_pass_{uuid.uuid4().hex[:8]}",
            "provider_order_id": f"mock_order_{uuid.uuid4().hex[:8]}"
        }

    @staticmethod
    def mock_activate_proxies_result() -> bool:
        """Мок результата активации прокси"""
        return True


class MockOrderService:
    """Мок OrderService для изоляции тестов"""

    def __init__(self):
        self.created_orders = []
        self.activated_orders = []

    async def create_order_from_cart_mock(self, user, cart_items: List) -> Dict[str, Any]:
        """Мок создания заказа"""
        order_data = {
            "id": len(self.created_orders) + 1,
            "order_number": f"ORD-MOCK-{uuid.uuid4().hex[:8].upper()}",
            "user_id": user.id,
            "total_amount": Decimal("10.00"),
            "status": "paid",
            "created_at": datetime.now()
        }
        self.created_orders.append(order_data)
        return order_data

    async def activate_proxies_for_order_mock(self, order_id: int) -> bool:
        """Мок активации прокси"""
        self.activated_orders.append(order_id)
        return True
