from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.models import ProxyPurchase
from app.schemas.proxy_purchase import ProxyPurchaseCreate, ProxyPurchaseUpdate


class CRUDProxyPurchase(CRUDBase[ProxyPurchase, ProxyPurchaseCreate, ProxyPurchaseUpdate]):

    async def create_purchase(
            self,
            db: AsyncSession,
            *,
            user_id: int,
            proxy_product_id: int,
            order_id: int,
            proxy_list: str,
            username: Optional[str] = None,
            password: Optional[str] = None,
            expires_at: datetime,
            provider_order_id: Optional[str] = None,
            provider_metadata: Optional[str] = None
    ) -> ProxyPurchase:
        """Создание покупки прокси"""
        # Если proxy_list это список, преобразуем в строку
        if isinstance(proxy_list, list):
            proxy_list = "\n".join(proxy_list)

        # Создаем объект напрямую, а не через схему
        purchase = ProxyPurchase(
            user_id=user_id,
            proxy_product_id=proxy_product_id,
            order_id=order_id,
            proxy_list=proxy_list,
            username=username,
            password=password,
            expires_at=expires_at,
            provider_order_id=provider_order_id,
            provider_metadata=provider_metadata,
            is_active=True
        )

        db.add(purchase)
        await db.commit()
        await db.refresh(purchase)
        return purchase

    async def get_user_purchase(
            self,
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

    async def get_user_purchases(
            self,
            db: AsyncSession,
            *,
            user_id: int,
            active_only: bool = True,
            skip: int = 0,
            limit: int = 100
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

        result = await db.execute(
            query.order_by(ProxyPurchase.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_expiring_purchases(
            self,
            db: AsyncSession,
            *,
            user_id: int,
            days_ahead: int = 7  # ИСПРАВЛЕНО: убрали expiry_date параметр
    ) -> List[ProxyPurchase]:
        """Получение истекающих покупок"""
        expiry_date = datetime.now() + timedelta(days=days_ahead)

        result = await db.execute(
            select(ProxyPurchase).where(
                and_(
                    ProxyPurchase.user_id == user_id,
                    ProxyPurchase.is_active.is_(True),
                    ProxyPurchase.expires_at <= expiry_date,
                    ProxyPurchase.expires_at > datetime.now()
                )
            ).order_by(ProxyPurchase.expires_at.asc())
        )
        return list(result.scalars().all())

    async def update_expiry(
            self,
            db: AsyncSession,
            *,
            purchase: ProxyPurchase,
            new_expires_at: datetime
    ) -> ProxyPurchase:
        """Обновление даты истечения"""
        purchase.expires_at = new_expires_at
        await db.commit()
        await db.refresh(purchase)
        return purchase


proxy_purchase_crud = CRUDProxyPurchase(ProxyPurchase)
