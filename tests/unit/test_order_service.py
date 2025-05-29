import pytest
import uuid
from decimal import Decimal

from app.models.models import (
    ProxyProduct, ProxyType, ProxyCategory, SessionType, ProviderType,
    Order, OrderStatus
)
from app.services.order_service import order_service
from app.core.exceptions import BusinessLogicError, InsufficientFundsError


@pytest.mark.unit
@pytest.mark.asyncio
class TestOrderService:

    async def test_create_order_from_cart_success(self, db_session, test_user):
        """Тест успешного создания заказа из корзины"""
        # Создаем продукт с обязательным proxy_category
        product = ProxyProduct(
            name="Test Product",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.DATACENTER,  # ДОБАВЛЕНО
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

        # Добавляем товар в корзину
        from app.crud.shopping_cart import shopping_cart_crud
        await shopping_cart_crud.add_to_cart(
            db_session,
            user_id=test_user.id,
            proxy_product_id=product.id,
            quantity=2
        )

        # Устанавливаем достаточный баланс
        test_user.balance = Decimal("10.00")
        await db_session.commit()

        # Создаем заказ
        order = await order_service.create_order_from_cart(db_session, test_user)

        assert order.user_id == test_user.id
        assert order.total_amount == Decimal("2.00")
        assert order.status == OrderStatus.PAID

    async def test_create_order_insufficient_balance(self, db_session, test_user):
        """Тест создания заказа с недостаточным балансом"""
        # Создаем дорогой продукт
        product = ProxyProduct(
            name="Expensive Product",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.RESIDENTIAL,  # ДОБАВЛЕНО
            session_type=SessionType.ROTATING,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("100.00"),
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
        from app.crud.shopping_cart import shopping_cart_crud
        await shopping_cart_crud.add_to_cart(
            db_session,
            user_id=test_user.id,
            proxy_product_id=product.id,
            quantity=1
        )

        # Устанавливаем недостаточный баланс
        test_user.balance = Decimal("1.00")
        await db_session.commit()

        # Пытаемся создать заказ
        with pytest.raises(InsufficientFundsError):
            await order_service.create_order_from_cart(db_session, test_user)

    async def test_create_order_empty_cart(self, db_session, test_user):
        """Тест создания заказа с пустой корзиной"""
        with pytest.raises(BusinessLogicError, match="Cart is empty"):
            await order_service.create_order_from_cart(db_session, test_user)

    async def test_get_user_orders(self, db_session, test_user):
        """Тест получения заказов пользователя"""
        orders = await order_service.get_user_orders(db_session, test_user)
        assert isinstance(orders, list)

    async def test_cancel_order_success(self, db_session, test_user):
        """Тест успешной отмены заказа"""
        # Создаем заказ
        unique_id = str(uuid.uuid4())[:8]
        order = Order(
            order_number=f"ORD-CANCEL-{unique_id}",
            user_id=test_user.id,
            total_amount=Decimal("5.00"),
            status=OrderStatus.PENDING
        )
        db_session.add(order)
        await db_session.commit()
        await db_session.refresh(order)

        # Отменяем заказ
        cancelled_order = await order_service.cancel_order(
            db_session, order.id, test_user, "Test cancellation"
        )

        assert cancelled_order.status == OrderStatus.CANCELLED
        assert "Test cancellation" in cancelled_order.notes

    async def test_get_order_summary(self, db_session, test_user):
        """Тест получения сводки по заказам"""
        summary = await order_service.get_order_summary(db_session, test_user)

        assert "total_orders" in summary
        assert "total_spent" in summary
        assert "recent_orders" in summary
        assert isinstance(summary["recent_orders"], list)

    async def test_update_order_status(self, db_session, test_user):
        """Тест обновления статуса заказа"""
        # Создаем заказ
        unique_id = str(uuid.uuid4())[:8]
        order = Order(
            order_number=f"ORD-UPDATE-{unique_id}",
            user_id=test_user.id,
            total_amount=Decimal("5.00"),
            status=OrderStatus.PENDING
        )
        db_session.add(order)
        await db_session.commit()
        await db_session.refresh(order)

        # Обновляем статус
        updated_order = await order_service.update_order_status(
            db_session, order.id, OrderStatus.PAID, test_user
        )

        assert updated_order.status == OrderStatus.PAID

    async def test_get_order_by_id(self, db_session, test_user):
        """Тест получения заказа по ID"""
        # Создаем заказ
        unique_id = str(uuid.uuid4())[:8]
        order = Order(
            order_number=f"ORD-GET-{unique_id}",
            user_id=test_user.id,
            total_amount=Decimal("5.00"),
            status=OrderStatus.PENDING
        )
        db_session.add(order)
        await db_session.commit()
        await db_session.refresh(order)

        # Получаем заказ
        found_order = await order_service.get_order_by_id(db_session, order.id, test_user)
        assert found_order.id == order.id

    async def test_get_order_by_number(self, db_session, test_user):
        """Тест получения заказа по номеру"""
        # Создаем заказ
        unique_id = str(uuid.uuid4())[:8]
        order_number = f"ORD-NUMBER-{unique_id}"
        order = Order(
            order_number=order_number,
            user_id=test_user.id,
            total_amount=Decimal("5.00"),
            status=OrderStatus.PENDING
        )
        db_session.add(order)
        await db_session.commit()
        await db_session.refresh(order)

        # Получаем заказ по номеру
        found_order = await order_service.get_order_by_number(db_session, order_number, test_user)
        assert found_order.order_number == order_number
