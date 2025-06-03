"""
Unit тесты для CRUD операций транзакций.

Тестирует создание, обновление, поиск транзакций
и операции с балансом пользователей.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta

from app.crud.transaction import transaction_crud
from app.models.models import TransactionType, TransactionStatus


@pytest.mark.unit
@pytest.mark.asyncio
class TestTransactionCRUD:
    """Тесты CRUD операций транзакций."""

    async def test_create_transaction_success(self, db_session, test_user):
        """Тест успешного создания транзакции."""
        transaction = await transaction_crud.create_transaction(
            db_session,
            user_id=test_user.id,
            amount=Decimal("25.00"),
            currency="USD",
            transaction_type=TransactionType.DEPOSIT,
            description="Test deposit transaction"
        )

        assert transaction.user_id == test_user.id
        assert transaction.amount == Decimal("25.00")
        assert transaction.currency == "USD"
        assert transaction.transaction_type == TransactionType.DEPOSIT
        assert transaction.status == TransactionStatus.PENDING
        assert transaction.description == "Test deposit transaction"
        assert transaction.transaction_id is not None

    async def test_create_transaction_with_order(self, db_session, test_user, test_order):
        """Тест создания транзакции с привязкой к заказу."""
        transaction = await transaction_crud.create_transaction(
            db_session,
            user_id=test_user.id,
            amount=Decimal("15.00"),
            currency="USD",
            transaction_type=TransactionType.PURCHASE,
            description="Purchase transaction",
            order_id=test_order.id
        )

        assert transaction.order_id == test_order.id
        assert transaction.transaction_type == TransactionType.PURCHASE

    async def test_get_transaction_by_id(self, db_session, test_user):
        """Тест получения транзакции по ID."""
        # Создаем транзакцию
        created_tx = await transaction_crud.create_transaction(
            db_session,
            user_id=test_user.id,
            amount=Decimal("10.00"),
            currency="USD",
            transaction_type=TransactionType.DEPOSIT
        )

        # Получаем по ID
        found_tx = await transaction_crud.get(db_session, obj_id=created_tx.id)

        assert found_tx is not None
        assert found_tx.id == created_tx.id
        assert found_tx.transaction_id == created_tx.transaction_id

    async def test_get_transaction_by_transaction_id(self, db_session, test_user):
        """Тест получения транзакции по transaction_id."""
        created_tx = await transaction_crud.create_transaction(
            db_session,
            user_id=test_user.id,
            amount=Decimal("20.00"),
            currency="USD",
            transaction_type=TransactionType.DEPOSIT
        )

        found_tx = await transaction_crud.get_by_transaction_id(
            db_session, transaction_id=created_tx.transaction_id
        )

        assert found_tx is not None
        assert found_tx.transaction_id == created_tx.transaction_id

    async def test_get_transaction_by_transaction_id_not_found(self, db_session):
        """Тест получения несуществующей транзакции."""
        found_tx = await transaction_crud.get_by_transaction_id(
            db_session, transaction_id="nonexistent_tx_id"
        )

        assert found_tx is None

    async def test_get_user_transactions(self, db_session, test_user):
        """Тест получения транзакций пользователя."""
        # Создаем несколько транзакций
        transactions_data = [
            (Decimal("10.00"), TransactionType.DEPOSIT),
            (Decimal("5.00"), TransactionType.PURCHASE),
            (Decimal("15.00"), TransactionType.DEPOSIT)
        ]

        created_transactions = []
        for amount, tx_type in transactions_data:
            tx = await transaction_crud.create_transaction(
                db_session,
                user_id=test_user.id,
                amount=amount,
                currency="USD",
                transaction_type=tx_type
            )
            created_transactions.append(tx)

        # Получаем все транзакции пользователя
        user_transactions = await transaction_crud.get_user_transactions(
            db_session, user_id=test_user.id
        )

        assert len(user_transactions) >= 3
        user_tx_ids = {tx.id for tx in user_transactions}
        created_tx_ids = {tx.id for tx in created_transactions}
        assert created_tx_ids.issubset(user_tx_ids)

    async def test_get_user_transactions_with_type_filter(self, db_session, test_user):
        """Тест получения транзакций с фильтром по типу."""
        # Создаем транзакции разных типов
        deposit_tx = await transaction_crud.create_transaction(
            db_session,
            user_id=test_user.id,
            amount=Decimal("100.00"),
            currency="USD",
            transaction_type=TransactionType.DEPOSIT
        )

        purchase_tx = await transaction_crud.create_transaction(
            db_session,
            user_id=test_user.id,
            amount=Decimal("25.00"),
            currency="USD",
            transaction_type=TransactionType.PURCHASE
        )

        # Получаем только депозиты
        deposit_transactions = await transaction_crud.get_user_transactions(
            db_session,
            user_id=test_user.id,
            transaction_type=TransactionType.DEPOSIT
        )

        deposit_tx_ids = {tx.id for tx in deposit_transactions}
        assert deposit_tx.id in deposit_tx_ids
        assert purchase_tx.id not in deposit_tx_ids

    async def test_get_user_transactions_with_pagination(self, db_session, test_user):
        """Тест получения транзакций с пагинацией."""
        # Создаем 10 транзакций
        for i in range(10):
            await transaction_crud.create_transaction(
                db_session,
                user_id=test_user.id,
                amount=Decimal(f"{i + 1}.00"),
                currency="USD",
                transaction_type=TransactionType.DEPOSIT
            )

        # Первая страница (5 элементов)
        first_page = await transaction_crud.get_user_transactions(
            db_session,
            user_id=test_user.id,
            skip=0,
            limit=5
        )

        # Вторая страница (5 элементов)
        second_page = await transaction_crud.get_user_transactions(
            db_session,
            user_id=test_user.id,
            skip=5,
            limit=5
        )

        assert len(first_page) == 5
        assert len(second_page) == 5

        # Проверяем что транзакции не пересекаются
        first_page_ids = {tx.id for tx in first_page}
        second_page_ids = {tx.id for tx in second_page}
        assert first_page_ids.isdisjoint(second_page_ids)

    async def test_update_transaction_status(self, db_session, test_user):
        """Тест обновления статуса транзакции."""
        transaction = await transaction_crud.create_transaction(
            db_session,
            user_id=test_user.id,
            amount=Decimal("30.00"),
            currency="USD",
            transaction_type=TransactionType.DEPOSIT
        )

        assert transaction.status == TransactionStatus.PENDING

        # Обновляем статус
        updated_tx = await transaction_crud.update_status(
            db_session,
            transaction=transaction,
            status=TransactionStatus.COMPLETED
        )

        assert updated_tx.status == TransactionStatus.COMPLETED

    async def test_create_refund_transaction(self, db_session, test_user):
        """Тест создания транзакции возврата."""
        # Создаем оригинальную транзакцию
        original_tx = await transaction_crud.create_transaction(
            db_session,
            user_id=test_user.id,
            amount=Decimal("50.00"),
            currency="USD",
            transaction_type=TransactionType.PURCHASE
        )

        # Создаем возврат
        refund_tx = await transaction_crud.create_refund_transaction(
            db_session,
            original_transaction=original_tx,
            refund_amount=Decimal("50.00"),
            reason="User request"
        )

        assert refund_tx.transaction_type == TransactionType.REFUND
        assert refund_tx.amount == Decimal("50.00")
        assert refund_tx.user_id == test_user.id
        assert refund_tx.description.startswith("Refund")

    async def test_get_transactions_by_date_range(self, db_session, test_user):
        """Тест получения транзакций за период."""
        # Создаем транзакции в разное время
        old_date = datetime.now() - timedelta(days=10)
        recent_date = datetime.now() - timedelta(days=1)

        old_tx = await transaction_crud.create_transaction(
            db_session,
            user_id=test_user.id,
            amount=Decimal("10.00"),
            currency="USD",
            transaction_type=TransactionType.DEPOSIT
        )
        # Симулируем старую дату
        old_tx.created_at = old_date
        await db_session.commit()

        recent_tx = await transaction_crud.create_transaction(
            db_session,
            user_id=test_user.id,
            amount=Decimal("20.00"),
            currency="USD",
            transaction_type=TransactionType.DEPOSIT
        )
        recent_tx.created_at = recent_date
        await db_session.commit()

        # Получаем транзакции за последние 5 дней
        from_date = datetime.now() - timedelta(days=5)
        to_date = datetime.now()

        recent_transactions = await transaction_crud.get_transactions_by_date_range(
            db_session,
            user_id=test_user.id,
            from_date=from_date,
            to_date=to_date
        )

        recent_tx_ids = {tx.id for tx in recent_transactions}
        assert recent_tx.id in recent_tx_ids
        assert old_tx.id not in recent_tx_ids

    async def test_get_transaction_statistics(self, db_session, test_user):
        """Тест получения статистики транзакций."""
        # Создаем транзакции разных типов
        await transaction_crud.create_transaction(
            db_session,
            user_id=test_user.id,
            amount=Decimal("100.00"),
            currency="USD",
            transaction_type=TransactionType.DEPOSIT,
            status=TransactionStatus.COMPLETED
        )

        await transaction_crud.create_transaction(
            db_session,
            user_id=test_user.id,
            amount=Decimal("25.00"),
            currency="USD",
            transaction_type=TransactionType.PURCHASE,
            status=TransactionStatus.COMPLETED
        )

        stats = await transaction_crud.get_transaction_statistics(
            db_session, user_id=test_user.id
        )

        assert "total_transactions" in stats
        assert "total_deposits" in stats
        assert "total_purchases" in stats
        assert "total_amount" in stats
        assert stats["total_transactions"] >= 2

    async def test_get_pending_transactions(self, db_session, test_user):
        """Тест получения ожидающих транзакций."""
        # Создаем транзакции с разными статусами
        pending_tx = await transaction_crud.create_transaction(
            db_session,
            user_id=test_user.id,
            amount=Decimal("40.00"),
            currency="USD",
            transaction_type=TransactionType.DEPOSIT
        )  # По умолчанию PENDING

        completed_tx = await transaction_crud.create_transaction(
            db_session,
            user_id=test_user.id,
            amount=Decimal("60.00"),
            currency="USD",
            transaction_type=TransactionType.DEPOSIT
        )
        await transaction_crud.update_status(
            db_session, completed_tx, TransactionStatus.COMPLETED
        )

        # Получаем только ожидающие
        pending_transactions = await transaction_crud.get_pending_transactions(
            db_session, user_id=test_user.id
        )

        pending_tx_ids = {tx.id for tx in pending_transactions}
        assert pending_tx.id in pending_tx_ids
        assert completed_tx.id not in pending_tx_ids

    async def test_generate_transaction_id_uniqueness(self):
        """Тест уникальности генерируемых ID транзакций."""
        transaction_ids = set()

        for _ in range(100):
            tx_id = transaction_crud._generate_transaction_id()
            assert tx_id not in transaction_ids
            transaction_ids.add(tx_id)
            assert tx_id.startswith("tx_")

    async def test_delete_transaction(self, db_session, test_user):
        """Тест удаления транзакции."""
        transaction = await transaction_crud.create_transaction(
            db_session,
            user_id=test_user.id,
            amount=Decimal("5.00"),
            currency="USD",
            transaction_type=TransactionType.DEPOSIT
        )

        tx_id = transaction.id

        # Удаляем транзакцию
        result = await transaction_crud.delete(db_session, obj_id=tx_id)
        assert result is not None

        # Проверяем что транзакция удалена
        deleted_tx = await transaction_crud.get(db_session, obj_id=tx_id)
        assert deleted_tx is None
