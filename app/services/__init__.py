"""
Модуль сервисов приложения.

Содержит бизнес-логику приложения, реализованную в соответствии с принципами
Clean Architecture и Domain-Driven Design. Каждый сервис отвечает за конкретную
область бизнес-логики и предоставляет высокоуровневый API для работы с данными.

Сервисы:
- auth_service: Аутентификация и авторизация пользователей
- cart_service: Управление корзиной покупок
- order_service: Обработка заказов и их жизненный цикл
- payment_service: Интеграция с платежными системами
- product_service: Управление каталогом продуктов прокси
- proxy_service: Работа с купленными прокси-серверами

Базовые классы:
- BaseService: Абстрактный базовый класс для всех сервисов
- BusinessRuleValidator: Валидатор бизнес-правил
- EventPublisher: Публикатор событий
- CacheService: Абстракция для кэширования

Архитектурные принципы:
- Инверсия зависимостей (Dependency Inversion)
- Единственная ответственность (Single Responsibility)
- Открыт/закрыт (Open/Closed)
- Разделение интерфейса (Interface Segregation)

Использование:
    from app.services import auth_service, cart_service, order_service

    # Аутентификация пользователя
    user = await auth_service.authenticate_user(email, password, db)

    # Добавление товара в корзину
    cart_item = await cart_service.add_item_to_cart(db, product_id, quantity, user_id=user.id)

    # Создание заказа
    order = await order_service.create_order_from_cart(db, user)
"""
from typing import Dict

from .auth_service import auth_service, AuthService
from .cart_service import cart_service, CartService
from .order_service import order_service, OrderService
from .payment_service import payment_service, PaymentService
from .product_service import product_service, ProductService
from .proxy_service import proxy_service, ProxyService

# Базовые классы
from .base import (
    BaseService,
    BusinessRuleValidator,
    EventPublisher,
    CacheService
)

__all__ = [
    # Экземпляры сервисов (готовые к использованию)
    "auth_service",
    "cart_service",
    "order_service",
    "payment_service",
    "product_service",
    "proxy_service",

    # Классы сервисов (для наследования или создания новых экземпляров)
    "AuthService",
    "CartService",
    "OrderService",
    "PaymentService",
    "ProductService",
    "ProxyService",

    # Базовые классы
    "BaseService",
    "BusinessRuleValidator",
    "EventPublisher",
    "CacheService",
]

# Версия модуля сервисов
__version__ = "1.0.0"

# Реестр всех сервисов для быстрого доступа
SERVICES_REGISTRY = {
    "auth": auth_service,
    "cart": cart_service,
    "order": order_service,
    "payment": payment_service,
    "product": product_service,
    "proxy": proxy_service,
}


def get_service(service_name: str):
    """
    Получение сервиса по имени.

    Args:
        service_name: Имя сервиса (auth, cart, order, payment, product, proxy)

    Returns:
        Экземпляр запрошенного сервиса

    Raises:
        KeyError: Если сервис не найден

    Example:
        auth_service = get_service("auth")
        user = await auth_service.authenticate_user(email, password, db)
    """
    if service_name not in SERVICES_REGISTRY:
        available_services = ", ".join(SERVICES_REGISTRY.keys())
        raise KeyError(f"Service '{service_name}' not found. Available: {available_services}")

    return SERVICES_REGISTRY[service_name]


async def health_check_all_services() -> Dict[str, bool]:
    """
    Проверка состояния всех сервисов.

    Returns:
        Dict[str, bool]: Статус каждого сервиса
    """
    results = {}

    for name, service in SERVICES_REGISTRY.items():
        try:
            # Проверяем, есть ли у сервиса метод health_check
            if hasattr(service, 'health_check'):
                results[name] = await service.health_check()
            else:
                # Простая проверка - сервис существует и имеет нужные атрибуты
                results[name] = hasattr(service, 'business_rules') or hasattr(service, 'crud')
        except Exception as e:
            logger.error(f"Health check failed for service {name}: {e}")
            results[name] = False

    return results


# Вспомогательные функции для группового управления сервисами
async def initialize_all_services():
    """
    Инициализация всех сервисов (если требуется).

    Некоторые сервисы могут требовать дополнительной инициализации
    при старте приложения.
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.info("Initializing all services...")

    for name, service in SERVICES_REGISTRY.items():
        try:
            if hasattr(service, 'initialize'):
                await service.initialize()
                logger.debug(f"Service {name} initialized")
        except Exception as e:
            logger.error(f"Failed to initialize service {name}: {e}")

    logger.info("All services initialization completed")


async def cleanup_all_services():
    """
    Очистка ресурсов всех сервисов при завершении приложения.

    Вызывается при shutdown приложения для корректного
    освобождения ресурсов.
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.info("Cleaning up all services...")

    for name, service in SERVICES_REGISTRY.items():
        try:
            if hasattr(service, 'cleanup'):
                await service.cleanup()
                logger.debug(f"Service {name} cleaned up")
        except Exception as e:
            logger.error(f"Failed to cleanup service {name}: {e}")

    logger.info("All services cleanup completed")


# Импорт для обратной совместимости
import logging

logger = logging.getLogger(__name__)

# Логирование инициализации модуля
logger.debug("Services module initialized with all services")
