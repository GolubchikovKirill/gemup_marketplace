"""
CRUD операции для финансовых транзакций.

Содержит методы для создания, обновления и отслеживания финансовых операций,
включая пополнения, покупки, возвраты и выводы средств.
"""

import logging
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.models import Transaction, TransactionType, TransactionStatus, User
from app.schemas.transaction import TransactionCreate, TransactionUpdate

logger = logging.getLogger(__name__)


class CRUDTransaction(CRUDBase[Transaction, TransactionCreate, TransactionUpdate]):
    """
    CRUD для управления финансовыми транзакциями.

    Обеспечивает создание, обновление и отслеживание всех типов финансовых операций
    с поддержкой различных платежных провайдеров и статусов.
    """

    async def create_transaction(
            self,
            db: AsyncSession,
            *,
            user_id: int,
            amount: Decimal,
            transaction_type: TransactionType,
            payment_provider: str = "cryptomus",
            description: Optional[str] = None,
            order_id: Optional[int] = None,
            currency: str = "USD"
    ) -> Optional[Transaction]:
        """
        Создание новой транзакции.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            amount: Сумма транзакции
            transaction_type: Тип транзакции
            payment_provider: Платежный провайдер
            description: Описание транзакции
            order_id: ID связанного заказа
            currency: Валюта

        Returns:
            Optional[Transaction]: Созданная транзакция или None
        """
        try:
            # Валидация входных данных
            if amount <= 0:
                logger.warning(f"Invalid transaction amount: {amount}")
                return None

            # Проверяем существование пользователя
            user = await db.get(User, user_id)
            if not user:
                logger.warning(f"User {user_id} not found")
                return None

            # Генерируем уникальный ID транзакции
            transaction_id = self._generate_transaction_id()

            # Создаем транзакцию
            transaction = Transaction(
                transaction_id=transaction_id,
                user_id=user_id,
                order_id=order_id,
                amount=amount,
                currency=currency,
                transaction_type=transaction_type,
                status=TransactionStatus.PENDING,
                payment_provider=payment_provider,
                description=description or f"{transaction_type.value.title()} transaction"
            )

            db.add(transaction)
            await db.commit()
            await db.refresh(transaction)

            logger.info(
                f"Created transaction {transaction.transaction_id} for user {user_id}, amount: {amount} {currency}")
            return transaction

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating transaction: {e}")
            return None

    @staticmethod
    async def get_by_transaction_id(
            db: AsyncSession,
            *,
            transaction_id: str
    ) -> Optional[Transaction]:
        """
        Получение транзакции по transaction_id.

        Args:
            db: Сессия базы данных
            transaction_id: ID транзакции

        Returns:
            Optional[Transaction]: Транзакция или None
        """
        try:
            result = await db.execute(
                select(Transaction)
                .options(selectinload(Transaction.user))
                .where(Transaction.transaction_id == transaction_id)
            )
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error getting transaction by ID {transaction_id}: {e}")
            return None

    @staticmethod
    async def get_by_external_id(
            db: AsyncSession,
            *,
            external_transaction_id: str
    ) -> Optional[Transaction]:
        """
        Получение транзакции по внешнему ID.

        Args:
            db: Сессия базы данных
            external_transaction_id: Внешний ID транзакции

        Returns:
            Optional[Transaction]: Транзакция или None
        """
        try:
            result = await db.execute(
                select(Transaction).where(
                    Transaction.external_transaction_id == external_transaction_id
                )
            )
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error getting transaction by external ID {external_transaction_id}: {e}")
            return None

    @staticmethod
    async def update_status(
            db: AsyncSession,
            *,
            transaction: Transaction,
            status: TransactionStatus,
            external_transaction_id: Optional[str] = None,
            payment_url: Optional[str] = None,
            provider_metadata: Optional[str] = None
    ) -> Optional[Transaction]:
        """
        Обновление статуса транзакции.

        Args:
            db: Сессия базы данных
            transaction: Транзакция для обновления
            status: Новый статус
            external_transaction_id: Внешний ID транзакции
            payment_url: URL для оплаты
            provider_metadata: Метаданные провайдера

        Returns:
            Optional[Transaction]: Обновленная транзакция или None
        """
        try:
            old_status = transaction.status
            transaction.status = status

            if external_transaction_id:
                transaction.external_transaction_id = external_transaction_id

            if payment_url:
                transaction.payment_url = payment_url

            if provider_metadata:
                transaction.provider_metadata = provider_metadata

            if status == TransactionStatus.COMPLETED:
                transaction.completed_at = datetime.now()

            transaction.updated_at = datetime.now()

            await db.commit()
            await db.refresh(transaction)

            logger.info(f"Updated transaction {transaction.transaction_id} status: {old_status} -> {status}")
            return transaction

        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating transaction {transaction.id} status: {e}")
            return None

    @staticmethod
    async def get_user_transactions(
            db: AsyncSession,
            *,
            user_id: int,
            transaction_type: Optional[TransactionType] = None,
            status: Optional[TransactionStatus] = None,
            skip: int = 0,
            limit: int = 100
    ) -> List[Transaction]:
        """
        Получение транзакций пользователя.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            transaction_type: Фильтр по типу транзакции
            status: Фильтр по статусу
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            List[Transaction]: Список транзакций пользователя
        """
        try:
            query = select(Transaction).where(Transaction.user_id == user_id)

            if transaction_type:
                query = query.where(Transaction.transaction_type == transaction_type)

            if status:
                query = query.where(Transaction.status == status)

            query = query.order_by(desc(Transaction.created_at)).offset(skip).limit(limit)
            result = await db.execute(query)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error getting transactions for user {user_id}: {e}")
            return []

    @staticmethod
    async def get_pending_transactions(
            db: AsyncSession,
            *,
            older_than_minutes: Optional[int] = None
    ) -> List[Transaction]:
        """
        Получение транзакций в ожидании.

        Args:
            db: Сессия базы данных
            older_than_minutes: Фильтр по времени создания (старше N минут)

        Returns:
            List[Transaction]: Список ожидающих транзакций
        """
        try:
            query = select(Transaction).where(Transaction.status == TransactionStatus.PENDING)

            if older_than_minutes:
                time_threshold = datetime.now() - timedelta(minutes=older_than_minutes)
                query = query.where(Transaction.created_at < time_threshold)

            query = query.order_by(Transaction.created_at.asc())
            result = await db.execute(query)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error getting pending transactions: {e}")
            return []

    @staticmethod
    async def get_failed_transactions(
            db: AsyncSession,
            *,
            days_back: int = 7,
            limit: int = 100
    ) -> List[Transaction]:
        """
        Получение неудачных транзакций.

        Args:
            db: Сессия базы данных
            days_back: Количество дней назад для поиска
            limit: Максимальное количество записей

        Returns:
            List[Transaction]: Список неудачных транзакций
        """
        try:
            time_threshold = datetime.now() - timedelta(days=days_back)

            result = await db.execute(
                select(Transaction)
                .where(
                    and_(
                        Transaction.status == TransactionStatus.FAILED,
                        Transaction.created_at >= time_threshold
                    )
                )
                .order_by(desc(Transaction.created_at))
                .limit(limit)
            )
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error getting failed transactions: {e}")
            return []

    @staticmethod
    async def get_transactions_by_amount_range(
            db: AsyncSession,
            *,
            min_amount: Decimal,
            max_amount: Decimal,
            currency: str = "USD",
            skip: int = 0,
            limit: int = 100
    ) -> List[Transaction]:
        """
        Получение транзакций по диапазону сумм.

        Args:
            db: Сессия базы данных
            min_amount: Минимальная сумма
            max_amount: Максимальная сумма
            currency: Валюта
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            List[Transaction]: Список транзакций в диапазоне сумм
        """
        try:
            result = await db.execute(
                select(Transaction)
                .where(
                    and_(
                        Transaction.amount >= min_amount,
                        Transaction.amount <= max_amount,
                        Transaction.currency == currency
                    )
                )
                .order_by(desc(Transaction.created_at))
                .offset(skip)
                .limit(limit)
            )
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error getting transactions by amount range: {e}")
            return []

    @staticmethod
    async def get_transactions_stats(
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
            days: Период для статистики в днях

        Returns:
            Dict[str, Any]: Статистика транзакций
        """
        try:
            start_date = datetime.now() - timedelta(days=days)

            base_query = select(Transaction).where(Transaction.created_at >= start_date)
            if user_id:
                base_query = base_query.where(Transaction.user_id == user_id)

            # Общее количество транзакций
            total_result = await db.execute(
                select(func.count(Transaction.id)).select_from(base_query.subquery())
            )
            total_transactions = total_result.scalar() or 0

            # Общая сумма по завершенным транзакциям
            completed_sum_result = await db.execute(
                select(func.sum(Transaction.amount))
                .select_from(
                    base_query.where(Transaction.status == TransactionStatus.COMPLETED).subquery()
                )
            )
            total_amount = completed_sum_result.scalar() or Decimal('0.00')

            # Статистика по статусам
            status_stats = {}
            for status in TransactionStatus:
                status_result = await db.execute(
                    select(func.count(Transaction.id))
                    .select_from(
                        base_query.where(Transaction.status == status).subquery()
                    )
                )
                status_stats[status.value] = status_result.scalar() or 0

            # Статистика по типам
            type_stats = {}
            for trans_type in TransactionType:
                type_result = await db.execute(
                    select(func.count(Transaction.id))
                    .select_from(
                        base_query.where(Transaction.transaction_type == trans_type).subquery()
                    )
                )
                type_stats[trans_type.value] = type_result.scalar() or 0

            # Статистика по провайдерам
            provider_stats_result = await db.execute(
                select(
                    Transaction.payment_provider,
                    func.count(Transaction.id)
                )
                .select_from(base_query.subquery())
                .group_by(Transaction.payment_provider)
            )
            provider_stats = dict(provider_stats_result.all())

            return {
                "total_transactions": total_transactions,
                "total_amount": str(total_amount),
                "status_breakdown": status_stats,
                "type_breakdown": type_stats,
                "provider_breakdown": provider_stats,
                "period_days": days
            }

        except Exception as e:
            logger.error(f"Error getting transaction stats: {e}")
            return {
                "total_transactions": 0,
                "total_amount": "0.00",
                "status_breakdown": {},
                "type_breakdown": {},
                "provider_breakdown": {},
                "period_days": days
            }

    @staticmethod
    async def search_transactions(
            db: AsyncSession,
            *,
            search_term: str,
            user_id: Optional[int] = None,
            skip: int = 0,
            limit: int = 100
    ) -> List[Transaction]:
        """
        Поиск транзакций по ID или описанию.

        Args:
            db: Сессия базы данных
            search_term: Поисковый термин
            user_id: ID пользователя (опционально)
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            List[Transaction]: Список найденных транзакций
        """
        try:
            if not search_term or len(search_term.strip()) < 2:
                return []

            search_pattern = f"%{search_term.strip()}%"

            query = select(Transaction).where(
                or_(
                    Transaction.transaction_id.ilike(search_pattern),
                    Transaction.external_transaction_id.ilike(search_pattern),
                    Transaction.description.ilike(search_pattern)
                )
            )

            if user_id:
                query = query.where(Transaction.user_id == user_id)

            query = query.order_by(desc(Transaction.created_at)).offset(skip).limit(limit)
            result = await db.execute(query)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error searching transactions with term '{search_term}': {e}")
            return []

    @staticmethod
    def _generate_transaction_id() -> str:
        """
        Генерация уникального ID транзакции.

        Returns:
            str: Уникальный ID транзакции
        """
        date_part = datetime.now().strftime('%Y%m%d')
        random_part = str(uuid.uuid4())[:8].upper()
        return f"TXN-{date_part}-{random_part}"

    async def cancel_transaction(
            self,
            db: AsyncSession,
            *,
            transaction_id: str,
            reason: Optional[str] = None
    ) -> Optional[Transaction]:
        """
        Отмена транзакции.

        Args:
            db: Сессия базы данных
            transaction_id: ID транзакции
            reason: Причина отмены

        Returns:
            Optional[Transaction]: Отмененная транзакция или None
        """
        try:
            transaction = await self.get_by_transaction_id(db, transaction_id=transaction_id)

            if not transaction:
                logger.warning(f"Transaction {transaction_id} not found")
                return None

            if transaction.status != TransactionStatus.PENDING:
                logger.warning(f"Cannot cancel transaction {transaction_id} with status {transaction.status}")
                return None

            transaction.status = TransactionStatus.CANCELLED
            transaction.updated_at = datetime.now()

            if reason:
                # Добавляем причину к описанию
                transaction.description = f"{transaction.description} (Cancelled: {reason})"

            await db.commit()
            await db.refresh(transaction)

            logger.info(f"Cancelled transaction {transaction_id}, reason: {reason}")
            return transaction

        except Exception as e:
            await db.rollback()
            logger.error(f"Error cancelling transaction {transaction_id}: {e}")
            return None


transaction_crud = CRUDTransaction(Transaction)
