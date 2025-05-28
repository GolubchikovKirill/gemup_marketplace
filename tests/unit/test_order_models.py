from decimal import Decimal

import pytest

from app.models.models import Order, OrderItem, OrderStatus


@pytest.mark.unit
class TestOrderModels:

    def test_order_creation(self):
        """Тест создания модели заказа"""
        order = Order(
            order_number="ORD-20250128-TEST1234",
            user_id=1,
            total_amount=Decimal("15.50"),
            currency="USD",
            status=OrderStatus.PENDING,
            payment_method="balance"
        )

        assert order.order_number == "ORD-20250128-TEST1234"
        assert order.total_amount == Decimal("15.50")
        assert order.status == OrderStatus.PENDING
        assert order.currency == "USD"

    def test_order_item_creation(self):
        """Тест создания элемента заказа"""
        order_item = OrderItem(
            order_id=1,
            proxy_product_id=1,
            quantity=5,
            unit_price=Decimal("2.00"),
            total_price=Decimal("10.00"),
            generation_params='{"format": "ip:port"}'
        )

        assert order_item.quantity == 5
        assert order_item.unit_price == Decimal("2.00")
        assert order_item.total_price == Decimal("10.00")

    def test_order_status_enum(self):
        """Тест enum статусов заказа"""
        assert OrderStatus.PENDING == "pending"
        assert OrderStatus.PAID == "paid"
        assert OrderStatus.PROCESSING == "processing"
        assert OrderStatus.COMPLETED == "completed"
        assert OrderStatus.CANCELLED == "cancelled"
        assert OrderStatus.FAILED == "failed"
        assert OrderStatus.REFUNDED == "refunded"

    def test_order_repr(self):
        """Тест строкового представления заказа"""
        order = Order(
            id=1,
            order_number="ORD-TEST",
            status=OrderStatus.PENDING
        )

        repr_str = repr(order)
        assert "Order" in repr_str
        assert "ORD-TEST" in repr_str
        assert "pending" in repr_str
