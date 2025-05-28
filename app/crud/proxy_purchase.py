from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime

from app.crud.base import CRUDBase
from app.models.models import ProxyPurchase
from app.schemas.proxy_purchase import ProxyPurchaseCreate, ProxyPurchaseUpdate


class CRUDProxyPurchase(CRUDBase[ProxyPurchase, ProxyPurchaseCreate, ProxyPurchaseUpdate]):

    @staticmethod
    async def create_purchase(
            db: AsyncSession,
            *,
            user_id: int,
            proxy_product_id: int,
            order_id: int,
            proxy_list: List[str],
            username: str = None,
            password: str = None,
            expires_at: datetime,
            provider_order_id: str = None
    ) -> ProxyPurchase:
        """Создание записи о покупке прокси"""

        # Конвертируем список прокси в строку
        proxy_list_str = "\n".join(proxy_list) if isinstance(proxy_list, list) else str(proxy_list)

        purchase = ProxyPurchase(
            user_id=user_id,
            proxy_product_id=proxy_product_id,
            order_id=order_id,
            proxy_list=proxy_list_str,
            username=username,
            password=password,
            expires_at=expires_at,
            provider_order_id=provider_order_id,
            is_active=True
        )

        db.add(purchase)
        await db.commit()
        await db.refresh(purchase)
        return purchase

    @staticmethod
    async def get_user_purchases(
            db: AsyncSession,
            *,
            user_id: int,
            active_only: bool = True
    ) -> List[ProxyPurchase]:
        """Получение покупок прокси пользователя"""
        query = select(ProxyPurchase).where(ProxyPurchase.user_id == user_id)

        if active_only:
            query = query.where(
                and_(
                    ProxyPurchase.is_active.is_(True),
                    ProxyPurchase.expires_at > datetime.now()
                )
            )

        result = await db.execute(query.order_by(ProxyPurchase.created_at.desc()))
        return list(result.scalars().all())

    @staticmethod
    async def get_user_purchase(
            db: AsyncSession,
            *,
            purchase_id: int,
            user_id: int
    ) -> Optional[ProxyPurchase]:
        """Получение конкретной покупки пользователя"""
        result = await db.execute(
            select(ProxyPurchase).where(
                and_(
                    ProxyPurchase.id == purchase_id,
                    ProxyPurchase.user_id == user_id
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_expiry(
            db: AsyncSession,
            *,
            purchase: ProxyPurchase,
            new_expires_at: datetime
    ) -> ProxyPurchase:
        """Обновление даты истечения"""
        purchase.expires_at = new_expires_at
        purchase.updated_at = datetime.now()

        await db.commit()
        await db.refresh(purchase)
        return purchase

    @staticmethod
    async def get_expiring_purchases(
            db: AsyncSession,
            *,
            user_id: int,
            expiry_date: datetime
    ) -> List[ProxyPurchase]:
        """Получение истекающих покупок"""
        result = await db.execute(
            select(ProxyPurchase).where(
                and_(
                    ProxyPurchase.user_id == user_id,
                    ProxyPurchase.is_active.is_(True),
                    ProxyPurchase.expires_at <= expiry_date,
                    ProxyPurchase.expires_at > datetime.now()
                )
            ).order_by(ProxyPurchase.expires_at)
        )
        return list(result.scalars().all())


proxy_purchase_crud = CRUDProxyPurchase(ProxyPurchase)
