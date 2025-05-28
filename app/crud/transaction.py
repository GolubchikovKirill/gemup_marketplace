from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import uuid

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
            payment_provider: str = "cryptomus",
            description: str = None,
            order_id: int = None,
            currency: str = "USD"  # ИСПРАВЛЕНО: добавлен параметр currency
    ) -> Transaction:
        """Создание новой транзакции"""
        transaction_id = f"TXN-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

        transaction = Transaction(
            transaction_id=transaction_id,
            user_id=user_id,
            order_id=order_id,
            amount=amount,
            currency=currency,  # ИСПРАВЛЕНО: передаем currency
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
    async def get_by_transaction_id(
            db: AsyncSession,
            *,
            transaction_id: str
    ) -> Optional[Transaction]:
        """Получение транзакции по transaction_id"""
        result = await db.execute(
            select(Transaction).where(Transaction.transaction_id == transaction_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_status(
            db: AsyncSession,
            *,
            transaction: Transaction,
            status: TransactionStatus,
            external_transaction_id: str = None,
            payment_url: str = None
    ) -> Transaction:
        """Обновление статуса транзакции"""
        transaction.status = status

        if external_transaction_id:
            transaction.external_transaction_id = external_transaction_id

        if payment_url:
            transaction.payment_url = payment_url

        if status == TransactionStatus.COMPLETED:
            transaction.completed_at = datetime.now()

        transaction.updated_at = datetime.now()

        await db.commit()
        await db.refresh(transaction)
        return transaction

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
    async def get_pending_transactions(db: AsyncSession) -> List[Transaction]:
        """Получение транзакций в ожидании"""
        result = await db.execute(
            select(Transaction).where(Transaction.status == TransactionStatus.PENDING)
        )
        return list(result.scalars().all())


transaction_crud = CRUDTransaction(Transaction)
