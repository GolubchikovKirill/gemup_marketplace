"""
Сервис для управления купленными прокси.

Обеспечивает активацию, мониторинг, продление и управление
прокси-серверами, приобретенными пользователями.
Полная production-ready реализация без мок-данных.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessLogicError
from app.crud.proxy_purchase import proxy_purchase_crud
from app.crud.proxy_product import proxy_product_crud
from app.integrations import get_proxy_provider
from app.models.models import ProxyPurchase, Order, ProviderType
from app.schemas.proxy_purchase import ProxyPurchaseCreate, ProxyPurchaseUpdate
from app.services.base import BaseService, BusinessRuleValidator

logger = logging.getLogger(__name__)


class ProxyBusinessRules(BusinessRuleValidator):
    """Валидатор бизнес-правил для прокси."""

    async def validate(self, data: dict, session: AsyncSession) -> bool:  # ИСПРАВЛЕНО: переименовал db в session
        """
        Валидация бизнес-правил для прокси.

        Args:
            data: Данные для валидации
            session: Сессия базы данных

        Returns:
            bool: Результат валидации

        Raises:
            BusinessLogicError: При нарушении бизнес-правил
        """
        try:
            # Валидация основных параметров
            if "user_id" in data and not data["user_id"]:
                raise BusinessLogicError("User ID is required")

            if "days" in data:
                days = data["days"]
                if not isinstance(days, int) or days <= 0:
                    raise BusinessLogicError("Days must be a positive integer")
                if days > 365:
                    raise BusinessLogicError("Maximum extension period is 365 days")

            # Валидация статуса прокси
            if "status" in data:
                valid_statuses = ["active", "expired", "cancelled"]
                if data["status"] not in valid_statuses:
                    raise BusinessLogicError(f"Status must be one of: {', '.join(valid_statuses)}")

            logger.debug("Proxy business rules validation passed")
            return True

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error during proxy business rules validation: {e}")
            raise BusinessLogicError(f"Validation failed: {str(e)}")


class ProxyService(BaseService[ProxyPurchase, ProxyPurchaseCreate, ProxyPurchaseUpdate]):
    """
    Сервис для управления купленными прокси.

    Предоставляет функциональность для активации, мониторинга,
    продления и управления жизненным циклом прокси-серверов.
    """

    def __init__(self):
        super().__init__(ProxyPurchase)
        self.crud = proxy_purchase_crud
        self.business_rules = ProxyBusinessRules()

    async def get_user_proxies(
        self,
        session: AsyncSession,  # ИСПРАВЛЕНО: переименовал db в session
        user_id: int,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100
    ) -> List[ProxyPurchase]:
        """
        Получение списка прокси пользователя.

        Args:
            session: Сессия базы данных
            user_id: Идентификатор пользователя
            active_only: Только активные прокси
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            List[ProxyPurchase]: Список прокси пользователя

        Raises:
            BusinessLogicError: При ошибках валидации
        """
        try:
            validation_data = {"user_id": user_id}
            await self.business_rules.validate(validation_data, session)

            return await self.crud.get_user_purchases(
                session, user_id=user_id, active_only=active_only, skip=skip, limit=limit
            )

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error getting user proxies: {e}")
            return []

    async def get_proxy_details(
        self,
        session: AsyncSession,  # ИСПРАВЛЕНО: переименовал db в session
        purchase_id: int,
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Получение детальной информации о покупке прокси.

        Args:
            session: Сессия базы данных
            purchase_id: Идентификатор покупки
            user_id: Идентификатор пользователя (для проверки прав)

        Returns:
            Optional[Dict[str, Any]]: Детальная информация о прокси

        Raises:
            BusinessLogicError: При ошибках доступа
        """
        try:
            purchase = await self.crud.get_user_purchase(
                session, purchase_id=purchase_id, user_id=user_id
            )

            if not purchase:
                raise BusinessLogicError("Proxy purchase not found or access denied")

            # Получаем актуальную информацию о продукте
            product = await proxy_product_crud.get(session, obj_id=purchase.proxy_product_id)

            # Проверяем статус у провайдера
            provider_status = await self._check_provider_status(session, purchase)

            # Парсим список прокси
            proxy_list = self._parse_proxy_list(purchase.proxy_list)

            return {
                "id": purchase.id,
                "order_id": purchase.order_id,
                "product": {
                    "id": product.id if product else None,
                    "name": product.name if product else "Unknown Product",
                    "provider": product.provider.value if product and product.provider else "unknown",
                    "country": product.country_name if product else None
                },
                "proxy_list": proxy_list,
                "credentials": {
                    "username": purchase.username,
                    "password": purchase.password
                },
                "status": {
                    "is_active": purchase.is_active,
                    "expires_at": purchase.expires_at.isoformat() if purchase.expires_at else None,
                    "is_expired": purchase.expires_at < datetime.now() if purchase.expires_at else False,
                    "days_remaining": self._calculate_days_remaining(purchase.expires_at),
                    "provider_status": provider_status
                },
                "usage": {
                    "traffic_used_gb": str(purchase.traffic_used_gb) if hasattr(purchase, 'traffic_used_gb') else "0.00",
                    "last_used": purchase.last_used.isoformat() if hasattr(purchase, 'last_used') and purchase.last_used else None
                },
                "metadata": {
                    "provider_order_id": purchase.provider_order_id,
                    "created_at": purchase.created_at.isoformat(),
                    "updated_at": purchase.updated_at.isoformat()
                }
            }

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error getting proxy details: {e}")
            return None

    async def extend_proxy_subscription(
        self,
        session: AsyncSession,  # ИСПРАВЛЕНО: переименовал db в session
        purchase_id: int,
        user_id: int,
        days: int
    ) -> Dict[str, Any]:
        """
        Продление подписки на прокси.

        Args:
            session: Сессия базы данных
            purchase_id: Идентификатор покупки
            user_id: Идентификатор пользователя
            days: Количество дней для продления

        Returns:
            Dict[str, Any]: Результат продления

        Raises:
            BusinessLogicError: При ошибках валидации или продления
        """
        try:
            validation_data = {"user_id": user_id, "days": days}
            await self.business_rules.validate(validation_data, session)

            purchase = await self.crud.get_user_purchase(
                session, purchase_id=purchase_id, user_id=user_id
            )

            if not purchase:
                raise BusinessLogicError("Proxy purchase not found or access denied")

            if not purchase.is_active:
                raise BusinessLogicError("Cannot extend inactive proxy subscription")

            # Рассчитываем новую дату истечения
            current_expires = purchase.expires_at or datetime.now()
            if current_expires < datetime.now():
                # Если уже истек, продлеваем от текущего момента
                new_expires_at = datetime.now() + timedelta(days=days)
            else:
                # Если еще активен, продлеваем от текущей даты истечения
                new_expires_at = current_expires + timedelta(days=days)

            # Пытаемся продлить через провайдера
            extension_cost = await self._extend_with_provider(session, purchase, days)

            # Обновляем дату истечения в нашей БД
            updated_purchase = await self.crud.update_expiry(
                session, purchase=purchase, new_expires_at=new_expires_at
            )

            if not updated_purchase:
                raise BusinessLogicError("Failed to update proxy expiry date")

            logger.info(f"Extended proxy {purchase_id} for {days} days")

            return {
                "purchase_id": purchase_id,
                "extended_days": days,
                "new_expires_at": new_expires_at.isoformat(),
                "cost": str(extension_cost) if extension_cost else "0.00",
                "currency": "USD",
                "status": "extended"
            }

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error extending proxy subscription: {e}")
            raise BusinessLogicError(f"Failed to extend subscription: {str(e)}")

    async def get_expiring_proxies(
        self,
        session: AsyncSession,  # ИСПРАВЛЕНО: переименовал db в session
        user_id: int,
        days_ahead: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Получение списка истекающих прокси.

        Args:
            session: Сессия базы данных
            user_id: Идентификатор пользователя
            days_ahead: За сколько дней до истечения показывать

        Returns:
            List[Dict[str, Any]]: Список истекающих прокси
        """
        try:
            validation_data = {"user_id": user_id, "days": days_ahead}
            await self.business_rules.validate(validation_data, session)

            expiring_purchases = await self.crud.get_expiring_purchases(
                session, user_id=user_id, days_ahead=days_ahead
            )

            result = []
            for purchase in expiring_purchases:
                product = await proxy_product_crud.get(session, obj_id=purchase.proxy_product_id)
                days_remaining = self._calculate_days_remaining(purchase.expires_at)

                result.append({
                    "id": purchase.id,
                    "product_name": product.name if product else "Unknown Product",
                    "country": product.country_name if product else None,
                    "expires_at": purchase.expires_at.isoformat(),
                    "days_remaining": days_remaining,
                    "proxy_count": len(self._parse_proxy_list(purchase.proxy_list)),
                    "can_extend": purchase.is_active and days_remaining >= 0
                })

            return result

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error getting expiring proxies: {e}")
            return []

    async def activate_proxies_for_order(self, session: AsyncSession, order: Order) -> bool:  # ИСПРАВЛЕНО: переименовал db в session
        """
        Активация всех прокси для заказа.

        Args:
            session: Сессия базы данных
            order: Заказ для активации

        Returns:
            bool: Успешность активации
        """
        try:
            purchases = await self.crud.get_purchases_by_order_id(session, order_id=order.id)

            activated_count = 0
            for purchase in purchases:
                if not purchase.is_active:
                    purchase.is_active = True
                    activated_count += 1

            if activated_count > 0:
                await session.commit()

            logger.info(f"Activated {activated_count} proxy purchases for order {order.id}")
            return True

        except Exception as e:
            logger.error(f"Error activating proxies for order {order.id}: {e}")
            return False

    async def deactivate_proxy(
        self,
        session: AsyncSession,  # ИСПРАВЛЕНО: переименовал db в session
        purchase_id: int,
        user_id: int,
        reason: Optional[str] = None
    ) -> bool:
        """
        Деактивация прокси.

        Args:
            session: Сессия базы данных
            purchase_id: Идентификатор покупки
            user_id: Идентификатор пользователя
            reason: Причина деактивации

        Returns:
            bool: Успешность операции

        Raises:
            BusinessLogicError: При ошибках доступа
        """
        try:
            purchase = await self.crud.get_user_purchase(
                session, purchase_id=purchase_id, user_id=user_id
            )

            if not purchase:
                raise BusinessLogicError("Proxy purchase not found or access denied")

            deactivated_purchase = await self.crud.deactivate_purchase(
                session, purchase_id=purchase_id, reason=reason
            )

            if not deactivated_purchase:
                raise BusinessLogicError("Failed to deactivate proxy")

            logger.info(f"Deactivated proxy {purchase_id}, reason: {reason}")
            return True

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error deactivating proxy: {e}")
            return False

    async def update_traffic_usage(
        self,
        session: AsyncSession,  # ИСПРАВЛЕНО: переименовал db в session
        purchase_id: int,
        traffic_used_gb: Decimal
    ) -> bool:
        """
        Обновление информации об использованном трафике.

        Args:
            session: Сессия базы данных
            purchase_id: Идентификатор покупки
            traffic_used_gb: Использованный трафик в ГБ

        Returns:
            bool: Успешность операции
        """
        try:
            updated_purchase = await self.crud.update_traffic_usage(
                session, purchase_id=purchase_id, traffic_used_gb=traffic_used_gb
            )

            if updated_purchase:
                logger.debug(f"Updated traffic usage for purchase {purchase_id}: {traffic_used_gb} GB")
                return True
            return False

        except Exception as e:
            logger.error(f"Error updating traffic usage: {e}")
            return False

    async def get_proxy_statistics(
        self,
        session: AsyncSession,  # ИСПРАВЛЕНО: переименовал db в session
        user_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Получение статистики по прокси пользователя.

        Args:
            session: Сессия базы данных
            user_id: Идентификатор пользователя
            days: Период для статистики

        Returns:
            Dict[str, Any]: Статистика прокси
        """
        try:
            return await self.crud.get_purchases_stats(session, user_id=user_id, days=days)

        except Exception as e:
            logger.error(f"Error getting proxy statistics: {e}")
            return {
                "total_purchases": 0,
                "active_purchases": 0,
                "total_traffic_used_gb": "0.00",
                "product_breakdown": {},
                "period_days": days
            }

    @staticmethod  # ИСПРАВЛЕНО: добавлен @staticmethod
    async def _check_provider_status(session: AsyncSession, purchase: ProxyPurchase) -> Dict[str, Any]:  # ИСПРАВЛЕНО: добавлен параметр session
        """
        Проверка статуса прокси у провайдера.

        Args:
            session: Сессия базы данных
            purchase: Покупка прокси

        Returns:
            Dict[str, Any]: Статус от провайдера
        """
        try:
            if not purchase.provider_order_id:
                return {"status": "unknown", "message": "No provider order ID"}

            # Получаем продукт для определения провайдера
            product = await proxy_product_crud.get(session, obj_id=purchase.proxy_product_id)
            if not product or not product.provider:
                return {"status": "unknown", "message": "Unknown provider"}

            if product.provider == ProviderType.PROVIDER_711:
                proxy_api = get_proxy_provider("711proxy")
                return await proxy_api.get_proxy_status(purchase.provider_order_id)
            else:
                return {"status": "unsupported", "message": f"Provider {product.provider} not supported"}

        except Exception as e:
            logger.warning(f"Failed to check provider status: {e}")
            return {"status": "error", "message": str(e)}

    @staticmethod  # ИСПРАВЛЕНО: добавлен @staticmethod
    async def _extend_with_provider(session: AsyncSession, purchase: ProxyPurchase, days: int) -> Optional[Decimal]:  # ИСПРАВЛЕНО: добавлен параметр session
        """
        Продление прокси через провайдера.

        Args:
            session: Сессия базы данных
            purchase: Покупка прокси
            days: Количество дней

        Returns:
            Optional[Decimal]: Стоимость продления или None
        """
        try:
            if not purchase.provider_order_id:
                logger.warning("No provider order ID for extension")
                return None

            product = await proxy_product_crud.get(session, obj_id=purchase.proxy_product_id)
            if not product or not product.provider:
                return None

            if product.provider == ProviderType.PROVIDER_711:
                proxy_api = get_proxy_provider("711proxy")
                result = await proxy_api.extend_proxies(purchase.provider_order_id, days)
                return Decimal(result.get("cost", "0.00"))
            else:
                logger.warning(f"Provider {product.provider} extension not supported")
                return None

        except Exception as e:
            logger.error(f"Failed to extend with provider: {e}")
            return None

    @staticmethod
    def _parse_proxy_list(proxy_list_str: str) -> List[Dict[str, Any]]:
        """
        Парсинг строки со списком прокси.

        Args:
            proxy_list_str: Строка с прокси

        Returns:
            List[Dict[str, Any]]: Распарсенный список прокси
        """
        if not proxy_list_str:
            return []

        proxies = []
        lines = proxy_list_str.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Поддерживаем разные форматы: ip:port:user:pass, ip:port, etc.
            parts = line.split(':')

            if len(parts) >= 2:
                proxy_info = {
                    "ip": parts[0],
                    "port": int(parts[1]) if parts[1].isdigit() else None,
                    "username": parts[2] if len(parts) > 2 else None,
                    "password": parts[3] if len(parts) > 3 else None,
                    "full_string": line
                }
                proxies.append(proxy_info)

        return proxies

    @staticmethod
    def _calculate_days_remaining(expires_at: Optional[datetime]) -> int:
        """
        Расчет оставшихся дней до истечения.

        Args:
            expires_at: Дата истечения

        Returns:
            int: Количество дней (может быть отрицательным если уже истек)
        """
        if not expires_at:
            return 0

        delta = expires_at - datetime.now()
        return delta.days

    # Реализация абстрактных методов BaseService
    async def create(self, session: AsyncSession, obj_in: ProxyPurchaseCreate) -> ProxyPurchase:  # ИСПРАВЛЕНО: переименовал db в session
        return await self.crud.create(session, obj_in=obj_in)

    async def get(self, session: AsyncSession, obj_id: int) -> Optional[ProxyPurchase]:  # ИСПРАВЛЕНО: переименовал db в session
        return await self.crud.get(session, obj_id=obj_id)

    async def update(self, session: AsyncSession, db_obj: ProxyPurchase, obj_in: ProxyPurchaseUpdate) -> ProxyPurchase:  # ИСПРАВЛЕНО: переименовал db в session
        return await self.crud.update(session, db_obj=db_obj, obj_in=obj_in)

    async def delete(self, session: AsyncSession, obj_id: int) -> bool:  # ИСПРАВЛЕНО: переименовал db в session
        result = await self.crud.delete(session, obj_id=obj_id)
        return result is not None

    async def get_multi(self, session: AsyncSession, skip: int = 0, limit: int = 100) -> List[ProxyPurchase]:  # ИСПРАВЛЕНО: переименовал db в session
        return await self.crud.get_multi(session, skip=skip, limit=limit)


proxy_service = ProxyService()
