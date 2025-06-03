"""
CRUD операции для пополнений баланса.

Содержит методы для управления пополнениями баланса пользователей
через различные платежные системы, включая Cryptomus.
"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional, Dict, Any

from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.models import BalanceTopup, User, PaymentProvider, TransactionStatus

logger = logging.getLogger(__name__)


class BalanceTopupCreate:
    """Схема создания пополнения баланса."""
    def __init__(self, user_id: int, amount: Decimal, payment_provider: PaymentProvider,
                 provider_payment_id: Optional[str] = None, transaction_id: Optional[int] = None):
        self.user_id = user_id
        self.amount = amount
        self.payment_provider = payment_provider
        self.provider_payment_id = provider_payment_id
        self.transaction_id = transaction_id


class BalanceTopupUpdate:
    """Схема обновления пополнения баланса."""
    def __init__(self, status: Optional[TransactionStatus] = None,
                 provider_payment_id: Optional[str] = None, completed_at: Optional[datetime] = None):
        self.status = status
        self.provider_payment_id = provider_payment_id
        self.completed_at = completed_at


class CRUDBalanceTopup(CRUDBase[BalanceTopup, BalanceTopupCreate, BalanceTopupUpdate]):
    """
    CRUD для управления пополнениями баланса.

    Обеспечивает создание, отслеживание и обновление пополнений баланса
    через различные платежные системы.
    """

    async def create_topup(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        amount: Decimal,
        payment_provider: PaymentProvider = PaymentProvider.CRYPTOMUS,
        provider_payment_id: Optional[str] = None,
        transaction_id: Optional[int] = None
    ) -> Optional[BalanceTopup]:
        """
        Создание пополнения баланса - КЛЮЧЕВОЕ для MVP.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            amount: Сумма пополнения
            payment_provider: Платежный провайдер
            provider_payment_id: ID платежа у провайдера
            transaction_id: ID связанной транзакции

        Returns:
            Optional[BalanceTopup]: Созданное пополнение или None
        """
        try:
            if amount <= 0:
                raise ValueError("Amount must be positive")

            # Проверяем существование пользователя
            user = await db.get(User, user_id)
            if not user:
                raise ValueError("User not found")

            topup = BalanceTopup(
                user_id=user_id,
                transaction_id=transaction_id,
                amount=amount,
                currency="USD",
                payment_provider=payment_provider,
                provider_payment_id=provider_payment_id,
                status=TransactionStatus.PENDING,
                created_at=datetime.now(timezone.utc)
            )

            db.add(topup)
            await db.commit()
            await db.refresh(topup)

            logger.info(f"Created balance topup {topup.id} for user {user_id}: {amount}")
            return topup

        except ValueError:
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating balance topup: {e}")
            return None

    async def get_by_provider_payment_id(
        self,
        db: AsyncSession,
        *,
        provider_payment_id: str
    ) -> Optional[BalanceTopup]:
        """
        Получение пополнения по ID платежа провайдера - для Cryptomus webhook.

        Args:
            db: Сессия базы данных
            provider_payment_id: ID платежа у провайдера

        Returns:
            Optional[BalanceTopup]: Найденное пополнение или None
        """
        try:
            result = await db.execute(
                select(BalanceTopup)
                .where(BalanceTopup.provider_payment_id == provider_payment_id)
            )
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error getting topup by provider payment ID {provider_payment_id}: {e}")
            return None

    async def update_status(
        self,
        db: AsyncSession,
        *,
        topup: BalanceTopup,
        status: TransactionStatus
    ) -> Optional[BalanceTopup]:
        """
        Обновление статуса пополнения - для обработки webhook.

        Args:
            db: Сессия базы данных
            topup: Пополнение для обновления
            status: Новый статус

        Returns:
            Optional[BalanceTopup]: Обновленное пополнение или None
        """
        try:
            old_status = topup.status
            topup.status = status

            if status == TransactionStatus.COMPLETED:
                topup.completed_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(topup)

            logger.info(f"Updated topup {topup.id} status: {old_status} -> {status}")
            return topup

        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating topup status: {e}")
            return None

    async def get_user_topups(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[BalanceTopup]:
        """
        Получение пополнений пользователя - для истории баланса.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            skip: Пропустить записей
            limit: Максимум записей

        Returns:
            List[BalanceTopup]: Список пополнений
        """
        try:
            result = await db.execute(
                select(BalanceTopup)
                .options(selectinload(BalanceTopup.transaction))
                .where(BalanceTopup.user_id == user_id)
                .order_by(desc(BalanceTopup.created_at))
                .offset(skip)
                .limit(limit)
            )
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error getting topups for user {user_id}: {e}")
            return []

    async def get_pending_topups(
        self,
        db: AsyncSession,
        *,
        older_than_minutes: int = 30
    ) -> List[BalanceTopup]:
        """
        Получение зависших пополнений для проверки.

        Args:
            db: Сессия базы данных
            older_than_minutes: Возраст в минутах

        Returns:
            List[BalanceTopup]: Список зависших пополнений
        """
        try:
            threshold_time = datetime.now(timezone.utc) - timedelta(minutes=older_than_minutes)

            result = await db.execute(
                select(BalanceTopup)
                .where(
                    and_(
                        BalanceTopup.status == TransactionStatus.PENDING,
                        BalanceTopup.created_at < threshold_time
                    )
                )
                .order_by(BalanceTopup.created_at.asc())
            )
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error getting pending topups: {e}")
            return []

    async def get_topup_stats(
        self,
        db: AsyncSession,
        *,
        user_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Получение статистики пополнений.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя (опционально)
            days: Период в днях

        Returns:
            Dict[str, Any]: Статистика пополнений
        """
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)

            base_query = select(BalanceTopup).where(BalanceTopup.created_at >= start_date)
            if user_id:
                base_query = base_query.where(BalanceTopup.user_id == user_id)

            # Общее количество
            total_result = await db.execute(
                select(func.count(BalanceTopup.id)).select_from(base_query.subquery())
            )
            total_topups = total_result.scalar() or 0

            # Сумма завершенных пополнений
            completed_result = await db.execute(
                select(func.sum(BalanceTopup.amount))
                .select_from(
                    base_query.where(BalanceTopup.status == TransactionStatus.COMPLETED).subquery()
                )
            )
            total_amount = completed_result.scalar() or Decimal('0.00000000')

            # Количество по статусам
            status_stats = {}
            for status in TransactionStatus:
                status_result = await db.execute(
                    select(func.count(BalanceTopup.id))
                    .select_from(
                        base_query.where(BalanceTopup.status == status).subquery()
                    )
                )
                status_stats[f"{status.value}_topups"] = status_result.scalar() or 0

            return {
                "total_topups": total_topups,
                "total_amount": str(total_amount),
                "period_days": days,
                **status_stats
            }

        except Exception as e:
            logger.error(f"Error getting topup stats: {e}")
            return {
                "total_topups": 0,
                "total_amount": "0.00000000",
                "period_days": days
            }


balance_topup_crud = CRUDBalanceTopup(BalanceTopup)
