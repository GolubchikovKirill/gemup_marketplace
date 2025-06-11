"""
Сервис для управления купленными прокси.

Обеспечивает функциональность работы с приобретенными прокси:
генерация списков, продление, статистика использования.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessLogicError
from app.crud.proxy_purchase import proxy_purchase_crud
from app.crud.user import user_crud
from app.integrations import get_proxy_provider, IntegrationError
from app.models.models import ProxyPurchase
from app.schemas.proxy_purchase import (
    ProxyGenerationRequest, ProxyGenerationResponse,
    ProxyExtensionRequest, ProxyExtensionResponse
)
from app.services.base import BaseService, BusinessRuleValidator

logger = logging.getLogger(__name__)


class ProxyBusinessRules(BusinessRuleValidator):
    """Валидатор бизнес-правил для прокси."""

    async def validate(self, data: Dict[str, Any], db: AsyncSession) -> bool:
        """
        Валидация бизнес-правил для прокси.

        Args:
            data: Данные для валидации
            db: Сессия базы данных

        Returns:
            bool: Результат валидации

        Raises:
            BusinessLogicError: При нарушении бизнес-правил
        """
        try:
            purchase_id = data.get("purchase_id")
            user_id = data.get("user_id")

            if not purchase_id:
                raise BusinessLogicError("Purchase ID is required")

            if not user_id:
                raise BusinessLogicError("User ID is required")

            # Проверяем существование покупки
            purchase = await proxy_purchase_crud.get(db, id=purchase_id)
            if not purchase:
                raise BusinessLogicError("Proxy purchase not found")

            # Проверяем права доступа
            if purchase.user_id != user_id:
                raise BusinessLogicError("Access denied to this proxy purchase")

            # Проверяем активность
            if not purchase.is_active:
                raise BusinessLogicError("Proxy purchase is not active")

            # Проверяем срок действия
            if purchase.expires_at <= datetime.now(timezone.utc):
                raise BusinessLogicError("Proxy purchase has expired")

            logger.debug(f"Proxy business rules validation passed for purchase {purchase_id}")
            return True

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error during proxy business rules validation: {e}")
            raise BusinessLogicError(f"Validation failed: {str(e)}")


class ProxyService(BaseService[ProxyPurchase, None, None]):
    """
    Сервис для управления купленными прокси.

    Предоставляет функциональность для работы с приобретенными прокси:
    генерация списков в различных форматах, продление срока действия,
    получение статистики использования.
    """

    def __init__(self):
        super().__init__(ProxyPurchase)
        self.crud = proxy_purchase_crud
        self.business_rules = ProxyBusinessRules()

    async def get_user_proxies(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100
    ) -> List[ProxyPurchase]:
        """
        Получение списка прокси пользователя - КЛЮЧЕВОЕ для раздела "Мои покупки".

        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            active_only: Только активные прокси
            skip: Пропустить записей
            limit: Максимум записей

        Returns:
            List[ProxyPurchase]: Список покупок прокси
        """
        try:
            return await self.crud.get_user_purchases(
                db, user_id=user_id, active_only=active_only, skip=skip, limit=limit
            )

        except Exception as e:
            logger.error(f"Error getting user proxies: {e}")
            return []

    async def generate_proxy_list(
        self,
        db: AsyncSession,
        *,
        purchase_id: int,
        user_id: int,
        generation_request: ProxyGenerationRequest
    ) -> ProxyGenerationResponse:
        """
        Генерация списка прокси в указанном формате - КЛЮЧЕВОЕ для страницы генерации.

        Args:
            db: Сессия базы данных
            purchase_id: ID покупки прокси
            user_id: ID пользователя
            generation_request: Параметры генерации

        Returns:
            ProxyGenerationResponse: Сгенерированный список прокси

        Raises:
            BusinessLogicError: При ошибках валидации или генерации
        """
        try:
            # Валидация бизнес-правил
            validation_data = {
                "purchase_id": purchase_id,
                "user_id": user_id
            }
            await self.business_rules.validate(validation_data, db)

            # Генерируем список прокси
            proxy_data = await self.crud.get_proxy_list_formatted(
                db,
                purchase_id=purchase_id,
                user_id=user_id,
                format_type=generation_request.format_type
            )

            if not proxy_data["success"]:
                raise BusinessLogicError(proxy_data["message"])

            # Создаем ответ
            response = ProxyGenerationResponse(
                purchase_id=purchase_id,
                proxy_count=proxy_data["proxy_count"],
                format=proxy_data["format"],
                proxies=proxy_data["proxies"],
                expires_at=datetime.fromisoformat(proxy_data["expires_at"].replace('Z', '+00:00')),
                generated_at=datetime.now(timezone.utc)
            )

            logger.info(f"Generated proxy list for purchase {purchase_id}: {len(proxy_data['proxies'])} proxies")
            return response

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error generating proxy list: {e}")
            raise BusinessLogicError(f"Failed to generate proxy list: {str(e)}")

    async def extend_proxy_subscription(
        self,
        db: AsyncSession,
        *,
        purchase_id: int,
        user_id: int,
        extension_request: ProxyExtensionRequest
    ) -> ProxyExtensionResponse:
        """
        Продление подписки на прокси - КЛЮЧЕВОЕ для продления услуг.

        Args:
            db: Сессия базы данных
            purchase_id: ID покупки прокси
            user_id: ID пользователя
            extension_request: Параметры продления

        Returns:
            ProxyExtensionResponse: Результат продления

        Raises:
            BusinessLogicError: При ошибках продления
        """
        try:
            # Валидация бизнес-правил
            validation_data = {
                "purchase_id": purchase_id,
                "user_id": user_id
            }
            await self.business_rules.validate(validation_data, db)

            # Выполняем продление
            extension_result = await self.crud.extend_purchase(
                db,
                purchase_id=purchase_id,
                user_id=user_id,
                extend_days=extension_request.days
            )

            if not extension_result["success"]:
                raise BusinessLogicError(extension_result["message"])

            # Создаем ответ
            response = ProxyExtensionResponse(
                purchase_id=purchase_id,
                extended_days=extension_result["extended_days"],
                new_expires_at=extension_result["new_expires_at"],
                cost=extension_result["cost"],
                currency="USD",
                status="completed"
            )

            logger.info(f"Extended proxy subscription {purchase_id} by {extension_request.days} days")
            return response

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error extending proxy subscription: {e}")
            raise BusinessLogicError(f"Failed to extend subscription: {str(e)}")

    async def get_proxy_statistics(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Получение статистики использования прокси пользователя.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            days: Период в днях

        Returns:
            Dict[str, Any]: Статистика использования
        """
        try:
            # Получаем статистику от CRUD
            stats = await self.crud.get_purchases_stats(db, user_id=user_id)

            # Дополняем информацией о пользователе
            user = await user_crud.get(db, id=user_id)

            return {
                **stats,
                "user_id": user_id,
                "user_balance": str(user.balance) if user else "0.00000000",
                "period_days": days,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting proxy statistics: {e}")
            return {
                "total_purchases": 0,
                "active_purchases": 0,
                "expired_purchases": 0,
                "expiring_soon": 0,
                "total_traffic_gb": "0.00000000",
                "product_breakdown": {},
                "period_days": days,
                "user_id": user_id
            }

    async def get_expiring_proxies(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        days_ahead: int = 7
    ) -> List[ProxyPurchase]:
        """
        Получение прокси, срок действия которых истекает.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            days_ahead: За сколько дней предупреждать

        Returns:
            List[ProxyPurchase]: Список истекающих прокси
        """
        try:
            return await self.crud.get_expiring_purchases(
                db, user_id=user_id, days_ahead=days_ahead
            )

        except Exception as e:
            logger.error(f"Error getting expiring proxies: {e}")
            return []

    async def sync_proxy_with_provider(
        self,
        db: AsyncSession,
        *,
        purchase_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Синхронизация данных прокси с провайдером - для интеграции с 711.

        Args:
            db: Сессия базы данных
            purchase_id: ID покупки
            user_id: ID пользователя

        Returns:
            Dict[str, Any]: Результат синхронизации
        """
        try:
            # Валидация прав доступа
            validation_data = {
                "purchase_id": purchase_id,
                "user_id": user_id
            }
            await self.business_rules.validate(validation_data, db)

            purchase = await self.crud.get(db, id=purchase_id)
            if not purchase or not purchase.provider_order_id:
                raise BusinessLogicError("No provider order ID found")

            # Получаем провайдера
            if not purchase.proxy_product or not purchase.proxy_product.provider:
                raise BusinessLogicError("Provider information not available")

            provider_name = purchase.proxy_product.provider.value

            try:
                provider_api = get_proxy_provider(provider_name)

                # Получаем актуальную информацию от провайдера
                provider_status = await provider_api.get_proxy_status(purchase.provider_order_id)

                # Синхронизируем данные
                sync_result = await self.crud.sync_with_provider(
                    db, purchase_id=purchase_id, provider_data=provider_status
                )

                if sync_result:
                    logger.info(f"Synced purchase {purchase_id} with provider {provider_name}")
                    return {
                        "success": True,
                        "message": "Synchronization completed",
                        "provider_status": provider_status,
                        "last_sync": datetime.now(timezone.utc).isoformat()
                    }
                else:
                    return {
                        "success": False,
                        "message": "Synchronization failed",
                        "provider_status": provider_status
                    }

            except IntegrationError as e:
                logger.warning(f"Provider integration error: {e}")
                return {
                    "success": False,
                    "message": f"Provider error: {e.message}",
                    "provider_status": None
                }

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error syncing with provider: {e}")
            return {
                "success": False,
                "message": f"Sync failed: {str(e)}",
                "provider_status": None
            }

    async def get_proxy_usage_details(
        self,
        db: AsyncSession,
        *,
        purchase_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Получение детальной информации об использовании прокси.

        Args:
            db: Сессия базы данных
            purchase_id: ID покупки
            user_id: ID пользователя

        Returns:
            Dict[str, Any]: Детальная информация об использовании
        """
        try:
            # Валидация прав доступа
            validation_data = {
                "purchase_id": purchase_id,
                "user_id": user_id
            }
            await self.business_rules.validate(validation_data, db)

            purchase = await self.crud.get_user_purchase(
                db, purchase_id=purchase_id, user_id=user_id
            )

            if not purchase:
                raise BusinessLogicError("Purchase not found")

            # Рассчитываем дополнительную информацию
            current_time = datetime.now(timezone.utc)
            time_remaining = purchase.expires_at - current_time
            days_remaining = max(0, time_remaining.days)

            # Подсчитываем количество прокси
            proxy_count = len(purchase.proxy_list.split('\n')) if purchase.proxy_list else 0

            return {
                "purchase_id": purchase_id,
                "proxy_count": proxy_count,
                "traffic_used_gb": str(purchase.traffic_used_gb),
                "expires_at": purchase.expires_at.isoformat(),
                "days_remaining": days_remaining,
                "is_active": purchase.is_active,
                "last_used": purchase.last_used.isoformat() if purchase.last_used else None,
                "provider_order_id": purchase.provider_order_id,
                "product_info": {
                    "name": purchase.proxy_product.name if purchase.proxy_product else "Unknown",
                    "country": purchase.proxy_product.country_name if purchase.proxy_product else "Unknown",
                    "category": purchase.proxy_product.proxy_category.value if purchase.proxy_product else "Unknown"
                },
                "order_info": {
                    "order_number": purchase.order.order_number if purchase.order else "Unknown",
                    "order_date": purchase.order.created_at.isoformat() if purchase.order else None
                }
            }

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error getting proxy usage details: {e}")
            raise BusinessLogicError(f"Failed to get usage details: {str(e)}")

    async def deactivate_proxy_purchase(
        self,
        db: AsyncSession,
        *,
        purchase_id: int,
        user_id: int,
        reason: Optional[str] = None
    ) -> bool:
        """
        Деактивация покупки прокси.

        Args:
            db: Сессия базы данных
            purchase_id: ID покупки
            user_id: ID пользователя
            reason: Причина деактивации

        Returns:
            bool: Успешность операции
        """
        try:
            # Валидация прав доступа
            validation_data = {
                "purchase_id": purchase_id,
                "user_id": user_id
            }
            await self.business_rules.validate(validation_data, db)

            result = await self.crud.deactivate_purchase(
                db, purchase_id=purchase_id, reason=reason
            )

            if result:
                logger.info(f"Deactivated proxy purchase {purchase_id}, reason: {reason}")
                return True
            else:
                return False

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error deactivating proxy purchase: {e}")
            return False

    # Реализация абстрактных методов BaseService
    async def create(self, db: AsyncSession, *, obj_in) -> ProxyPurchase:
        raise NotImplementedError("Use order service to create proxy purchases")

    async def get(self, db: AsyncSession, *, obj_id: int) -> Optional[ProxyPurchase]:
        return await self.crud.get(db, id=obj_id)

    async def update(self, db: AsyncSession, *, db_obj: ProxyPurchase, obj_in) -> ProxyPurchase:
        raise NotImplementedError("Use specific methods for updating proxy purchases")

    async def delete(self, db: AsyncSession, *, obj_id: int) -> bool:
        raise NotImplementedError("Use deactivate_proxy_purchase method instead")

    async def get_multi(self, db: AsyncSession, *, skip: int = 0, limit: int = 100) -> List[ProxyPurchase]:
        return await self.crud.get_multi(db, skip=skip, limit=limit)


proxy_service = ProxyService()
