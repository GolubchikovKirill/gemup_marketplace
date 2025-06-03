"""
Централизованный доступ к мокам для тестов
"""

from .order_mocks import MockOrderData
from .proxy_mocks import MockProxyData, MockProxy711API, MockCryptomusAPI
from .payment_mocks import MockPaymentData

__all__ = [
    # Order mocks
    "MockOrderData",

    # Proxy mocks
    "MockProxyData",
    "MockProxy711API",
    "MockCryptomusAPI",

    # Payment mocks
    "MockPaymentData"
]
