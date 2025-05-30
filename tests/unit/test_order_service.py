import pytest
import uuid
from decimal import Decimal

from app.models.models import (
    ProxyProduct, ProxyType, ProxyCategory, SessionType, ProviderType,
    Order, OrderStatus
)
from app.services.order_service import order_service
from app.core.exceptions import BusinessLogicError


@pytest.mark.unit
@pytest.mark.asyncio
class TestOrderService:

    async def test_create_order_from_cart_success(self, db_session, test_user):
        """Тест успешного создания заказа из корзины"""
        # Создаем продукт с обязательным proxy_category
        product = ProxyProduct(
            name="Test Product",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.DATACENTER,
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
            proxy_category=ProxyCategory.RESIDENTIAL,
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

        # ИСПРАВЛЕНО: используем BusinessLogicError вместо InsufficientFundsError
        with pytest.raises(BusinessLogicError, match="Insufficient balance"):
            await order_service.create_order_from_cart(db_session, test_user)

    async def test_create_order_empty_cart(self, db_session, test_user):
        """Тест создания заказа с пустой корзиной"""
        with pytest.raises(BusinessLogicError, match="Cart is empty"):
            await order_service.create_order_from_cart(db_session, test_user)

    async def test_get_user_orders(self, db_session, test_user):
        """Тест получения заказов пользователя"""
        # ИСПРАВЛЕНО: передаем user_id вместо user объекта
        orders = await order_service.get_user_orders(db_session, user_id=test_user.id)
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

        # ИСПРАВЛЕНО: используем правильную сигнатуру метода
        success = await order_service.cancel_order(
            db_session, order_id=order.id, user_id=test_user.id
        )

        assert success is True

        # Проверяем что заказ действительно отменен
        await db_session.refresh(order)
        assert order.status == OrderStatus.CANCELLED

    async def test_get_order_summary(self, db_session, test_user):
        """Тест получения сводки по заказам"""
        # ИСПРАВЛЕНО: передаем user_id и убираем recent_orders
        summary = await order_service.get_order_summary(db_session, user_id=test_user.id)

        assert "total_orders" in summary
        assert "total_spent" in summary
        assert "completed_orders" in summary  # ИСПРАВЛЕНО: вместо recent_orders
        assert "currency" in summary

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

        # ИСПРАВЛЕНО: используем правильную сигнатуру метода
        updated_order = await order_service.update_order_status(
            db_session, order_id=order.id, status=OrderStatus.PAID, user_id=test_user.id
        )

        assert updated_order is not None
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

        # ИСПРАВЛЕНО: используем правильную сигнатуру метода
        found_order = await order_service.get_order_by_id(
            db_session, order_id=order.id, user_id=test_user.id
        )
        assert found_order is not None
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

        # ИСПРАВЛЕНО: используем правильную сигнатуру метода
        found_order = await order_service.get_order_by_number(
            db_session, order_number=order_number, user_id=test_user.id
        )
        assert found_order is not None
        assert found_order.order_number == order_number

    async def test_get_order_by_id_wrong_user(self, db_session, test_user):
        """Тест получения заказа другого пользователя"""
        # Создаем заказ для другого пользователя
        unique_id = str(uuid.uuid4())[:8]
        order = Order(
            order_number=f"ORD-WRONG-{unique_id}",
            user_id=999,  # Другой пользователь
            total_amount=Decimal("5.00"),
            status=OrderStatus.PENDING
        )
        db_session.add(order)
        await db_session.commit()
        await db_session.refresh(order)

        # Пытаемся получить заказ
        found_order = await order_service.get_order_by_id(
            db_session, order_id=order.id, user_id=test_user.id
        )
        # Должен вернуть None, так как заказ принадлежит другому пользователю
        assert found_order is None

    async def test_cancel_order_already_cancelled(self, db_session, test_user):
        """Тест отмены уже отмененного заказа"""
        # Создаем отмененный заказ
        unique_id = str(uuid.uuid4())[:8]
        order = Order(
            order_number=f"ORD-CANCELLED-{unique_id}",
            user_id=test_user.id,
            total_amount=Decimal("5.00"),
            status=OrderStatus.CANCELLED
        )
        db_session.add(order)
        await db_session.commit()
        await db_session.refresh(order)

        # Пытаемся отменить уже отмененный заказ
        success = await order_service.cancel_order(
            db_session, order_id=order.id, user_id=test_user.id
        )

        # Должно вернуть False, так как заказ уже отменен
        assert success is False

    async def test_cancel_order_with_refund(self, db_session, test_user):
        """Тест отмены оплаченного заказа с возвратом средств"""
        # Запоминаем изначальный баланс
        initial_balance = test_user.balance

        # Создаем оплаченный заказ
        unique_id = str(uuid.uuid4())[:8]
        order_amount = Decimal("10.00")
        order = Order(
            order_number=f"ORD-REFUND-{unique_id}",
            user_id=test_user.id,
            total_amount=order_amount,
            status=OrderStatus.PAID
        )
        db_session.add(order)
        await db_session.commit()
        await db_session.refresh(order)

        # Отменяем заказ
        success = await order_service.cancel_order(
            db_session, order_id=order.id, user_id=test_user.id
        )

        assert success is True

        # Проверяем что деньги вернулись на баланс
        await db_session.refresh(test_user)
        assert test_user.balance == initial_balance + order_amount
