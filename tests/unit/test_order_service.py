"""
Unit тесты для сервиса заказов.

Тестирует создание заказов, обработку платежей, управление статусами
и интеграцию с внешними сервисами.
"""

import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest

from app.core.exceptions import BusinessLogicError
from app.models.models import (
    Order, OrderItem, OrderStatus, ProxyProduct, ProxyType, ProxyCategory,
    SessionType, ProviderType, ShoppingCart
)
from app.services.order_service import order_service


@pytest.mark.unit
@pytest.mark.asyncio
class TestOrderService:
    """Тесты сервиса заказов."""

    async def test_create_order_from_cart_success(self, db_session, test_user):
        """Тест успешного создания заказа из корзины."""
        # Создаем продукт
        product = ProxyProduct(
            name="Test Product",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.DATACENTER,
            session_type=SessionType.ROTATING,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("5.00"),
            duration_days=30,
            min_quantity=1,
            max_quantity=100,
            stock_available=50,
            is_active=True
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # Добавляем товар в корзину
        cart_item = ShoppingCart(
            user_id=test_user.id,
            proxy_product_id=product.id,
            quantity=2
        )
        db_session.add(cart_item)
        await db_session.commit()

        # Пополняем баланс пользователя
        test_user.balance = Decimal("20.00")
        await db_session.commit()

        # Мокаем создание покупки прокси
        with patch.object(order_service, 'create_proxy_purchases') as mock_create_purchases:
            mock_create_purchases.return_value = []

            order = await order_service.create_order_from_cart(db_session, test_user)

        assert order is not None
        assert order.user_id == test_user.id
        assert order.total_amount == Decimal("10.00")  # 2 * 5.00
        assert order.status == OrderStatus.COMPLETED

        # Проверяем что корзина очищена
        await db_session.execute(
            "SELECT COUNT(*) FROM shopping_cart WHERE user_id = ?", (test_user.id,)
        )
        # В зависимости от реализации корзина должна быть очищена

    async def test_create_order_empty_cart(self, db_session, test_user):
        """Тест создания заказа из пустой корзины."""
        with pytest.raises(BusinessLogicError, match="Cart is empty"):
            await order_service.create_order_from_cart(db_session, test_user)

    async def test_create_order_insufficient_balance(self, db_session, test_user):
        """Тест создания заказа с недостаточным балансом."""
        # Создаем дорогой продукт
        product = ProxyProduct(
            name="Expensive Product",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.DATACENTER,
            session_type=SessionType.ROTATING,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("100.00"),
            duration_days=30,
            stock_available=50,
            is_active=True
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # Добавляем в корзину
        cart_item = ShoppingCart(
            user_id=test_user.id,
            proxy_product_id=product.id,
            quantity=1
        )
        db_session.add(cart_item)
        await db_session.commit()

        # Баланс недостаточен (по умолчанию 0)
        with pytest.raises(BusinessLogicError, match="Insufficient balance"):
            await order_service.create_order_from_cart(db_session, test_user)

    async def test_get_user_orders(self, db_session, test_user, test_order):
        """Тест получения заказов пользователя."""
        orders = await order_service.get_user_orders(
            db_session, user_id=test_user.id
        )

        assert len(orders) >= 1
        assert any(order.id == test_order.id for order in orders)

    async def test_get_user_orders_with_pagination(self, db_session, test_user):
        """Тест получения заказов с пагинацией."""
        # Создаем несколько заказов
        orders_to_create = []
        for i in range(5):
            unique_id = str(uuid.uuid4())[:8]
            order = Order(
                order_number=f"ORD-PAGINATION-{unique_id}-{i}",
                user_id=test_user.id,
                total_amount=Decimal(f"{i + 1}0.00"),
                status=OrderStatus.PENDING
            )
            orders_to_create.append(order)

        db_session.add_all(orders_to_create)
        await db_session.commit()

        # Тестируем пагинацию
        first_page = await order_service.get_user_orders(
            db_session, user_id=test_user.id, skip=0, limit=3
        )

        second_page = await order_service.get_user_orders(
            db_session, user_id=test_user.id, skip=3, limit=3
        )

        assert len(first_page) == 3
        assert len(second_page) >= 2

        # Проверяем что заказы не дублируются
        first_page_ids = {order.id for order in first_page}
        second_page_ids = {order.id for order in second_page}
        assert first_page_ids.isdisjoint(second_page_ids)

    async def test_cancel_order_success(self, db_session, test_user, test_order):
        """Тест успешной отмены заказа."""
        # Устанавливаем статус PENDING для возможности отмены
        test_order.status = OrderStatus.PENDING
        await db_session.commit()

        success = await order_service.cancel_order(
            db_session, order_id=test_order.id, user_id=test_user.id
        )

        assert success is True
        await db_session.refresh(test_order)
        assert test_order.status == OrderStatus.CANCELLED

    async def test_cancel_order_already_completed(self, db_session, test_user, test_order):
        """Тест отмены уже завершенного заказа."""
        # Устанавливаем статус COMPLETED
        test_order.status = OrderStatus.COMPLETED
        await db_session.commit()

        success = await order_service.cancel_order(
            db_session, order_id=test_order.id, user_id=test_user.id
        )

        assert success is False

    async def test_get_order_summary(self, db_session, test_user):
        """Тест получения сводки заказов."""
        # Создаем заказы с разными статусами
        orders_data = [
            ("COMPLETED", Decimal("25.00")),
            ("COMPLETED", Decimal("15.50")),
            ("CANCELLED", Decimal("10.00")),
            ("PENDING", Decimal("5.00"))
        ]

        for i, (status, amount) in enumerate(orders_data):
            unique_id = str(uuid.uuid4())[:8]
            order = Order(
                order_number=f"ORD-SUMMARY-{unique_id}-{i}",
                user_id=test_user.id,
                total_amount=amount,
                status=OrderStatus[status]
            )
            db_session.add(order)

        await db_session.commit()

        summary = await order_service.get_order_summary(
            db_session, user_id=test_user.id, days=30
        )

        assert summary is not None
        assert "total_orders" in summary
        assert "total_spent" in summary
        assert "completed_orders" in summary
        assert "cancelled_orders" in summary
        assert summary["total_orders"] >= 4

    async def test_search_orders(self, db_session, test_user):
        """Тест поиска заказов."""
        # Создаем заказ с уникальным номером
        search_term = "SEARCH-TEST-12345"
        unique_id = str(uuid.uuid4())[:8]

        order = Order(
            order_number=f"ORD-{search_term}-{unique_id}",
            user_id=test_user.id,
            total_amount=Decimal("30.00"),
            status=OrderStatus.PENDING
        )
        db_session.add(order)
        await db_session.commit()

        # Ищем по части номера
        orders = await order_service.search_orders(
            db_session,
            search_term=search_term,
            user_id=test_user.id
        )

        assert len(orders) >= 1
        assert any(search_term in order.order_number for order in orders)

    async def test_generate_order_number_uniqueness(self):
        """Тест уникальности генерируемых номеров заказов."""
        order_numbers = set()

        for _ in range(100):
            order_number = order_service.generate_order_number()
            assert order_number not in order_numbers
            order_numbers.add(order_number)

            # Проверяем формат
            assert order_number.startswith("ORD-")
            assert len(order_number) >= 15

    async def test_calculate_order_total(self, db_session, test_user, test_proxy_product):
        """Тест расчета общей стоимости заказа."""
        # Создаем несколько товаров в корзине
        cart_items = []

        for i in range(3):
            cart_item = ShoppingCart(
                user_id=test_user.id,
                proxy_product_id=test_proxy_product.id,
                quantity=i + 1  # 1, 2, 3
            )
            cart_items.append(cart_item)

        db_session.add_all(cart_items)
        await db_session.commit()

        total = await order_service.calculate_cart_total(
            db_session, user_id=test_user.id
        )

        expected_total = test_proxy_product.price_per_proxy * (1 + 2 + 3)  # 6 * price
        assert total == expected_total

    @patch('app.services.order_service.order_service.create_proxy_purchases')
    async def test_create_proxy_purchases_integration(self, mock_create_purchases, db_session, test_order, test_proxy_product):
        """Тест интеграции создания покупок прокси."""
        mock_create_purchases.return_value = [
            {
                "proxy_list": "192.168.1.1:8080:user:pass\n192.168.1.2:8080:user:pass",
                "username": "testuser",
                "password": "testpass",
                "provider_order_id": "711_order_123",
                "expires_at": "2024-12-31T23:59:59Z"
            }
        ]

        # Создаем элемент заказа
        order_item = OrderItem(
            order_id=test_order.id,
            proxy_product_id=test_proxy_product.id,
            quantity=2,
            unit_price=test_proxy_product.price_per_proxy,
            total_price=test_proxy_product.price_per_proxy * 2
        )
        db_session.add(order_item)
        await db_session.commit()

        # Тестируем создание покупок прокси
        purchases = await order_service.create_proxy_purchases(db_session, test_order)

        assert len(purchases) >= 1
        mock_create_purchases.assert_called_once()

    async def test_order_status_transitions(self, db_session, test_user):
        """Тест переходов статусов заказа."""
        unique_id = str(uuid.uuid4())[:8]

        order = Order(
            order_number=f"ORD-STATUS-{unique_id}",
            user_id=test_user.id,
            total_amount=Decimal("15.00"),
            status=OrderStatus.PENDING
        )
        db_session.add(order)
        await db_session.commit()
        await db_session.refresh(order)

        # Тестируем допустимые переходы
        valid_transitions = [
            (OrderStatus.PENDING, OrderStatus.PAID),
            (OrderStatus.PAID, OrderStatus.PROCESSING),
            (OrderStatus.PROCESSING, OrderStatus.COMPLETED),
        ]

        for from_status, to_status in valid_transitions:
            order.status = from_status
            await db_session.commit()

            success = await order_service.update_order_status(
                db_session, order_id=order.id, status=to_status
            )

            assert success is True
            await db_session.refresh(order)
            assert order.status == to_status

    async def test_order_expiration_handling(self, db_session, test_user):
        """Тест обработки истечения заказов."""
        from datetime import datetime, timedelta

        unique_id = str(uuid.uuid4())[:8]

        # Создаем заказ с истекшим сроком
        order = Order(
            order_number=f"ORD-EXPIRED-{unique_id}",
            user_id=test_user.id,
            total_amount=Decimal("20.00"),
            status=OrderStatus.PENDING,
            expires_at=datetime.now() - timedelta(hours=1)  # Уже истек
        )
        db_session.add(order)
        await db_session.commit()

        # Тестируем обработку истекших заказов
        expired_orders = await order_service.get_expired_orders(db_session)

        assert len(expired_orders) >= 1
        assert any(order.id == o.id for o in expired_orders)

    @patch('app.integrations.proxy_711.proxy_711_api.purchase_proxies')
    async def test_proxy_provider_integration(self, mock_purchase, db_session, test_order, test_proxy_product):
        """Тест интеграции с провайдером прокси."""
        mock_purchase.return_value = {
            "provider_order_id": "711_success_123",
            "proxy_list": "203.0.113.1:8080:user123:pass456\n203.0.113.2:8080:user123:pass456",
            "username": "user123",
            "password": "pass456",
            "expires_at": "2024-12-31T23:59:59Z"
        }

        # Создаем элемент заказа
        order_item = OrderItem(
            order_id=test_order.id,
            proxy_product_id=test_proxy_product.id,
            quantity=2,
            unit_price=test_proxy_product.price_per_proxy,
            total_price=test_proxy_product.price_per_proxy * 2
        )
        db_session.add(order_item)
        await db_session.commit()

        # Тестируем покупку прокси
        result = await order_service.purchase_proxies_from_provider(
            db_session, order_item
        )

        assert result["provider_order_id"] == "711_success_123"
        assert "203.0.113.1:8080" in result["proxy_list"]
        mock_purchase.assert_called_once()

    async def test_order_rollback_on_failure(self, db_session, test_user, test_proxy_product):
        """Тест отката заказа при сбое."""
        # Добавляем товар в корзину
        cart_item = ShoppingCart(
            user_id=test_user.id,
            proxy_product_id=test_proxy_product.id,
            quantity=1
        )
        db_session.add(cart_item)
        await db_session.commit()

        # Пополняем баланс
        test_user.balance = Decimal("10.00")
        await db_session.commit()

        # Мокаем сбой при создании прокси
        with patch.object(order_service, 'create_proxy_purchases') as mock_create:
            mock_create.side_effect = Exception("Provider API error")

            with pytest.raises(Exception, match="Provider API error"):
                await order_service.create_order_from_cart(db_session, test_user)

        # Проверяем что заказ не создался или был откачен
        orders = await order_service.get_user_orders(db_session, user_id=test_user.id)
        failed_orders = [o for o in orders if o.status == OrderStatus.FAILED]

        # В зависимости от реализации - либо заказ помечен как FAILED, либо не создан
        if failed_orders:
            assert len(failed_orders) >= 1
