import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessLogicError
from app.crud.proxy_purchase import proxy_purchase_crud
from app.models.models import User, ProxyPurchase, Order
from app.schemas.proxy_purchase import ProxyPurchaseCreate, ProxyPurchaseUpdate
from app.services.base import BaseService, BusinessRuleValidator

logger = logging.getLogger(__name__)


class ProxyBusinessRules(BusinessRuleValidator):
    """Валидатор бизнес-правил для прокси"""

    async def validate(self, data: dict, db: AsyncSession) -> bool:
        """Валидация правил прокси"""
        return True


class ProxyService(BaseService[ProxyPurchase, ProxyPurchaseCreate, ProxyPurchaseUpdate]):
    """Сервис для работы с прокси"""

    def __init__(self):
        super().__init__(ProxyPurchase)
        self.crud = proxy_purchase_crud
        self.business_rules = ProxyBusinessRules()

    async def get_user_proxies(
            self,
            db: AsyncSession,
            user: User,
            active_only: bool = True
    ) -> List[ProxyPurchase]:
        """Получение прокси пользователя"""
        try:
            return await self.crud.get_user_purchases(
                db,
                user_id=user.id,
                active_only=active_only
            )
        except Exception as e:
            logger.error(f"Error getting user proxies: {e}")
            return []

    async def generate_proxy_list(
            self,
            db: AsyncSession,
            purchase_id: int,
            user: User,
            format_type: str = "ip:port:user:pass"
    ) -> Dict[str, Any]:
        """Генерация списка прокси"""
        try:
            purchase = await self.crud.get_user_purchase(
                db, purchase_id=purchase_id, user_id=user.id
            )

            if not purchase:
                raise BusinessLogicError("Proxy purchase not found")

            if not purchase.is_active:
                raise BusinessLogicError("Proxy purchase is not active")

            if purchase.expires_at < datetime.now():
                raise BusinessLogicError("Proxy purchase has expired")

            # Парсим список прокси
            proxy_lines = purchase.proxy_list.strip().split('\n')
            formatted_proxies = []

            for line in proxy_lines:
                if line.strip():
                    formatted_proxies.append(self._format_proxy_line(line.strip(), format_type))

            return {
                "purchase_id": purchase_id,
                "proxy_count": len(formatted_proxies),
                "format": format_type,
                "proxies": formatted_proxies,
                "expires_at": purchase.expires_at
            }

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error generating proxy list: {e}")
            raise BusinessLogicError(f"Failed to generate proxy list: {str(e)}")

    async def extend_proxy_purchase(
            self,
            db: AsyncSession,
            purchase_id: int,
            user: User,
            days: int
    ) -> ProxyPurchase:
        """Продление прокси"""
        try:
            purchase = await self.crud.get_user_purchase(
                db, purchase_id=purchase_id, user_id=user.id
            )

            if not purchase:
                raise BusinessLogicError("Proxy purchase not found")

            # Продлеваем срок действия
            new_expires_at = purchase.expires_at + timedelta(days=days)

            # Обновляем в базе
            update_data = ProxyPurchaseUpdate(expires_at=new_expires_at)
            updated_purchase = await self.crud.update(db, db_obj=purchase, obj_in=update_data)

            logger.info(f"Extended proxy purchase {purchase_id} by {days} days")
            return updated_purchase

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error extending proxy purchase: {e}")
            raise BusinessLogicError(f"Failed to extend proxy purchase: {str(e)}")

    async def get_expiring_proxies(
            self,
            db: AsyncSession,
            user: User,
            days_ahead: int = 7
    ) -> List[ProxyPurchase]:
        """Получение истекающих прокси"""
        try:
            return await self.crud.get_expiring_purchases(
                db,
                user_id=user.id,
                days_ahead=days_ahead
            )
        except Exception as e:
            logger.error(f"Error getting expiring proxies: {e}")
            return []

    async def get_user_proxy_stats(
            self,
            db: AsyncSession,
            user: User
    ) -> Dict[str, Any]:
        """Получение статистики прокси пользователя"""
        try:
            all_purchases = await self.crud.get_user_purchases(
                db, user_id=user.id, active_only=False
            )

            active_purchases = [p for p in all_purchases if p.is_active and p.expires_at > datetime.now()]
            expired_purchases = [p for p in all_purchases if p.expires_at <= datetime.now()]

            total_traffic = sum(p.traffic_used_gb for p in all_purchases)

            return {
                "total_proxies": len(all_purchases),
                "active_proxies": len(active_purchases),
                "expired_proxies": len(expired_purchases),
                "total_traffic_gb": str(total_traffic)
            }

        except Exception as e:
            logger.error(f"Error getting proxy stats: {e}")
            return {
                "total_proxies": 0,
                "active_proxies": 0,
                "expired_proxies": 0,
                "total_traffic_gb": "0.00"
            }

    async def activate_proxies_for_order(
            self,
            db: AsyncSession,
            order: Order
    ) -> List[ProxyPurchase]:
        """Активация прокси для заказа"""
        try:
            logger.info(f"Activating proxies for order {order.id}")

            # Получаем все покупки прокси для этого заказа
            from sqlalchemy import select
            result = await db.execute(
                select(ProxyPurchase).where(ProxyPurchase.order_id == order.id)
            )
            purchases = list(result.scalars().all())

            # Активируем каждую покупку
            for purchase in purchases:
                purchase.is_active = True
                await db.commit()

            logger.info(f"Activated {len(purchases)} proxy purchases for order {order.id}")
            return purchases

        except Exception as e:
            logger.error(f"Error activating proxies for order {order.id}: {e}")
            return []

    def _format_proxy_list(
            self,
            proxy_list: str,
            username: str,
            password: str,
            format_type: str
    ) -> List[str]:
        """Форматирование списка прокси"""
        lines = proxy_list.strip().split('\n')
        formatted_lines = []

        for line in lines:
            if line.strip():
                if format_type == "ip:port:user:pass":
                    formatted_lines.append(f"{line.strip()}:{username}:{password}")
                elif format_type == "user:pass@ip:port":
                    formatted_lines.append(f"{username}:{password}@{line.strip()}")
                else:  # ip:port
                    formatted_lines.append(line.strip())

        return formatted_lines

    @staticmethod
    def _format_proxy_line(proxy_line: str, format_type: str) -> str:
        """Форматирование строки прокси"""
        if format_type == "ip:port:user:pass":
            if ":" in proxy_line and len(proxy_line.split(":")) == 2:
                return f"{proxy_line}:user123:pass123"
            return proxy_line
        elif format_type == "user:pass@ip:port":
            if ":" in proxy_line and len(proxy_line.split(":")) == 2:
                return f"user123:pass123@{proxy_line}"
            return proxy_line
        else:
            return proxy_line

    # Реализация абстрактных методов BaseService
    async def create(self, db: AsyncSession, obj_in: ProxyPurchaseCreate) -> ProxyPurchase:
        return await self.crud.create(db, obj_in=obj_in)

    async def get(self, db: AsyncSession, obj_id: int) -> Optional[ProxyPurchase]:
        return await self.crud.get(db, obj_id=obj_id)

    async def update(self, db: AsyncSession, db_obj: ProxyPurchase, obj_in: ProxyPurchaseUpdate) -> ProxyPurchase:
        return await self.crud.update(db, db_obj=db_obj, obj_in=obj_in)

    async def delete(self, db: AsyncSession, obj_id: int) -> bool:
        await self.crud.remove(db, obj_id=obj_id)
        return True

    async def get_multi(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[ProxyPurchase]:
        return await self.crud.get_multi(db, skip=skip, limit=limit)


proxy_service = ProxyService()
