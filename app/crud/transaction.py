import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.models import Transaction, TransactionType, TransactionStatus
from app.schemas.transaction import TransactionCreate, TransactionUpdate


class CRUDTransaction(CRUDBase[Transaction, TransactionCreate, TransactionUpdate]):

    @staticmethod
    async def create_transaction(
            db: AsyncSession,
            *,
            user_id: int,
            amount: float,
            transaction_type: TransactionType,
            order_id: Optional[int] = None,
            payment_provider: str = "cryptomus",
            description: Optional[str] = None
    ) -> Transaction:
        """Создание новой транзакции"""
        transaction_id = f"TXN-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

        transaction = Transaction(
            transaction_id=transaction_id,
            user_id=user_id,
            order_id=order_id,
            amount=amount,
            transaction_type=transaction_type,
            status=TransactionStatus.PENDING,
            payment_provider=payment_provider,
            description=description
        )

        db.add(transaction)
        await db.commit()
        await db.refresh(transaction)
        return transaction

    @staticmethod
    async def get_by_transaction_id(db: AsyncSession, *, transaction_id: str) -> Optional[Transaction]:
        """Получение транзакции по ID"""
        result = await db.execute(
            select(Transaction).where(Transaction.transaction_id == transaction_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_external_id(db: AsyncSession, *, external_id: str) -> Optional[Transaction]:
        """Получение транзакции по внешнему ID"""
        result = await db.execute(
            select(Transaction).where(Transaction.external_transaction_id == external_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_transactions(
            db: AsyncSession,
            *,
            user_id: int,
            skip: int = 0,
            limit: int = 100
    ) -> List[Transaction]:
        """Получение транзакций пользователя"""
        result = await db.execute(
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_by_status(
            db: AsyncSession,
            *,
            status: TransactionStatus,
            skip: int = 0,
            limit: int = 100
    ) -> List[Transaction]:
        """Получение транзакций по статусу"""
        result = await db.execute(
            select(Transaction)
            .where(Transaction.status == status)
            .order_by(Transaction.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def update_status(
            db: AsyncSession,
            *,
            transaction: Transaction,
            status: TransactionStatus,
            external_transaction_id: Optional[str] = None,
            payment_url: Optional[str] = None
    ) -> Transaction:
        """Обновление статуса транзакции"""
        transaction.status = status
        transaction.updated_at = datetime.now()

        if external_transaction_id:
            transaction.external_transaction_id = external_transaction_id

        if payment_url:
            transaction.payment_url = payment_url

        if status in [TransactionStatus.COMPLETED, TransactionStatus.FAILED]:
            transaction.completed_at = datetime.now()

        await db.commit()
        await db.refresh(transaction)
        return transaction

    @staticmethod
    async def get_pending_transactions(db: AsyncSession) -> List[Transaction]:
        """Получение всех ожидающих транзакций"""
        result = await db.execute(
            select(Transaction).where(Transaction.status == TransactionStatus.PENDING)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_order_transactions(
            db: AsyncSession,
            *,
            order_id: int
    ) -> List[Transaction]:
        """Получение транзакций для заказа"""
        result = await db.execute(
            select(Transaction)
            .where(Transaction.order_id == order_id)
            .order_by(Transaction.created_at.desc())
        )
        return list(result.scalars().all())


transaction_crud = CRUDTransaction(Transaction)
