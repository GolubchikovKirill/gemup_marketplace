"""
Модуль интеграций с внешними сервисами - оптимизировано для MVP.

Содержит интеграции с:
- Провайдерами прокси (711proxy)
- Платежными системами (Cryptomus)
"""

from typing import Dict, Any

from .base import BaseIntegration, IntegrationError
from .cryptomus import cryptomus_api
from .proxy_711 import proxy_711_api

# Реестр провайдеров прокси для MVP
PROXY_PROVIDERS = {
    "711proxy": proxy_711_api,
}

# Реестр платежных провайдеров для MVP
PAYMENT_PROVIDERS = {
    "cryptomus": cryptomus_api,
}


def get_proxy_provider(provider_name: str) -> BaseIntegration:
    """
    Получение провайдера прокси по имени.

    Args:
        provider_name: Имя провайдера

    Returns:
        BaseIntegration: Экземпляр провайдера

    Raises:
        ValueError: Если провайдер не найден
    """
    if provider_name not in PROXY_PROVIDERS:
        available = ", ".join(PROXY_PROVIDERS.keys())
        raise ValueError(f"Unknown proxy provider '{provider_name}'. Available: {available}")

    return PROXY_PROVIDERS[provider_name]


def get_payment_provider(provider_name: str) -> BaseIntegration:
    """
    Получение платежного провайдера по имени.

    Args:
        provider_name: Имя провайдера

    Returns:
        BaseIntegration: Экземпляр провайдера

    Raises:
        ValueError: Если провайдер не найден
    """
    if provider_name not in PAYMENT_PROVIDERS:
        available = ", ".join(PAYMENT_PROVIDERS.keys())
        raise ValueError(f"Unknown payment provider '{provider_name}'. Available: {available}")

    return PAYMENT_PROVIDERS[provider_name]


async def test_all_integrations() -> Dict[str, Dict[str, Any]]:
    """
    Тестирование всех интеграций - для проверки MVP.

    Returns:
        Dict[str, Dict[str, Any]]: Результаты тестирования
    """
    results = {
        "proxy_providers": {},
        "payment_providers": {}
    }

    # Тестируем провайдеров прокси
    for name, provider in PROXY_PROVIDERS.items():
        try:
            is_connected = await provider.test_connection()
            results["proxy_providers"][name] = {
                "status": "connected" if is_connected else "failed",
                "error": None
            }
        except Exception as e:
            results["proxy_providers"][name] = {
                "status": "error",
                "error": str(e)
            }

    # Тестируем платежных провайдеров
    for name, provider in PAYMENT_PROVIDERS.items():
        try:
            is_connected = await provider.test_connection()
            results["payment_providers"][name] = {
                "status": "connected" if is_connected else "failed",
                "error": None
            }
        except Exception as e:
            results["payment_providers"][name] = {
                "status": "error",
                "error": str(e)
            }

    return results


async def get_integration_status() -> Dict[str, Any]:
    """
    Получение статуса всех интеграций.

    Returns:
        Dict[str, Any]: Сводная информация о статусе
    """
    test_results = await test_all_integrations()

    total_proxy = len(PROXY_PROVIDERS)
    connected_proxy = sum(1 for r in test_results["proxy_providers"].values() if r["status"] == "connected")

    total_payment = len(PAYMENT_PROVIDERS)
    connected_payment = sum(1 for r in test_results["payment_providers"].values() if r["status"] == "connected")

    return {
        "proxy_providers": {
            "total": total_proxy,
            "connected": connected_proxy,
            "available": list(PROXY_PROVIDERS.keys()),
            "details": test_results["proxy_providers"]
        },
        "payment_providers": {
            "total": total_payment,
            "connected": connected_payment,
            "available": list(PAYMENT_PROVIDERS.keys()),
            "details": test_results["payment_providers"]
        },
        "overall_status": "healthy" if (connected_proxy > 0 and connected_payment > 0) else "degraded"
    }


__all__ = [
    "BaseIntegration",
    "IntegrationError",
    "proxy_711_api",
    "cryptomus_api",
    "get_proxy_provider",
    "get_payment_provider",
    "test_all_integrations",
    "get_integration_status",
    "PROXY_PROVIDERS",
    "PAYMENT_PROVIDERS"
]
