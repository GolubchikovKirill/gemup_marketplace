"""
Общие тестовые данные и фикстуры для моков
"""

from typing import Dict, Any
from decimal import Decimal
from datetime import datetime, timedelta


def get_mock_proxy_product() -> Dict[str, Any]:
    """Мок данные продукта прокси"""
    return {
        "id": 1,
        "name": "Mock Datacenter Proxy",
        "proxy_type": "http",
        "proxy_category": "datacenter",
        "session_type": "sticky",
        "provider": "provider_711",
        "country_code": "US",
        "country_name": "United States",
        "price_per_proxy": Decimal("2.00"),
        "duration_days": 30,
        "min_quantity": 1,
        "max_quantity": 100,
        "stock_available": 50,
        "is_active": True
    }


def get_mock_user() -> Dict[str, Any]:
    """Мок данные пользователя"""
    return {
        "id": 1,
        "email": "test@example.com",
        "username": "testuser",
        "first_name": "Test",
        "last_name": "User",
        "balance": Decimal("100.00"),
        "is_guest": False,
        "is_active": True,
        "created_at": datetime.now()
    }


def get_mock_order() -> Dict[str, Any]:
    """Мок данные заказа"""
    return {
        "id": 1,
        "order_number": "ORD-20241201-ABCD1234",
        "user_id": 1,
        "total_amount": Decimal("10.00"),
        "currency": "USD",
        "status": "paid",
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }


def get_mock_proxy_purchase() -> Dict[str, Any]:
    """Мок данные покупки прокси"""
    return {
        "id": 1,
        "user_id": 1,
        "proxy_product_id": 1,
        "order_id": 1,
        "proxy_list": "192.168.1.1:8080\n192.168.1.2:8080",
        "username": "mock_user",
        "password": "mock_pass",
        "is_active": True,
        "expires_at": datetime.now() + timedelta(days=30),
        "traffic_used_gb": Decimal("0.00"),
        "created_at": datetime.now()
    }
