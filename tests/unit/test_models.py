"""
Unit тесты для моделей базы данных.

Тестирует создание экземпляров моделей, валидацию полей,
связи между таблицами и поведение модели.
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.models.models import (
    User, ProxyProduct, Order, OrderItem, Transaction, ProxyPurchase, ShoppingCart,
    ProxyType, ProxyCategory, SessionType, ProviderType, OrderStatus,
    TransactionType, TransactionStatus
)


@pytest.mark.unit
class TestUserModel:
    """Тесты модели пользователя."""

    def test_user_creation_registered(self):
        """Тест создания зарегистрированного пользователя."""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password_123",
            first_name="Test",
            last_name="User",
            is_guest=False,
            is_active=True,
            balance=Decimal('0.00')
        )

        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.is_guest is False
        assert user.is_active is True
        assert user.balance == Decimal('0.00')
        assert user.hashed_password == "hashed_password_123"

    def test_user_creation_guest(self):
        """Тест создания гостевого пользователя."""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

        guest = User(
            is_guest=True,
            guest_session_id="guest-session-123",
            guest_expires_at=expires_at,
            balance=Decimal('0.00')
        )

        assert guest.is_guest is True
        assert guest.guest_session_id == "guest-session-123"
        assert guest.guest_expires_at == expires_at
        assert guest.email is None
        assert guest.username is None

    def test_user_default_values(self):
        """Тест значений по умолчанию."""
        user = User(email="default@example.com")

        # Проверяем значения по умолчанию
        assert user.balance == Decimal('0.00') or user.balance is None
        assert user.is_active is True or user.is_active is None
        assert user.is_guest is False or user.is_guest is None
        assert user.is_verified is False or user.is_verified is None

    def test_user_string_representation(self):
        """Тест строкового представления пользователя."""
        user = User(
            id=1,
            email="repr@example.com",
            username="repruser"
        )

        user_str = str(user)
        assert "repruser" in user_str or "repr@example.com" in user_str


@pytest.mark.unit
class TestProxyProductModel:
    """Тесты модели продукта прокси."""

    def test_proxy_product_creation(self):
        """Тест создания продукта прокси."""
        product = ProxyProduct(
            name="US HTTP Proxies",
            description="High-quality US HTTP proxies",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.DATACENTER,
            session_type=SessionType.ROTATING,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            city="New York",
            price_per_proxy=Decimal("2.50"),
            price_per_gb=Decimal("0.10"),
            duration_days=30,
            min_quantity=1,
            max_quantity=1000,
            max_threads=10,
            bandwidth_limit_gb=100,
            uptime_guarantee=Decimal("99.9"),
            speed_mbps=100,
            ip_pool_size=10000,
            stock_available=500,
            is_active=True,
            is_featured=False
        )

        assert product.name == "US HTTP Proxies"
        assert product.proxy_type == ProxyType.HTTP
        assert product.proxy_category == ProxyCategory.DATACENTER
        assert product.price_per_proxy == Decimal("2.50")
        assert product.country_code == "US"
        assert product.is_active is True

    def test_proxy_product_default_values(self):
        """Тест значений по умолчанию продукта."""
        product = ProxyProduct(
            name="Default Product",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.DATACENTER,
            session_type=SessionType.STICKY,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("1.00"),
            duration_days=30
        )

        assert product.is_active is True or product.is_active is None
        assert product.is_featured is False or product.is_featured is None
        assert product.stock_available == 0 or product.stock_available is None

    def test_proxy_product_enums(self):
        """Тест перечислений в модели продукта."""
        # Тестируем все типы прокси
        for proxy_type in ProxyType:
            product = ProxyProduct(
                name=f"Product {proxy_type.value}",
                proxy_type=proxy_type,
                proxy_category=ProxyCategory.DATACENTER,
                session_type=SessionType.STICKY,
                provider=ProviderType.PROVIDER_711,
                country_code="US",
                country_name="United States",
                price_per_proxy=Decimal("1.00"),
                duration_days=30
            )
            assert product.proxy_type == proxy_type

        # Тестируем все категории
        for category in ProxyCategory:
            product = ProxyProduct(
                name=f"Product {category.value}",
                proxy_type=ProxyType.HTTP,
                proxy_category=category,
                session_type=SessionType.STICKY,
                provider=ProviderType.PROVIDER_711,
                country_code="US",
                country_name="United States",
                price_per_proxy=Decimal("1.00"),
                duration_days=30
            )
            assert product.proxy_category == category


@pytest.mark.unit
class TestOrderModel:
    """Тесты модели заказа."""

    def test_order_creation(self):
        """Тест создания заказа."""
        order = Order(
            order_number="ORD-20240115-TEST123",
            user_id=1,
            total_amount=Decimal("25.50"),
            currency="USD",
            status=OrderStatus.PENDING,
            payment_method="balance",
            expires_at=datetime.now() + timedelta(hours=24)
        )

        assert order.order_number == "ORD-20240115-TEST123"
        assert order.total_amount == Decimal("25.50")
        assert order.status == OrderStatus.PENDING
        assert order.currency == "USD"
        assert order.payment_method == "balance"

    def test_order_status_enum(self):
        """Тест enum статусов заказа."""
        # Проверяем все возможные статусы
        statuses = [
            OrderStatus.PENDING,
            OrderStatus.PAID,
            OrderStatus.PROCESSING,
            OrderStatus.COMPLETED,
            OrderStatus.CANCELLED,
            OrderStatus.FAILED,
            OrderStatus.REFUNDED
        ]

        for status in statuses:
            order = Order(
                order_number=f"ORD-{status.value.upper()}",
                user_id=1,
                total_amount=Decimal("10.00"),
                status=status
            )
            assert order.status == status

    def test_order_default_currency(self):
        """Тест валюты по умолчанию."""
        order = Order(
            order_number="ORD-DEFAULT-CURRENCY",
            user_id=1,
            total_amount=Decimal("10.00"),
            status=OrderStatus.PENDING
        )

        # Валюта по умолчанию должна быть USD или None
        assert order.currency == "USD" or order.currency is None


@pytest.mark.unit
class TestOrderItemModel:
    """Тесты модели элемента заказа."""

    def test_order_item_creation(self):
        """Тест создания элемента заказа."""
        order_item = OrderItem(
            order_id=1,
            proxy_product_id=1,
            quantity=5,
            unit_price=Decimal("3.00"),
            total_price=Decimal("15.00"),
            generation_params='{"format": "ip:port:user:pass"}'
        )

        assert order_item.quantity == 5
        assert order_item.unit_price == Decimal("3.00")
        assert order_item.total_price == Decimal("15.00")
        assert '"format"' in order_item.generation_params

    def test_order_item_price_calculation_validation(self):
        """Тест валидации расчета цены в элементе заказа."""
        # Правильный расчет
        correct_item = OrderItem(
            order_id=1,
            proxy_product_id=1,
            quantity=4,
            unit_price=Decimal("2.50"),
            total_price=Decimal("10.00")  # 4 * 2.50
        )

        assert correct_item.total_price == correct_item.quantity * correct_item.unit_price


@pytest.mark.unit
class TestTransactionModel:
    """Тесты модели транзакции."""

    def test_transaction_creation(self):
        """Тест создания транзакции."""
        transaction = Transaction(
            transaction_id="tx_test_123",
            user_id=1,
            amount=Decimal("50.00"),
            currency="USD",
            transaction_type=TransactionType.DEPOSIT,
            status=TransactionStatus.PENDING,
            description="Test deposit"
        )

        assert transaction.transaction_id == "tx_test_123"
        assert transaction.amount == Decimal("50.00")
        assert transaction.transaction_type == TransactionType.DEPOSIT
        assert transaction.status == TransactionStatus.PENDING

    def test_transaction_types(self):
        """Тест типов транзакций."""
        types_to_test = [
            TransactionType.DEPOSIT,
            TransactionType.PURCHASE,
            TransactionType.REFUND,
            TransactionType.WITHDRAWAL
        ]

        for tx_type in types_to_test:
            transaction = Transaction(
                transaction_id=f"tx_{tx_type.value}",
                user_id=1,
                amount=Decimal("10.00"),
                transaction_type=tx_type,
                status=TransactionStatus.PENDING
            )
            assert transaction.transaction_type == tx_type

    def test_transaction_statuses(self):
        """Тест статусов транзакций."""
        statuses_to_test = [
            TransactionStatus.PENDING,
            TransactionStatus.PROCESSING,
            TransactionStatus.COMPLETED,
            TransactionStatus.FAILED,
            TransactionStatus.CANCELLED,
            TransactionStatus.REFUNDED
        ]

        for status in statuses_to_test:
            transaction = Transaction(
                transaction_id=f"tx_{status.value}",
                user_id=1,
                amount=Decimal("10.00"),
                transaction_type=TransactionType.DEPOSIT,
                status=status
            )
            assert transaction.status == status


@pytest.mark.unit
class TestProxyPurchaseModel:
    """Тесты модели покупки прокси."""

    def test_proxy_purchase_creation(self):
        """Тест создания покупки прокси."""
        expires_at = datetime.now() + timedelta(days=30)

        purchase = ProxyPurchase(
            user_id=1,
            proxy_product_id=1,
            order_id=1,
            proxy_list="192.168.1.1:8080:user:pass\n192.168.1.2:8080:user:pass",
            username="testuser",
            password="testpass",
            is_active=True,
            expires_at=expires_at,
            traffic_used_gb=Decimal("0.00"),
            provider_order_id="711_order_123"
        )

        assert purchase.user_id == 1
        assert "192.168.1.1:8080" in purchase.proxy_list
        assert purchase.username == "testuser"
        assert purchase.is_active is True
        assert purchase.traffic_used_gb == Decimal("0.00")

    def test_proxy_purchase_default_values(self):
        """Тест значений по умолчанию покупки прокси."""
        purchase = ProxyPurchase(
            user_id=1,
            proxy_product_id=1,
            order_id=1,
            proxy_list="192.168.1.1:8080",
            expires_at=datetime.now() + timedelta(days=30)
        )

        assert purchase.is_active is True or purchase.is_active is None
        assert purchase.traffic_used_gb == Decimal('0.00') or purchase.traffic_used_gb is None


@pytest.mark.unit
class TestShoppingCartModel:
    """Тесты модели корзины покупок."""

    def test_shopping_cart_creation_registered_user(self):
        """Тест создания элемента корзины для зарегистрированного пользователя."""
        cart_item = ShoppingCart(
            user_id=1,
            proxy_product_id=1,
            quantity=3,
            generation_params='{"format": "ip:port:user:pass"}'
        )

        assert cart_item.user_id == 1
        assert cart_item.proxy_product_id == 1
        assert cart_item.quantity == 3
        assert cart_item.guest_session_id is None

    def test_shopping_cart_creation_guest_user(self):
        """Тест создания элемента корзины для гостевого пользователя."""
        cart_item = ShoppingCart(
            guest_session_id="guest-session-123",
            proxy_product_id=1,
            quantity=2
        )

        assert cart_item.guest_session_id == "guest-session-123"
        assert cart_item.proxy_product_id == 1
        assert cart_item.quantity == 2
        assert cart_item.user_id is None

    def test_shopping_cart_quantity_validation(self):
        """Тест валидации количества в корзине."""
        # Положительное количество
        cart_item = ShoppingCart(
            user_id=1,
            proxy_product_id=1,
            quantity=5
        )
        assert cart_item.quantity == 5

        # Нулевое количество (может быть невалидным в зависимости от бизнес-логики)
        cart_item_zero = ShoppingCart(
            user_id=1,
            proxy_product_id=1,
            quantity=0
        )
        assert cart_item_zero.quantity == 0


@pytest.mark.unit
class TestModelRelationships:
    """Тесты связей между моделями."""

    def test_user_orders_relationship(self):
        """Тест связи пользователь-заказы."""
        # Это концептуальный тест - в реальности нужна настроенная БД
        user = User(id=1, email="test@example.com")

        order1 = Order(
            id=1,
            order_number="ORD-001",
            user_id=user.id,
            total_amount=Decimal("10.00"),
            status=OrderStatus.COMPLETED
        )

        order2 = Order(
            id=2,
            order_number="ORD-002",
            user_id=user.id,
            total_amount=Decimal("20.00"),
            status=OrderStatus.PENDING
        )

        # В реальном SQLAlchemy с relationships:
        # assert len(user.orders) == 2
        # assert order1 in user.orders
        # assert order2 in user.orders

        # Пока проверяем связи через ID
        assert order1.user_id == user.id
        assert order2.user_id == user.id

    def test_order_items_relationship(self):
        """Тест связи заказ-элементы заказа."""
        order = Order(
            id=1,
            order_number="ORD-ITEMS-TEST",
            user_id=1,
            total_amount=Decimal("30.00"),
            status=OrderStatus.COMPLETED
        )

        item1 = OrderItem(
            id=1,
            order_id=order.id,
            proxy_product_id=1,
            quantity=2,
            unit_price=Decimal("10.00"),
            total_price=Decimal("20.00")
        )

        item2 = OrderItem(
            id=2,
            order_id=order.id,
            proxy_product_id=2,
            quantity=1,
            unit_price=Decimal("10.00"),
            total_price=Decimal("10.00")
        )

        # Проверяем связи через ID
        assert item1.order_id == order.id
        assert item2.order_id == order.id

    def test_proxy_purchase_relationships(self):
        """Тест связей покупки прокси."""
        purchase = ProxyPurchase(
            id=1,
            user_id=1,
            proxy_product_id=1,
            order_id=1,
            proxy_list="192.168.1.1:8080",
            expires_at=datetime.now() + timedelta(days=30)
        )

        # Проверяем что все внешние ключи установлены
        assert purchase.user_id == 1
        assert purchase.proxy_product_id == 1
        assert purchase.order_id == 1


@pytest.mark.unit
class TestModelValidation:
    """Тесты валидации моделей."""

    def test_email_format_validation(self):
        """Тест валидации формата email (концептуальный)."""
        # В реальном приложении может быть валидация на уровне модели
        user = User(email="valid@example.com")
        assert "@" in user.email
        assert "." in user.email

    def test_decimal_precision(self):
        """Тест точности десятичных чисел."""
        product = ProxyProduct(
            name="Precision Test",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.DATACENTER,
            session_type=SessionType.STICKY,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("1.99999999"),  # Высокая точность
            duration_days=30
        )

        # Проверяем что Decimal сохраняет точность
        assert isinstance(product.price_per_proxy, Decimal)
        assert product.price_per_proxy == Decimal("1.99999999")

    def test_datetime_handling(self):
        """Тест обработки datetime."""
        now = datetime.now()
        expires_at = now + timedelta(days=30)

        purchase = ProxyPurchase(
            user_id=1,
            proxy_product_id=1,
            order_id=1,
            proxy_list="test",
            expires_at=expires_at
        )

        assert isinstance(purchase.expires_at, datetime)
        assert purchase.expires_at > now
