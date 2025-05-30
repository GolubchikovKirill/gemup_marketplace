import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessLogicError
from app.crud.proxy_purchase import proxy_purchase_crud
from app.integrations.proxy_711 import proxy_711_api
from app.models.models import ProxyPurchase, Order, User
from app.services.base import BaseService, BusinessRuleValidator

logger = logging.getLogger(__name__)


class ProxyBusinessRules(BusinessRuleValidator):
    """Валидатор бизнес-правил для прокси"""

    async def validate(self, data: dict, db: AsyncSession) -> bool:
        """Валидация правил прокси"""
        return True


class ProxyService(BaseService[ProxyPurchase, dict, dict]):
    """Сервис для работы с прокси"""

    def __init__(self):
        super().__init__(ProxyPurchase)
        self.business_rules = ProxyBusinessRules()

    @staticmethod
    async def activate_proxies_for_order(
            db: AsyncSession,
            order: Order
    ) -> List[ProxyPurchase]:
        """Активация прокси после успешной оплаты заказа"""
        try:
            activated_proxies = []

            for order_item in order.order_items:
                # Покупаем прокси у провайдера
                proxy_data = await proxy_711_api.purchase_proxies(
                    product_id=str(order_item.proxy_product_id),
                    quantity=order_item.quantity,
                    duration_days=order_item.proxy_product.duration_days,
                    country_code=order_item.proxy_product.country_code,
                    city=order_item.proxy_product.city
                )

                # Создаем запись о покупке прокси
                proxy_purchase = await proxy_purchase_crud.create_purchase(
                    db,
                    user_id=order.user_id,
                    proxy_product_id=order_item.proxy_product_id,
                    order_id=order.id,
                    proxy_list=proxy_data.get('proxies', []),
                    username=proxy_data.get('username'),
                    password=proxy_data.get('password'),
                    expires_at=datetime.now() + timedelta(days=order_item.proxy_product.duration_days),
                    provider_order_id=proxy_data.get('order_id')
                )

                activated_proxies.append(proxy_purchase)
                logger.info(f"Activated {order_item.quantity} proxies for order {order.id}")

            return activated_proxies

        except Exception as e:
            logger.error(f"Error activating proxies for order {order.id}: {e}")
            raise BusinessLogicError(f"Failed to activate proxies: {str(e)}")

    @staticmethod
    async def get_user_proxies(
            db: AsyncSession,
            user: User,
            active_only: bool = True
    ) -> List[ProxyPurchase]:
        """Получение прокси пользователя"""
        return await proxy_purchase_crud.get_user_purchases(
            db,
            user_id=user.id,
            active_only=active_only
        )

    async def generate_proxy_list(
            self,
            db: AsyncSession,
            purchase_id: int,
            user: User,
            format_type: str = "ip:port:user:pass"
    ) -> Dict[str, Any]:
        """Генерация списка прокси в нужном формате"""
        try:
            # Получаем покупку прокси
            purchase = await proxy_purchase_crud.get_user_purchase(
                db, purchase_id=purchase_id, user_id=user.id
            )

            if not purchase:
                raise BusinessLogicError("Proxy purchase not found")

            if not purchase.is_active:
                raise BusinessLogicError("Proxy purchase is not active")

            if purchase.expires_at < datetime.now():
                raise BusinessLogicError("Proxy purchase has expired")

            # Форматируем прокси
            formatted_proxies = self._format_proxy_list(
                purchase.proxy_list,
                purchase.username,
                purchase.password,
                format_type
            )

            return {
                "purchase_id": purchase.id,
                "proxy_count": len(formatted_proxies),
                "format": format_type,
                "expires_at": purchase.expires_at,
                "proxies": formatted_proxies
            }

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error generating proxy list: {e}")
            raise BusinessLogicError(f"Failed to generate proxy list: {str(e)}")

    @staticmethod
    def _format_proxy_list(
            proxy_list: str,
            username: str,
            password: str,
            format_type: str
    ) -> List[str]:
        """Форматирование списка прокси"""
        # ИСПРАВЛЕНО: правильный парсинг строки прокси
        if isinstance(proxy_list, str):
            # Разбиваем по переносам строк и фильтруем пустые
            proxies = [line.strip() for line in proxy_list.split('\n') if line.strip()]
        else:
            proxies = proxy_list

        formatted = []

        for proxy in proxies:
            # Убираем лишние пробелы
            proxy = proxy.strip()
            if not proxy:
                continue

            if format_type == "ip:port:user:pass":
                formatted.append(f"{proxy}:{username}:{password}")
            elif format_type == "user:pass@ip:port":
                formatted.append(f"{username}:{password}@{proxy}")
            elif format_type == "ip:port":
                formatted.append(proxy)
            else:
                formatted.append(f"{proxy}:{username}:{password}")

        return formatted

    @staticmethod
    async def extend_proxy_purchase(
            db: AsyncSession,
            purchase_id: int,
            user: User,
            days: int
    ) -> ProxyPurchase:
        """Продление прокси"""
        try:
            purchase = await proxy_purchase_crud.get_user_purchase(
                db, purchase_id=purchase_id, user_id=user.id
            )

            if not purchase:
                raise BusinessLogicError("Proxy purchase not found")

            # Продлеваем у провайдера
            if purchase.provider_order_id:
                await proxy_711_api.extend_proxies(
                    purchase.provider_order_id,
                    days
                )

            # Обновляем дату истечения
            new_expires_at = purchase.expires_at + timedelta(days=days)
            updated_purchase = await proxy_purchase_crud.update_expiry(
                db,
                purchase=purchase,
                new_expires_at=new_expires_at
            )

            logger.info(f"Extended proxy purchase {purchase_id} by {days} days")
            return updated_purchase

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error extending proxy purchase: {e}")
            raise BusinessLogicError(f"Failed to extend proxies: {str(e)}")

    @staticmethod
    async def get_expiring_proxies(
            db: AsyncSession,
            user: User,
            days_ahead: int = 7
    ) -> List[ProxyPurchase]:
        """Получение прокси, которые скоро истекают"""
        expiry_date = datetime.now() + timedelta(days=days_ahead)
        return await proxy_purchase_crud.get_expiring_purchases(
            db,
            user_id=user.id,
            expiry_date=expiry_date
        )

    # Реализация абстрактных методов BaseService
    async def create(self, db: AsyncSession, obj_in: dict) -> ProxyPurchase:
        return await proxy_purchase_crud.create(db, obj_in=obj_in)

    async def get(self, db: AsyncSession, obj_id: int) -> Optional[ProxyPurchase]:
        return await proxy_purchase_crud.get(db, obj_id=obj_id)

    async def update(self, db: AsyncSession, db_obj: ProxyPurchase, obj_in: dict) -> ProxyPurchase:
        return await proxy_purchase_crud.update(db, db_obj=db_obj, obj_in=obj_in)

    async def delete(self, db: AsyncSession, obj_id: int) -> bool:
        await proxy_purchase_crud.remove(db, obj_id=obj_id)
        return True

    async def get_multi(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[ProxyPurchase]:
        return await proxy_purchase_crud.get_multi(db, skip=skip, limit=limit)


proxy_service = ProxyService()
