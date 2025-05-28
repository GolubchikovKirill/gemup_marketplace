from decimal import Decimal

import pytest

from app.core.exceptions import BusinessLogicError, InsufficientFundsError
from app.models.models import (
    ProxyProduct, ProxyType, SessionType, ProviderType,
    OrderStatus, ShoppingCart
)
from app.schemas.cart import CartCreate
from app.services.cart_service import cart_service
from app.services.order_service import order_service, OrderBusinessRules


@pytest.mark.unit
@pytest.mark.asyncio
class TestOrderService:

    async def test_create_order_from_cart_success(self, db_session, test_user):
        """Тест успешного создания заказа из корзины"""
        # Создаем продукт
        product = ProxyProduct(
            name="Test Product",
            proxy_type=ProxyType.HTTP,
            session_type=SessionType.STICKY,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("1.00"),
            duration_days=30,
            min_quantity=1,
            max_quantity=100,
            stock_available=50,
            is_active=True
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # Пополняем баланс пользователя
        test_user.balance = Decimal("10.00")
        await db_session.commit()
        await db_session.refresh(test_user)

        # Добавляем товар в корзину
        cart_item = CartCreate(
            proxy_product_id=product.id,
            quantity=2,
            user_id=test_user.id
        )
        created_item = await cart_service.create(db_session, cart_item)
        await db_session.commit()

        # Создаем заказ
        order = await order_service.create_order_from_cart(
            db_session,
            user=test_user,
            payment_method="balance"
        )

        assert order is not None
        assert order.user_id == test_user.id
        assert order.total_amount == Decimal("2.00")
        assert order.status == OrderStatus.PAID
        assert len(order.order_items) == 1
        assert order.order_items[0].quantity == 2

        # Проверяем, что баланс списался
        await db_session.refresh(test_user)
        assert test_user.balance == Decimal("8.00")

        # Проверяем, что корзина очистилась
        cart_items = await cart_service.get_user_cart(db_session, user_id=test_user.id)
        assert len(cart_items) == 0

    async def test_create_order_insufficient_funds(self, db_session, test_user):
        """Тест создания заказа с недостаточным балансом"""
        # Создаем продукт
        product = ProxyProduct(
            name="Expensive Product",
            proxy_type=ProxyType.HTTP,
            session_type=SessionType.STICKY,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("10.00"),
            duration_days=30,
            min_quantity=1,
            max_quantity=100,
            stock_available=50,
            is_active=True
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # Устанавливаем недостаточный баланс
        test_user.balance = Decimal("5.00")
        await db_session.commit()

        # Добавляем товар в корзину
        cart_item = CartCreate(
            proxy_product_id=product.id,
            quantity=2,  # Итого: 20.00
            user_id=test_user.id
        )
        await cart_service.create(db_session, cart_item)

        # Пытаемся создать заказ
        with pytest.raises(InsufficientFundsError):
            await order_service.create_order_from_cart(
                db_session,
                user=test_user
            )

    async def test_create_order_empty_cart(self, db_session, test_user):
        """Тест создания заказа с пустой корзиной"""
        with pytest.raises(BusinessLogicError, match="Cart is empty"):
            await order_service.create_order_from_cart(
                db_session,
                user=test_user
            )

    async def test_create_order_insufficient_stock(self, db_session, test_user):
        """Тест создания заказа с недостаточным количеством товара"""
        # Создаем продукт с малым количеством на складе
        product = ProxyProduct(
            name="Limited Product",
            proxy_type=ProxyType.HTTP,
            session_type=SessionType.STICKY,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("1.00"),
            duration_days=30,
            min_quantity=1,
            max_quantity=100,
            stock_available=1,  # Только 1 товар
            is_active=True
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # Добавляем больше товаров, чем есть на складе
        cart_item = CartCreate(
            proxy_product_id=product.id,
            quantity=5,  # Больше чем stock_available
            user_id=test_user.id
        )

        # Ожидаем ошибку при добавлении в корзину
        with pytest.raises(Exception):  # Может быть ProductNotAvailableError или BusinessLogicError
            await cart_service.create(db_session, cart_item)

    async def test_get_user_orders(self, db_session, test_user):
        """Тест получения заказов пользователя"""
        orders = await order_service.get_user_orders(db_session, test_user)
        assert isinstance(orders, list)

    async def test_cancel_order_success(self, db_session, test_user):
        """Тест успешной отмены заказа"""
        # Создаем продукт и заказ
        product = ProxyProduct(
            name="Cancellable Product",
            proxy_type=ProxyType.HTTP,
            session_type=SessionType.STICKY,
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

        test_user.balance = Decimal("10.00")
        await db_session.commit()

        cart_item = CartCreate(
            proxy_product_id=product.id,
            quantity=1,
            user_id=test_user.id
        )
        await cart_service.create(db_session, cart_item)

        # Создаем заказ
        order = await order_service.create_order_from_cart(
            db_session,
            user=test_user
        )

        initial_stock = product.stock_available
        initial_balance = test_user.balance

        # Отменяем заказ
        cancelled_order = await order_service.cancel_order(
            db_session,
            order.id,
            test_user,
            "Test cancellation"
        )

        assert cancelled_order.status == OrderStatus.CANCELLED
        assert "Test cancellation" in cancelled_order.notes

        # Проверяем, что товар вернулся на склад
        await db_session.refresh(product)
        assert product.stock_available == initial_stock + 1

        # Проверяем, что средства вернулись на баланс
        await db_session.refresh(test_user)
        assert test_user.balance == initial_balance + Decimal("5.00")

    async def test_order_summary(self, db_session, test_user):
        """Тест получения сводки по заказам"""
        summary = await order_service.get_order_summary(db_session, test_user)

        assert "total_orders" in summary
        assert "pending_orders" in summary
        assert "completed_orders" in summary
        assert "cancelled_orders" in summary
        assert "total_spent" in summary
        assert "recent_orders" in summary
        assert isinstance(summary["recent_orders"], list)

    async def test_order_status_transitions(self, db_session):
        """Тест валидации переходов статусов заказа"""
        # Тестируем разрешенные переходы
        assert order_service._can_update_status(OrderStatus.PENDING, OrderStatus.PAID)
        assert order_service._can_update_status(OrderStatus.PAID, OrderStatus.PROCESSING)
        assert order_service._can_update_status(OrderStatus.PROCESSING, OrderStatus.COMPLETED)

        # Тестируем запрещенные переходы
        assert not order_service._can_update_status(OrderStatus.COMPLETED, OrderStatus.PENDING)
        assert not order_service._can_update_status(OrderStatus.CANCELLED, OrderStatus.PAID)


@pytest.mark.unit
@pytest.mark.asyncio
class TestOrderBusinessRules:

    async def test_validate_success(self, db_session):
        """Тест успешной валидации"""
        # Создаем продукт
        product = ProxyProduct(
            name="Valid Product",
            proxy_type=ProxyType.HTTP,
            session_type=SessionType.STICKY,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("1.00"),
            duration_days=30,
            min_quantity=1,
            max_quantity=100,
            stock_available=50,
            is_active=True
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # Создаем пользователя с достаточным балансом
        from app.models.models import User
        user = User(
            email="test@example.com",
            balance=Decimal("10.00"),
            is_guest=False,
            is_active=True
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Создаем элемент корзины
        cart_item = ShoppingCart(
            user_id=user.id,
            proxy_product_id=product.id,
            quantity=2
        )

        validator = OrderBusinessRules()
        result = await validator.validate({
            'user_id': user.id,
            'cart_items': [cart_item]
        }, db_session)

        assert result is True

    async def test_validate_inactive_product(self, db_session):
        """Тест валидации с неактивным продуктом"""
        product = ProxyProduct(
            name="Inactive Product",
            proxy_type=ProxyType.HTTP,
            session_type=SessionType.STICKY,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("1.00"),
            duration_days=30,
            min_quantity=1,
            max_quantity=100,
            stock_available=50,
            is_active=False  # Неактивный продукт
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        cart_item = ShoppingCart(
            proxy_product_id=product.id,
            quantity=1
        )

        validator = OrderBusinessRules()

        with pytest.raises(BusinessLogicError, match="not available"):
            await validator.validate({
                'user_id': 1,
                'cart_items': [cart_item]
            }, db_session)
