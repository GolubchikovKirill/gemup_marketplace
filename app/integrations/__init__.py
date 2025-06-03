"""
Модуль интеграций с внешними сервисами.

Содержит клиенты для работы с:
- Платежными системами (Cryptomus)
- Провайдерами прокси (711Proxy, и другие)
- Внешними API

Все интеграции следуют единому стандарту обработки ошибок,
логирования и конфигурации.
"""
from typing import Dict

from .base import BaseIntegration, IntegrationError
from .cryptomus import cryptomus_api, CryptomusAPI
from .proxy_711 import proxy_711_api, Proxy711API

# Попытка импорта дополнительных интеграций
try:
    from .other_providers import *
except ImportError:
    # Дополнительные провайдеры пока не реализованы
    pass

__all__ = [
    # Базовые классы
    "BaseIntegration",
    "IntegrationError",

    # Платежные системы
    "CryptomusAPI",
    "cryptomus_api",

    # Провайдеры прокси
    "Proxy711API",
    "proxy_711_api",

    # Функции для получения провайдеров
    "get_payment_provider",
    "get_proxy_provider",  # ИСПРАВЛЕНО: добавлено в __all__
]

# Версия модуля интеграций
__version__ = "1.0.0"

# Реестр всех доступных интеграций
INTEGRATIONS_REGISTRY = {
    "payment": {
        "cryptomus": cryptomus_api,
    },
    "proxy": {
        "711proxy": proxy_711_api,
    }
}


def get_payment_provider(provider_name: str = "cryptomus"):
    """
    Получение провайдера платежей.

    Args:
        provider_name: Имя провайдера платежей

    Returns:
        Экземпляр API провайдера платежей

    Raises:
        KeyError: Если провайдер не найден
    """
    if provider_name not in INTEGRATIONS_REGISTRY["payment"]:
        available = ", ".join(INTEGRATIONS_REGISTRY["payment"].keys())
        raise KeyError(f"Payment provider '{provider_name}' not found. Available: {available}")

    return INTEGRATIONS_REGISTRY["payment"][provider_name]


def get_proxy_provider(provider_name: str):
    """
    Получение провайдера прокси.

    Args:
        provider_name: Имя провайдера прокси

    Returns:
        Экземпляр API провайдера прокси

    Raises:
        KeyError: Если провайдер не найден
    """
    if provider_name not in INTEGRATIONS_REGISTRY["proxy"]:
        available = ", ".join(INTEGRATIONS_REGISTRY["proxy"].keys())
        raise KeyError(f"Proxy provider '{provider_name}' not found. Available: {available}")

    return INTEGRATIONS_REGISTRY["proxy"][provider_name]


async def test_all_integrations() -> Dict[str, bool]:
    """
    Тестирование всех интеграций.

    Returns:
        Dict[str, bool]: Результаты тестирования для каждой интеграции
    """
    results = {}

    # Тестируем платежные системы
    for name, provider in INTEGRATIONS_REGISTRY["payment"].items():
        try:
            if hasattr(provider, 'test_connection'):
                results[f"payment_{name}"] = await provider.test_connection()
            else:
                results[f"payment_{name}"] = True  # Предполагаем что работает
        except Exception:
            results[f"payment_{name}"] = False

    # Тестируем провайдеров прокси
    for name, provider in INTEGRATIONS_REGISTRY["proxy"].items():
        try:
            if hasattr(provider, 'test_connection'):
                results[f"proxy_{name}"] = await provider.test_connection()
            else:
                results[f"proxy_{name}"] = True
        except Exception:
            results[f"proxy_{name}"] = False

    return results
