"""
CRUD операции для транзакций.

Содержит методы для управления финансовыми транзакциями,
пополнениями баланса и интеграцией с платежными системами.
Оптимизировано для MVP с Cryptomus.
"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional, Dict, Any

from sqlalchemy import select, and_, func, desc, update, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.models import Transaction, TransactionType, TransactionStatus, User, Order
from app.schemas.transaction import TransactionCreate, TransactionUpdate

logger = logging.getLogger(__name__)


class CRUDTransaction(CRUDBase[Transaction, TransactionCreate, TransactionUpdate]):
    """
    CRUD для управления транзакциями.

    Обеспечивает создание, обновление и отслеживание финансовых операций,
    включая пополнения баланса через Cryptomus и покупки.
    """

    async def create_balance_topup(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        amount: Decimal,
        payment_method: str = "cryptomus",
        provider_payment_id: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[Transaction]:
        """
        Создание транзакции пополнения баланса - КЛЮЧЕВОЕ для MVP.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            amount: Сумма пополнения
            payment_method: Метод оплаты
            provider_payment_id: ID платежа у провайдера
            description: Описание транзакции

        Returns:
            Optional[Transaction]: Созданная транзакция или None
        """
        try:
            if amount <= 0:
                raise ValueError("Amount must be positive")

            # Проверяем существование пользователя
            user = await db.get(User, user_id)
            if not user:
                raise ValueError("User not found")

            transaction = Transaction(
                user_id=user_id,
                amount=amount,
                currency="USD",
                transaction_type=TransactionType.BALANCE_TOPUP,
                status=TransactionStatus.PENDING,
                payment_method=payment_method,
                provider_payment_id=provider_payment_id,
                description=description or f"Balance topup via {payment_method}",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )

            db.add(transaction)
            await db.commit()
            await db.refresh(transaction)

            logger.info(f"Created balance topup transaction {transaction.id} for user {user_id}: {amount}")
            return transaction

        except ValueError:
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating balance topup: {e}")
            return None

    async def create_purchase_transaction(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        order_id: int,
        amount: Decimal,
        payment_method: str = "balance"
    ) -> Optional[Transaction]:
        """
        Создание транзакции покупки.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            order_id: ID заказа
            amount: Сумма покупки
            payment_method: Метод оплаты

        Returns:
            Optional[Transaction]: Созданная транзакция или None
        """
        try:
            if amount <= 0:
                raise ValueError("Amount must be positive")

            # Проверяем существование пользователя и заказа
            user = await db.get(User, user_id)
            if not user:
                raise ValueError("User not found")

            order = await db.get(Order, order_id)
            if not order:
                raise ValueError("Order not found")

            # Для покупок сумма отрицательная
            transaction = Transaction(
                user_id=user_id,
                order_id=order_id,
                amount=-amount,  # Отрицательная для списания
                currency="USD",
                transaction_type=TransactionType.PURCHASE,
                status=TransactionStatus.COMPLETED,  # Покупки сразу завершены
                payment_method=payment_method,
                description=f"Purchase for order {order.order_number}",
                processed_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )

            db.add(transaction)
            await db.commit()
            await db.refresh(transaction)

            logger.info(f"Created purchase transaction {transaction.id} for order {order_id}: {amount}")
            return transaction

        except ValueError:
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating purchase transaction: {e}")
            return None

    async def get_by_provider_payment_id(
        self,
        db: AsyncSession,
        *,
        provider_payment_id: str
    ) -> Optional[Transaction]:
        """
        Получение транзакции по ID платежа провайдера - для Cryptomus webhook.

        Args:
            db: Сессия базы данных
            provider_payment_id: ID платежа у провайдера

        Returns:
            Optional[Transaction]: Найденная транзакция или None
        """
        try:
            result = await db.execute(
                select(Transaction)
                .where(Transaction.provider_payment_id == provider_payment_id)
            )
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error getting transaction by provider payment ID {provider_payment_id}: {e}")
            return None

    async def update_transaction_status(
        self,
        db: AsyncSession,
        *,
        transaction: Transaction,
        status: TransactionStatus,
        provider_metadata: Optional[str] = None
    ) -> Optional[Transaction]:
        """
        Обновление статуса транзакции - для обработки Cryptomus webhook.

        Args:
            db: Сессия базы данных
            transaction: Транзакция для обновления
            status: Новый статус
            provider_metadata: Метаданные от провайдера

        Returns:
            Optional[Transaction]: Обновленная транзакция или None
        """
        try:
            old_status = transaction.status
            transaction.status = status
            transaction.updated_at = datetime.now(timezone.utc)

            if provider_metadata:
                transaction.provider_metadata = provider_metadata

            if status == TransactionStatus.COMPLETED:
                transaction.processed_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(transaction)

            logger.info(f"Updated transaction {transaction.id} status: {old_status} -> {status}")
            return transaction

        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating transaction status: {e}")
            return None

    async def get_user_transactions(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        transaction_type: Optional[TransactionType] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Transaction]:
        """
        Получение транзакций пользователя - для истории баланса.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            transaction_type: Фильтр по типу транзакции
            skip: Пропустить записей
            limit: Максимум записей

        Returns:
            List[Transaction]: Список транзакций
        """
        try:
            query = (
                select(Transaction)
                .options(selectinload(Transaction.order))
                .where(Transaction.user_id == user_id)
            )

            if transaction_type:
                query = query.where(Transaction.transaction_type == transaction_type)

            query = query.order_by(desc(Transaction.created_at)).offset(skip).limit(limit)
            result = await db.execute(query)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error getting user transactions: {e}")
            return []

    async def get_pending_transactions(
        self,
        db: AsyncSession,
        *,
        older_than_minutes: int = 30
    ) -> List[Transaction]:
        """
        Получение зависших транзакций для проверки.

        Args:
            db: Сессия базы данных
            older_than_minutes: Возраст транзакции в минутах

        Returns:
            List[Transaction]: Список зависших транзакций
        """
        try:
            threshold_time = datetime.now(timezone.utc) - timedelta(minutes=older_than_minutes)

            result = await db.execute(
                select(Transaction)
                .where(
                    and_(
                        Transaction.status == TransactionStatus.PENDING,
                        Transaction.created_at < threshold_time
                    )
                )
                .order_by(Transaction.created_at.asc())
            )
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error getting pending transactions: {e}")
            return []

    async def get_transaction_stats(
        self,
        db: AsyncSession,
        *,
        user_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Получение статистики транзакций.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя (опционально)
            days: Период в днях

        Returns:
            Dict[str, Any]: Статистика транзакций
        """
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)

            base_query = select(Transaction).where(Transaction.created_at >= start_date)
            if user_id:
                base_query = base_query.where(Transaction.user_id == user_id)

            # Общее количество
            total_result = await db.execute(
                select(func.count(Transaction.id)).select_from(base_query.subquery())
            )
            total_transactions = total_result.scalar() or 0

            # Сумма пополнений
            deposits_result = await db.execute(
                select(func.sum(Transaction.amount))
                .select_from(
                    base_query.where(
                        and_(
                            Transaction.transaction_type == TransactionType.BALANCE_TOPUP,
                            Transaction.status == TransactionStatus.COMPLETED
                        )
                    ).subquery()
                )
            )
            total_deposits = deposits_result.scalar() or Decimal('0.00000000')

            # Сумма покупок
            purchases_result = await db.execute(
                select(func.sum(Transaction.amount))
                .select_from(
                    base_query.where(
                        and_(
                            Transaction.transaction_type == TransactionType.PURCHASE,
                            Transaction.status == TransactionStatus.COMPLETED
                        )
                    ).subquery()
                )
            )
            total_purchases = abs(purchases_result.scalar() or Decimal('0.00000000'))

            # Статистика по статусам
            status_stats = {}
            for status in TransactionStatus:
                status_result = await db.execute(
                    select(func.count(Transaction.id))
                    .select_from(
                        base_query.where(Transaction.status == status).subquery()
                    )
                )
                status_stats[f"{status.value}_transactions"] = status_result.scalar() or 0

            # Статистика по типам
            type_stats = {}
            for transaction_type in TransactionType:
                type_result = await db.execute(
                    select(func.count(Transaction.id))
                    .select_from(
                        base_query.where(Transaction.transaction_type == transaction_type).subquery()
                    )
                )
                type_stats[f"{transaction_type.value}_transactions"] = type_result.scalar() or 0

            return {
                "total_transactions": total_transactions,
                "total_deposits": str(total_deposits),
                "total_purchases": str(total_purchases),
                "period_days": days,
                **status_stats,
                **type_stats
            }

        except Exception as e:
            logger.error(f"Error getting transaction stats: {e}")
            return {
                "total_transactions": 0,
                "total_deposits": "0.00000000",
                "total_purchases": "0.00000000",
                "period_days": days
            }

    async def get_transactions_by_status(
        self,
        db: AsyncSession,
        *,
        status: TransactionStatus,
        skip: int = 0,
        limit: int = 100
    ) -> List[Transaction]:
        """
        Получение транзакций по статусу.

        Args:
            db: Сессия базы данных
            status: Статус транзакции
            skip: Пропустить записей
            limit: Максимум записей

        Returns:
            List[Transaction]: Список транзакций
        """
        try:
            result = await db.execute(
                select(Transaction)
                .options(selectinload(Transaction.user), selectinload(Transaction.order))
                .where(Transaction.status == status)
                .order_by(desc(Transaction.created_at))
                .offset(skip)
                .limit(limit)
            )
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error getting transactions by status {status}: {e}")
            return []

    async def get_transactions_by_type(
        self,
        db: AsyncSession,
        *,
        transaction_type: TransactionType,
        skip: int = 0,
        limit: int = 100
    ) -> List[Transaction]:
        """
        Получение транзакций по типу.

        Args:
            db: Сессия базы данных
            transaction_type: Тип транзакции
            skip: Пропустить записей
            limit: Максимум записей

        Returns:
            List[Transaction]: Список транзакций
        """
        try:
            result = await db.execute(
                select(Transaction)
                .options(selectinload(Transaction.user), selectinload(Transaction.order))
                .where(Transaction.transaction_type == transaction_type)
                .order_by(desc(Transaction.created_at))
                .offset(skip)
                .limit(limit)
            )
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error getting transactions by type {transaction_type}: {e}")
            return []

    async def search_transactions(
        self,
        db: AsyncSession,
        *,
        search_term: str,
        user_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Transaction]:
        """
        Поиск транзакций по описанию или ID провайдера.

        Args:
            db: Сессия базы данных
            search_term: Поисковый термин
            user_id: ID пользователя (опционально)
            skip: Пропустить записей
            limit: Максимум записей

        Returns:
            List[Transaction]: Список найденных транзакций
        """
        try:
            if not search_term or len(search_term.strip()) < 2:
                return []

            search_pattern = f"%{search_term.strip()}%"

            query = select(Transaction).where(
                or_(
                    Transaction.description.ilike(search_pattern),
                    Transaction.provider_payment_id.ilike(search_pattern)
                )
            )

            if user_id:
                query = query.where(Transaction.user_id == user_id)

            query = query.order_by(desc(Transaction.created_at)).offset(skip).limit(limit)
            result = await db.execute(query)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error searching transactions: {e}")
            return []

    async def bulk_update_status(
        self,
        db: AsyncSession,
        *,
        transaction_ids: List[int],
        status: TransactionStatus,
        reason: Optional[str] = None
    ) -> int:
        """
        Массовое обновление статуса транзакций.

        Args:
            db: Сессия базы данных
            transaction_ids: Список ID транзакций
            status: Новый статус
            reason: Причина изменения

        Returns:
            int: Количество обновленных транзакций
        """
        try:
            if not transaction_ids:
                return 0

            update_data = {
                "status": status,
                "updated_at": datetime.now(timezone.utc)
            }

            if status == TransactionStatus.COMPLETED:
                update_data["processed_at"] = datetime.now(timezone.utc)

            result = await db.execute(
                update(Transaction)
                .where(Transaction.id.in_(transaction_ids))
                .values(**update_data)
            )
            await db.commit()

            updated_count = result.rowcount or 0
            logger.info(f"Bulk updated {updated_count} transactions to status {status}. Reason: {reason}")
            return updated_count

        except Exception as e:
            await db.rollback()
            logger.error(f"Error bulk updating transactions: {e}")
            return 0

    async def cleanup_old_transactions(
        self,
        db: AsyncSession,
        *,
        days_old: int = 90,
        keep_completed: bool = True
    ) -> int:
        """
        Очистка старых транзакций.

        Args:
            db: Сессия базы данных
            days_old: Возраст транзакций в днях
            keep_completed: Сохранять завершенные транзакции

        Returns:
            int: Количество удаленных транзакций
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)

            query = select(Transaction).where(Transaction.created_at < cutoff_date)

            if keep_completed:
                query = query.where(Transaction.status != TransactionStatus.COMPLETED)

            # Сначала получаем ID для удаления
            result = await db.execute(query)
            transactions_to_delete = list(result.scalars().all())

            if not transactions_to_delete:
                return 0

            # Удаляем транзакции
            from sqlalchemy import delete
            delete_ids = [t.id for t in transactions_to_delete]

            result = await db.execute(
                delete(Transaction).where(Transaction.id.in_(delete_ids))
            )
            await db.commit()

            deleted_count = result.rowcount or 0
            logger.info(f"Cleaned up {deleted_count} old transactions")
            return deleted_count

        except Exception as e:
            await db.rollback()
            logger.error(f"Error cleaning up old transactions: {e}")
            return 0

    async def get_daily_transaction_stats(
        self,
        db: AsyncSession,
        *,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Получение ежедневной статистики транзакций.

        Args:
            db: Сессия базы данных
            days: Количество дней

        Returns:
            List[Dict[str, Any]]: Ежедневная статистика
        """
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)

            result = await db.execute(
                select(
                    func.date(Transaction.created_at).label('date'),
                    func.count(Transaction.id).label('total_count'),
                    func.sum(
                        func.case(
                            (Transaction.transaction_type == TransactionType.BALANCE_TOPUP, Transaction.amount),
                            else_=0
                        )
                    ).label('deposits'),
                    func.sum(
                        func.case(
                            (Transaction.transaction_type == TransactionType.PURCHASE, func.abs(Transaction.amount)),
                            else_=0
                        )
                    ).label('purchases'),
                    func.count(
                        func.case(
                            (Transaction.status == TransactionStatus.COMPLETED, 1),
                            else_=None
                        )
                    ).label('completed_count')
                )
                .where(Transaction.created_at >= start_date)
                .group_by(func.date(Transaction.created_at))
                .order_by(func.date(Transaction.created_at))
            )

            stats = []
            for row in result.all():
                stats.append({
                    "date": row.date.isoformat(),
                    "total_transactions": row.total_count,
                    "completed_transactions": row.completed_count,
                    "total_deposits": str(row.deposits or Decimal('0.00000000')),
                    "total_purchases": str(row.purchases or Decimal('0.00000000')),
                    "success_rate": (row.completed_count / max(row.total_count, 1)) * 100
                })

            return stats

        except Exception as e:
            logger.error(f"Error getting daily transaction stats: {e}")
            return []

    async def get_user_balance_history(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Получение истории изменений баланса пользователя.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            days: Период в днях

        Returns:
            List[Dict[str, Any]]: История изменений баланса
        """
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)

            result = await db.execute(
                select(Transaction)
                .where(
                    and_(
                        Transaction.user_id == user_id,
                        Transaction.created_at >= start_date,
                        Transaction.status == TransactionStatus.COMPLETED
                    )
                )
                .order_by(Transaction.created_at.asc())
            )

            transactions = list(result.scalars().all())

            # Получаем текущий баланс пользователя
            user = await db.get(User, user_id)
            current_balance = user.balance if user else Decimal('0.00000000')

            # Рассчитываем баланс на каждый момент времени
            history = []
            running_balance = current_balance

            # Идем в обратном порядке, чтобы рассчитать исторический баланс
            for transaction in reversed(transactions):
                running_balance -= transaction.amount

                history.insert(0, {
                    "date": transaction.created_at.isoformat(),
                    "transaction_id": transaction.id,
                    "transaction_type": transaction.transaction_type.value,
                    "amount": str(transaction.amount),
                    "balance_after": str(running_balance + transaction.amount),
                    "description": transaction.description
                })

            return history

        except Exception as e:
            logger.error(f"Error getting user balance history: {e}")
            return []


transaction_crud = CRUDTransaction(Transaction)
