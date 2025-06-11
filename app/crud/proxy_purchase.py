"""
CRUD операции для покупок прокси.

Содержит методы для управления приобретенными пользователями прокси,
отслеживания использования и срока действия.
"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional, Dict, Any

from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.models import ProxyPurchase, ProxyProduct, Order, User
from app.schemas.proxy_purchase import (
    ProxyPurchaseCreate, ProxyPurchaseUpdate, ProxyStatsRequest,
    ProxyBulkActionRequest
)

logger = logging.getLogger(__name__)


class CRUDProxyPurchase(CRUDBase[ProxyPurchase, ProxyPurchaseCreate, ProxyPurchaseUpdate]):
    """
    CRUD для управления покупками прокси.

    Обеспечивает создание, обновление и отслеживание приобретенных прокси,
    включая управление сроками действия и статистикой использования.
    """

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
    ) -> Optional[ProxyPurchase]:
        """
        Создание покупки прокси - КЛЮЧЕВОЕ для MVP.

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
            if expires_at <= datetime.now(timezone.utc):
                logger.warning(f"Invalid expiry date for purchase: {expires_at}")
                raise ValueError("Expiry date must be in the future")

            # Проверяем существование пользователя, продукта и заказа
            user = await db.get(User, user_id)
            if not user:
                raise ValueError("User not found")

            product = await db.get(ProxyProduct, proxy_product_id)
            if not product:
                raise ValueError("Product not found")

            order = await db.get(Order, order_id)
            if not order:
                raise ValueError("Order not found")

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
                traffic_used_gb=Decimal('0.00000000'),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )

            db.add(purchase)
            await db.commit()
            await db.refresh(purchase)

            logger.info(f"Created proxy purchase {purchase.id} for user {user_id}")
            return purchase

        except ValueError:
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating proxy purchase: {e}")
            return None

    async def get_user_purchase(
        self,
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
                .options(
                    selectinload(ProxyPurchase.proxy_product),
                    selectinload(ProxyPurchase.order),
                    selectinload(ProxyPurchase.user)
                )
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

    async def get_user_purchases(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100
    ) -> List[ProxyPurchase]:
        """
        Получение покупок прокси пользователя - КЛЮЧЕВОЕ для раздела "Мои покупки".

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
                current_time = datetime.now(timezone.utc)
                query = query.where(
                    and_(
                        ProxyPurchase.is_active.is_(True),
                        ProxyPurchase.expires_at > current_time
                    )
                )

            query = query.order_by(desc(ProxyPurchase.created_at)).offset(skip).limit(limit)
            result = await db.execute(query)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error getting purchases for user {user_id}: {e}")
            return []

    async def get_expiring_purchases(
        self,
        db: AsyncSession,
        *,
        user_id: Optional[int] = None,
        days_ahead: int = 7
    ) -> List[ProxyPurchase]:
        """
        Получение истекающих покупок - для уведомлений о продлении.

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

            current_time = datetime.now(timezone.utc)
            expiry_date = current_time + timedelta(days=days_ahead)

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

    async def get_expired_purchases(
        self,
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
            expiry_threshold = datetime.now(timezone.utc) - timedelta(hours=hours_since_expiry)

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

    async def update_expiry(
        self,
        db: AsyncSession,
        *,
        purchase: ProxyPurchase,
        new_expires_at: datetime
    ) -> Optional[ProxyPurchase]:
        """
        Обновление даты истечения покупки - КЛЮЧЕВОЕ для продления услуг.

        Args:
            db: Сессия базы данных
            purchase: Покупка для обновления
            new_expires_at: Новая дата истечения

        Returns:
            Optional[ProxyPurchase]: Обновленная покупка или None
        """
        try:
            if new_expires_at <= datetime.now(timezone.utc):
                logger.warning(f"Invalid new expiry date: {new_expires_at}")
                raise ValueError("New expiry date must be in the future")

            old_expiry = purchase.expires_at
            purchase.expires_at = new_expires_at
            purchase.updated_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(purchase)

            logger.info(f"Updated expiry for purchase {purchase.id}: {old_expiry} -> {new_expires_at}")
            return purchase

        except ValueError:
            await db.rollback()
            raise
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
            purchase = await self.get(db, id=purchase_id)
            if not purchase:
                return None

            if traffic_used_gb < 0:
                logger.warning(f"Invalid traffic usage: {traffic_used_gb}")
                raise ValueError("Traffic usage cannot be negative")

            purchase.traffic_used_gb = traffic_used_gb
            purchase.last_used = datetime.now(timezone.utc)
            purchase.updated_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(purchase)

            logger.debug(f"Updated traffic usage for purchase {purchase_id}: {traffic_used_gb} GB")
            return purchase

        except ValueError:
            await db.rollback()
            raise
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
            purchase = await self.get(db, id=purchase_id)
            if not purchase:
                raise ValueError("Purchase not found")

            purchase.is_active = False
            purchase.updated_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(purchase)

            logger.info(f"Deactivated purchase {purchase_id}, reason: {reason}")
            return purchase

        except ValueError:
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error deactivating purchase {purchase_id}: {e}")
            return None

    async def get_proxy_list_formatted(
        self,
        db: AsyncSession,
        *,
        purchase_id: int,
        user_id: int,
        format_type: str = "ip:port:user:pass"
    ) -> Dict[str, Any]:
        """
        Получение отформатированного списка прокси - КЛЮЧЕВОЕ для генерации прокси.

        Args:
            db: Сессия базы данных
            purchase_id: ID покупки
            user_id: ID пользователя
            format_type: Формат вывода прокси

        Returns:
            Dict[str, Any]: Отформатированный список прокси
        """
        try:
            purchase = await self.get_user_purchase(db, purchase_id=purchase_id, user_id=user_id)
            if not purchase:
                return {
                    "success": False,
                    "message": "Purchase not found",
                    "proxies": []
                }

            if not purchase.is_active or purchase.expires_at <= datetime.now(timezone.utc):
                return {
                    "success": False,
                    "message": "Purchase is not active or expired",
                    "proxies": []
                }

            # Парсим список прокси
            proxy_lines = purchase.proxy_list.strip().split('\n')
            formatted_proxies = []

            for line in proxy_lines:
                line = line.strip()
                if not line:
                    continue

                try:
                    # Предполагаем формат ip:port:user:pass
                    parts = line.split(':')
                    if len(parts) >= 2:
                        ip = parts[0]
                        port = parts[1]
                        username = purchase.username or (parts[2] if len(parts) > 2 else "")
                        password = purchase.password or (parts[3] if len(parts) > 3 else "")

                        # Форматируем согласно запросу
                        if format_type == "ip:port":
                            formatted_proxies.append(f"{ip}:{port}")
                        elif format_type == "ip:port:user:pass":
                            formatted_proxies.append(f"{ip}:{port}:{username}:{password}")
                        elif format_type == "user:pass@ip:port":
                            formatted_proxies.append(f"{username}:{password}@{ip}:{port}")
                        elif format_type == "https://user:pass@ip:port":
                            formatted_proxies.append(f"https://{username}:{password}@{ip}:{port}")
                        elif format_type == "socks5://user:pass@ip:port":
                            formatted_proxies.append(f"socks5://{username}:{password}@{ip}:{port}")
                        else:
                            formatted_proxies.append(f"{ip}:{port}:{username}:{password}")

                except Exception as e:
                    logger.warning(f"Error formatting proxy line '{line}': {e}")
                    continue

            return {
                "success": True,
                "purchase_id": purchase_id,
                "proxy_count": len(formatted_proxies),
                "format": format_type,
                "proxies": formatted_proxies,
                "expires_at": purchase.expires_at.isoformat(),
                "product_name": purchase.proxy_product.name if purchase.proxy_product else "Unknown"
            }

        except Exception as e:
            logger.error(f"Error getting formatted proxy list: {e}")
            return {
                "success": False,
                "message": f"Error formatting proxies: {str(e)}",
                "proxies": []
            }

    async def extend_purchase(
        self,
        db: AsyncSession,
        *,
        purchase_id: int,
        user_id: int,
        extend_days: int
    ) -> Dict[str, Any]:
        """
        Продление покупки прокси - КЛЮЧЕВОЕ для продления услуг.

        Args:
            db: Сессия базы данных
            purchase_id: ID покупки
            user_id: ID пользователя
            extend_days: Количество дней для продления

        Returns:
            Dict[str, Any]: Результат продления
        """
        try:
            if extend_days <= 0 or extend_days > 365:
                raise ValueError("Extension days must be between 1 and 365")

            purchase = await self.get_user_purchase(db, purchase_id=purchase_id, user_id=user_id)
            if not purchase:
                return {
                    "success": False,
                    "message": "Purchase not found"
                }

            if not purchase.proxy_product:
                return {
                    "success": False,
                    "message": "Product information not available"
                }

            # Рассчитываем стоимость продления
            daily_cost = purchase.proxy_product.price_per_proxy / purchase.proxy_product.duration_days
            extension_cost = daily_cost * extend_days

            # Проверяем баланс пользователя
            user = await db.get(User, user_id)
            if not user or user.balance < extension_cost:
                return {
                    "success": False,
                    "message": f"Insufficient balance. Required: ${extension_cost:.2f}, Available: ${user.balance:.2f}"
                }

            # Продлеваем покупку
            new_expires_at = purchase.expires_at + timedelta(days=extend_days)
            updated_purchase = await self.update_expiry(db, purchase=purchase, new_expires_at=new_expires_at)

            if not updated_purchase:
                return {
                    "success": False,
                    "message": "Failed to extend purchase"
                }

            # Списываем средства с баланса
            user.balance -= extension_cost
            user.updated_at = datetime.now(timezone.utc)
            await db.commit()

            logger.info(f"Extended purchase {purchase_id} by {extend_days} days for ${extension_cost}")

            return {
                "success": True,
                "purchase_id": purchase_id,
                "extended_days": extend_days,
                "cost": str(extension_cost),
                "new_expires_at": updated_purchase.expires_at.isoformat(),
                "remaining_balance": str(user.balance)
            }

        except ValueError as e:
            return {
                "success": False,
                "message": str(e)
            }
        except Exception as e:
            await db.rollback()
            logger.error(f"Error extending purchase {purchase_id}: {e}")
            return {
                "success": False,
                "message": f"Extension failed: {str(e)}"
            }

    async def get_purchases_stats(
        self,
        db: AsyncSession,
        *,
        user_id: Optional[int] = None,
        stats_request: Optional[ProxyStatsRequest] = None
    ) -> Dict[str, Any]:
        """
        Получение статистики покупок.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя (опционально)
            stats_request: Параметры статистики

        Returns:
            Dict[str, Any]: Статистика покупок
        """
        try:
            if stats_request is None:
                stats_request = ProxyStatsRequest()

            start_date = datetime.now(timezone.utc) - timedelta(days=stats_request.period_days)
            current_time = datetime.now(timezone.utc)

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
                            ProxyPurchase.expires_at > current_time
                        )
                    ).subquery()
                )
            )
            active_purchases = active_result.scalar() or 0

            # Истекшие покупки
            expired_result = await db.execute(
                select(func.count(ProxyPurchase.id))
                .select_from(
                    base_query.where(
                        ProxyPurchase.expires_at <= current_time
                    ).subquery()
                )
            )
            expired_purchases = expired_result.scalar() or 0

            # Истекающие в ближайшие 7 дней
            expiring_date = current_time + timedelta(days=7)
            expiring_result = await db.execute(
                select(func.count(ProxyPurchase.id))
                .select_from(
                    base_query.where(
                        and_(
                            ProxyPurchase.is_active.is_(True),
                            ProxyPurchase.expires_at > current_time,
                            ProxyPurchase.expires_at <= expiring_date
                        )
                    ).subquery()
                )
            )
            expiring_soon = expiring_result.scalar() or 0

            # Общий использованный трафик
            traffic_result = await db.execute(
                select(func.sum(ProxyPurchase.traffic_used_gb))
                .select_from(base_query.subquery())
            )
            total_traffic = traffic_result.scalar() or Decimal('0.00000000')

            # Статистика по продуктам
            product_stats_result = await db.execute(
                select(
                    ProxyProduct.name,
                    func.count(ProxyPurchase.id).label('count'),
                    func.sum(ProxyPurchase.traffic_used_gb).label('traffic')
                )
                .select_from(
                    base_query
                    .join(ProxyProduct, ProxyPurchase.proxy_product_id == ProxyProduct.id)
                    .subquery()
                )
                .group_by(ProxyProduct.name)
            )
            product_stats = {
                name: {"count": count, "traffic": str(traffic or Decimal('0.00000000'))}
                for name, count, traffic in product_stats_result.all()
            }

            return {
                "total_purchases": total_purchases,
                "active_purchases": active_purchases,
                "expired_purchases": expired_purchases,
                "expiring_soon": expiring_soon,
                "total_traffic_gb": str(total_traffic),
                "product_breakdown": product_stats,
                "period_days": stats_request.period_days
            }

        except Exception as e:
            logger.error(f"Error getting purchases stats: {e}")
            return {
                "total_purchases": 0,
                "active_purchases": 0,
                "expired_purchases": 0,
                "expiring_soon": 0,
                "total_traffic_gb": "0.00000000",
                "product_breakdown": {},
                "period_days": 30
            }

    async def bulk_action(
        self,
        db: AsyncSession,
        *,
        bulk_request: ProxyBulkActionRequest
    ) -> Dict[str, Any]:
        """
        Массовые операции с покупками.

        Args:
            db: Сессия базы данных
            bulk_request: Запрос массовой операции

        Returns:
            Dict[str, Any]: Результат операции
        """
        try:
            processed = 0
            errors = []

            if bulk_request.action == "deactivate":
                for purchase_id in bulk_request.purchase_ids:
                    try:
                        await self.deactivate_purchase(db, purchase_id=purchase_id)
                        processed += 1
                    except Exception as e:
                        errors.append(f"Purchase {purchase_id}: {str(e)}")

            elif bulk_request.action == "extend":
                if not bulk_request.extend_days:
                    raise ValueError("extend_days is required for extend action")

                for purchase_id in bulk_request.purchase_ids:
                    try:
                        purchase = await self.get(db, id=purchase_id)
                        if purchase:
                            new_expiry = purchase.expires_at + timedelta(days=bulk_request.extend_days)
                            await self.update_expiry(db, purchase=purchase, new_expires_at=new_expiry)
                            processed += 1
                    except Exception as e:
                        errors.append(f"Purchase {purchase_id}: {str(e)}")

            return {
                "success": True,
                "processed": processed,
                "total": len(bulk_request.purchase_ids),
                "errors": errors
            }

        except Exception as e:
            logger.error(f"Error in bulk action: {e}")
            return {
                "success": False,
                "processed": 0,
                "total": len(bulk_request.purchase_ids),
                "errors": [str(e)]
            }

    async def cleanup_expired_purchases(self, db: AsyncSession) -> int:
        """
        Очистка просроченных покупок.

        Args:
            db: Сессия базы данных

        Returns:
            int: Количество деактивированных покупок
        """
        try:
            expired_purchases = await self.get_expired_purchases(db, hours_since_expiry=24)

            if not expired_purchases:
                return 0

            deactivated = 0
            for purchase in expired_purchases:
                try:
                    await self.deactivate_purchase(
                        db,
                        purchase_id=purchase.id,
                        reason="Automatic deactivation - expired"
                    )
                    deactivated += 1
                except Exception as e:
                    logger.error(f"Error deactivating expired purchase {purchase.id}: {e}")

            logger.info(f"Cleaned up {deactivated} expired purchases")
            return deactivated

        except Exception as e:
            logger.error(f"Error cleaning up expired purchases: {e}")
            return 0

    async def get_purchase_by_provider_order_id(
        self,
        db: AsyncSession,
        *,
        provider_order_id: str
    ) -> Optional[ProxyPurchase]:
        """
        Получение покупки по ID заказа провайдера - для интеграции с 711.

        Args:
            db: Сессия базы данных
            provider_order_id: ID заказа у провайдера

        Returns:
            Optional[ProxyPurchase]: Найденная покупка или None
        """
        try:
            result = await db.execute(
                select(ProxyPurchase)
                .options(selectinload(ProxyPurchase.proxy_product))
                .where(ProxyPurchase.provider_order_id == provider_order_id)
            )
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error getting purchase by provider order ID {provider_order_id}: {e}")
            return None

    async def sync_with_provider(
        self,
        db: AsyncSession,
        *,
        purchase_id: int,
        provider_data: Dict[str, Any]
    ) -> Optional[ProxyPurchase]:
        """
        Синхронизация покупки с данными провайдера.

        Args:
            db: Сессия базы данных
            purchase_id: ID покупки
            provider_data: Данные от провайдера

        Returns:
            Optional[ProxyPurchase]: Обновленная покупка или None
        """
        try:
            purchase = await self.get(db, id=purchase_id)
            if not purchase:
                return None

            # Обновляем данные от провайдера
            if 'proxy_list' in provider_data:
                purchase.proxy_list = provider_data['proxy_list']

            if 'expires_at' in provider_data:
                purchase.expires_at = provider_data['expires_at']

            if 'traffic_used_gb' in provider_data:
                purchase.traffic_used_gb = Decimal(str(provider_data['traffic_used_gb']))

            if 'is_active' in provider_data:
                purchase.is_active = provider_data['is_active']

            if 'provider_metadata' in provider_data:
                purchase.provider_metadata = provider_data['provider_metadata']

            purchase.updated_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(purchase)

            logger.info(f"Synced purchase {purchase_id} with provider data")
            return purchase

        except Exception as e:
            await db.rollback()
            logger.error(f"Error syncing purchase {purchase_id} with provider: {e}")
            return None

    async def get_user_active_proxies_count(
        self,
        db: AsyncSession,
        *,
        user_id: int
    ) -> int:
        """
        Получение количества активных прокси пользователя.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя

        Returns:
            int: Количество активных прокси
        """
        try:
            current_time = datetime.now(timezone.utc)

            result = await db.execute(
                select(func.count(ProxyPurchase.id))
                .where(
                    and_(
                        ProxyPurchase.user_id == user_id,
                        ProxyPurchase.is_active.is_(True),
                        ProxyPurchase.expires_at > current_time
                    )
                )
            )
            return result.scalar() or 0

        except Exception as e:
            logger.error(f"Error getting active proxies count for user {user_id}: {e}")
            return 0


proxy_purchase_crud = CRUDProxyPurchase(ProxyPurchase)
