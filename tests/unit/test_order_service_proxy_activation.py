import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest

from app.models.models import (
    Order, OrderItem, OrderStatus, TransactionStatus, ProxyProduct, ProxyType, ProxyCategory, SessionType, ProviderType,
    TransactionType
)
from app.services.order_service import order_service


@pytest.mark.unit
@pytest.mark.asyncio
class TestOrderServiceProxyActivation:

    @patch.object(order_service, '_activate_proxies_for_order')
    async def test_process_successful_payment_with_proxy_activation(
            self, mock_activate_proxies, db_session, test_user
    ):
        """Тест активации прокси при успешной оплате заказа"""
        unique_id = str(uuid.uuid4())[:8]

        # Создаем продукт с обязательным proxy_category
        product = ProxyProduct(
            name="Test Proxy Product",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.DATACENTER,  # ДОБАВЛЕНО
            session_type=SessionType.STICKY,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("2.00"),
            duration_days=30,
            min_quantity=1,
            max_quantity=100,
            stock_available=100,
            is_active=True
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # Создаем заказ с уникальным номером
        order = Order(
            order_number=f"ORD-TEST-{unique_id}",
            user_id=test_user.id,
            total_amount=Decimal("4.00"),
            status=OrderStatus.PAID
        )
        db_session.add(order)
        await db_session.commit()
        await db_session.refresh(order)

        # Создаем элемент заказа
        order_item = OrderItem(
            order_id=order.id,
            proxy_product_id=product.id,
            quantity=2,
            unit_price=Decimal("2.00"),
            total_price=Decimal("4.00")
        )
        db_session.add(order_item)
        await db_session.commit()

        # Создаем транзакцию
        from app.crud.transaction import transaction_crud
        transaction = await transaction_crud.create_transaction(
            db_session,
            user_id=test_user.id,
            amount=4.0,
            currency="USD",
            transaction_type=TransactionType.DEPOSIT,
            order_id=order.id
        )

        # Мокаем активацию прокси
        mock_activate_proxies.return_value = []

        # Обрабатываем успешный платеж
        await order_service._process_successful_payment(
            db_session, transaction, "4.00"
        )

        # Проверяем, что активация прокси была вызвана
        mock_activate_proxies.assert_called()

    async def test_process_successful_payment_without_order(self, db_session, test_user):
        """Тест обработки платежа без связанного заказа"""
        # Создаем транзакцию без заказа (пополнение баланса)
        from app.crud.transaction import transaction_crud
        transaction = await transaction_crud.create_transaction(
            db_session,
            user_id=test_user.id,
            amount=10.0,
            currency="USD",
            transaction_type=TransactionType.DEPOSIT
        )

        # Обрабатываем успешный платеж
        await order_service._process_successful_payment(
            db_session, transaction, "10.00"
        )

        # Проверяем, что баланс пополнился
        await db_session.refresh(test_user)
        assert test_user.balance >= Decimal("10.00")

        # Проверяем, что транзакция завершилась
        await db_session.refresh(transaction)
        assert transaction.status == TransactionStatus.COMPLETED
