"""
CRUD операции для покупок прокси.

Содержит методы для управления приобретенными пользователями прокси,
отслеживания использования и срока действия.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from decimal import Decimal

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.models import ProxyPurchase, ProxyProduct
from app.schemas.proxy_purchase import ProxyPurchaseCreate, ProxyPurchaseUpdate

logger = logging.getLogger(__name__)


class CRUDProxyPurchase(CRUDBase[ProxyPurchase, ProxyPurchaseCreate, ProxyPurchaseUpdate]):
    """
    CRUD для управления покупками прокси.

    Обеспечивает создание, обновление и отслеживание приобретенных прокси,
    включая управление сроками действия и статистикой использования.
    """

    @staticmethod
    async def create_purchase(
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
    ) -> Optional[ProxyPurchase]:
        """
        Создание покупки прокси.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            proxy_product_id: ID продукта прокси
            order_id: ID заказа
            proxy_list: Список прокси (строка или JSON)
            username: Имя пользователя для прокси
            password: Пароль для прокси
            expires_at: Дата истечения
            provider_order_id: ID заказа у провайдера
            provider_metadata: Метаданные провайдера

        Returns:
            Optional[ProxyPurchase]: Созданная покупка или None
        """
        try:
            # Валидация входных данных
            if expires_at <= datetime.now():
                logger.warning(f"Invalid expiry date for purchase: {expires_at}")
                return None

            # Если proxy_list это список, преобразуем в строку
            if isinstance(proxy_list, list):
                proxy_list = "\n".join(str(proxy) for proxy in proxy_list)

            # Создаем объект покупки
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
                is_active=True,
                traffic_used_gb=Decimal('0.00')
            )

            db.add(purchase)
            await db.commit()
            await db.refresh(purchase)

            logger.info(f"Created proxy purchase {purchase.id} for user {user_id}")
            return purchase

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating proxy purchase: {e}")
            return None

    @staticmethod
    async def get_user_purchase(
            db: AsyncSession,
        *,
        purchase_id: int,
        user_id: int
    ) -> Optional[ProxyPurchase]:
        """
        Получение конкретной покупки пользователя.

        Args:
            db: Сессия базы данных
            purchase_id: ID покупки
            user_id: ID пользователя

        Returns:
            Optional[ProxyPurchase]: Покупка пользователя или None
        """
        try:
            result = await db.execute(
                select(ProxyPurchase)
                .options(selectinload(ProxyPurchase.proxy_product))
                .where(
                    and_(
                        ProxyPurchase.id == purchase_id,
                        ProxyPurchase.user_id == user_id
                    )
                )
            )
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error getting user purchase {purchase_id} for user {user_id}: {e}")
            return None

    @staticmethod
    async def get_user_purchases(
            db: AsyncSession,
        *,
        user_id: int,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100
    ) -> List[ProxyPurchase]:
        """
        Получение покупок прокси пользователя.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            active_only: Только активные покупки
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            List[ProxyPurchase]: Список покупок пользователя
        """
        try:
            query = (
                select(ProxyPurchase)
                .options(selectinload(ProxyPurchase.proxy_product))
                .where(ProxyPurchase.user_id == user_id)
            )

            if active_only:
                query = query.where(
                    and_(
                        ProxyPurchase.is_active.is_(True),
                        ProxyPurchase.expires_at > datetime.now()
                    )
                )

            query = query.order_by(ProxyPurchase.created_at.desc()).offset(skip).limit(limit)
            result = await db.execute(query)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error getting purchases for user {user_id}: {e}")
            return []

    @staticmethod
    async def get_expiring_purchases(
            db: AsyncSession,
        *,
        user_id: Optional[int] = None,
        days_ahead: int = 7
    ) -> List[ProxyPurchase]:
        """
        Получение истекающих покупок.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя (опционально)
            days_ahead: За сколько дней предупреждать об истечении

        Returns:
            List[ProxyPurchase]: Список истекающих покупок
        """
        try:
            if days_ahead <= 0:
                days_ahead = 7

            expiry_date = datetime.now() + timedelta(days=days_ahead)
            current_time = datetime.now()

            query = select(ProxyPurchase).where(
                and_(
                    ProxyPurchase.is_active.is_(True),
                    ProxyPurchase.expires_at <= expiry_date,
                    ProxyPurchase.expires_at > current_time
                )
            )

            if user_id:
                query = query.where(ProxyPurchase.user_id == user_id)

            query = query.order_by(ProxyPurchase.expires_at.asc())
            result = await db.execute(query)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error getting expiring purchases: {e}")
            return []

    @staticmethod
    async def get_expired_purchases(
            db: AsyncSession,
        *,
        hours_since_expiry: int = 24
    ) -> List[ProxyPurchase]:
        """
        Получение просроченных покупок для очистки.

        Args:
            db: Сессия базы данных
            hours_since_expiry: Через сколько часов после истечения считать просроченным

        Returns:
            List[ProxyPurchase]: Список просроченных покупок
        """
        try:
            expiry_threshold = datetime.now() - timedelta(hours=hours_since_expiry)

            result = await db.execute(
                select(ProxyPurchase).where(
                    and_(
                        ProxyPurchase.is_active.is_(True),
                        ProxyPurchase.expires_at < expiry_threshold
                    )
                )
                .order_by(ProxyPurchase.expires_at.asc())
            )
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error getting expired purchases: {e}")
            return []

    @staticmethod
    async def update_expiry(
            db: AsyncSession,
        *,
        purchase: ProxyPurchase,
        new_expires_at: datetime
    ) -> Optional[ProxyPurchase]:
        """
        Обновление даты истечения покупки.

        Args:
            db: Сессия базы данных
            purchase: Покупка для обновления
            new_expires_at: Новая дата истечения

        Returns:
            Optional[ProxyPurchase]: Обновленная покупка или None
        """
        try:
            if new_expires_at <= datetime.now():
                logger.warning(f"Invalid new expiry date: {new_expires_at}")
                return None

            old_expiry = purchase.expires_at
            purchase.expires_at = new_expires_at
            purchase.updated_at = datetime.now()

            await db.commit()
            await db.refresh(purchase)

            logger.info(f"Updated expiry for purchase {purchase.id}: {old_expiry} -> {new_expires_at}")
            return purchase

        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating expiry for purchase {purchase.id}: {e}")
            return None

    async def update_traffic_usage(
        self,
        db: AsyncSession,
        *,
        purchase_id: int,
        traffic_used_gb: Decimal
    ) -> Optional[ProxyPurchase]:
        """
        Обновление использованного трафика.

        Args:
            db: Сессия базы данных
            purchase_id: ID покупки
            traffic_used_gb: Использованный трафик в ГБ

        Returns:
            Optional[ProxyPurchase]: Обновленная покупка или None
        """
        try:
            purchase = await self.get(db, obj_id=purchase_id)
            if not purchase:
                return None

            if traffic_used_gb < 0:
                logger.warning(f"Invalid traffic usage: {traffic_used_gb}")
                return None

            purchase.traffic_used_gb = traffic_used_gb
            purchase.last_used = datetime.now()
            purchase.updated_at = datetime.now()

            await db.commit()
            await db.refresh(purchase)

            logger.debug(f"Updated traffic usage for purchase {purchase_id}: {traffic_used_gb} GB")
            return purchase

        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating traffic usage for purchase {purchase_id}: {e}")
            return None

    async def deactivate_purchase(
        self,
        db: AsyncSession,
        *,
        purchase_id: int,
        reason: Optional[str] = None
    ) -> Optional[ProxyPurchase]:
        """
        Деактивация покупки.

        Args:
            db: Сессия базы данных
            purchase_id: ID покупки
            reason: Причина деактивации

        Returns:
            Optional[ProxyPurchase]: Деактивированная покупка или None
        """
        try:
            purchase = await self.get(db, obj_id=purchase_id)
            if not purchase:
                return None

            purchase.is_active = False
            purchase.updated_at = datetime.now()

            if reason:
                # Можно добавить поле для хранения причины деактивации
                pass

            await db.commit()
            await db.refresh(purchase)

            logger.info(f"Deactivated purchase {purchase_id}, reason: {reason}")
            return purchase

        except Exception as e:
            await db.rollback()
            logger.error(f"Error deactivating purchase {purchase_id}: {e}")
            return None

    @staticmethod
    async def get_purchases_stats(
            db: AsyncSession,
        *,
        user_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Получение статистики покупок.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя (опционально)
            days: Период для статистики в днях

        Returns:
            Dict[str, Any]: Статистика покупок
        """
        try:
            start_date = datetime.now() - timedelta(days=days)

            base_query = select(ProxyPurchase).where(ProxyPurchase.created_at >= start_date)
            if user_id:
                base_query = base_query.where(ProxyPurchase.user_id == user_id)

            # Общее количество покупок
            total_result = await db.execute(
                select(func.count(ProxyPurchase.id)).select_from(base_query.subquery())
            )
            total_purchases = total_result.scalar() or 0

            # Активные покупки
            active_result = await db.execute(
                select(func.count(ProxyPurchase.id))
                .select_from(
                    base_query.where(
                        and_(
                            ProxyPurchase.is_active.is_(True),
                            ProxyPurchase.expires_at > datetime.now()
                        )
                    ).subquery()
                )
            )
            active_purchases = active_result.scalar() or 0

            # Общий использованный трафик
            traffic_result = await db.execute(
                select(func.sum(ProxyPurchase.traffic_used_gb))
                .select_from(base_query.subquery())
            )
            total_traffic = traffic_result.scalar() or Decimal('0.00')

            # Покупки по продуктам
            product_stats_result = await db.execute(
                select(
                    ProxyProduct.name,
                    func.count(ProxyPurchase.id)
                )
                .select_from(
                    base_query
                    .join(ProxyProduct, ProxyPurchase.proxy_product_id == ProxyProduct.id)
                    .subquery()
                )
                .group_by(ProxyProduct.name)
            )
            product_stats = dict(product_stats_result.all())

            return {
                "total_purchases": total_purchases,
                "active_purchases": active_purchases,
                "total_traffic_used_gb": str(total_traffic),
                "product_breakdown": product_stats,
                "period_days": days
            }

        except Exception as e:
            logger.error(f"Error getting purchases stats: {e}")
            return {
                "total_purchases": 0,
                "active_purchases": 0,
                "total_traffic_used_gb": "0.00",
                "product_breakdown": {},
                "period_days": days
            }

    @staticmethod
    async def get_purchases_by_product(
            db: AsyncSession,
        *,
        proxy_product_id: int,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100
    ) -> List[ProxyPurchase]:
        """
        Получение покупок по продукту.

        Args:
            db: Сессия базы данных
            proxy_product_id: ID продукта прокси
            active_only: Только активные покупки
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            List[ProxyPurchase]: Список покупок продукта
        """
        try:
            query = select(ProxyPurchase).where(ProxyPurchase.proxy_product_id == proxy_product_id)

            if active_only:
                query = query.where(
                    and_(
                        ProxyPurchase.is_active.is_(True),
                        ProxyPurchase.expires_at > datetime.now()
                    )
                )

            query = query.order_by(ProxyPurchase.created_at.desc()).offset(skip).limit(limit)
            result = await db.execute(query)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error getting purchases for product {proxy_product_id}: {e}")
            return []


proxy_purchase_crud = CRUDProxyPurchase(ProxyPurchase)
