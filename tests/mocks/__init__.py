"""
Модуль с моками для тестирования
Все моки должны находиться здесь, а не в основном коде приложения
"""

from .proxy_mocks import MockProxy711API, MockCryptomusAPI
from .service_mocks import MockOrderService, MockPaymentService

__all__ = [
    "MockProxy711API",
    "MockCryptomusAPI",
    "MockOrderService",
    "MockPaymentService"
]
