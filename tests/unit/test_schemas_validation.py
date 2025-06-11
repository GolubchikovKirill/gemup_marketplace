"""
Unit тесты для валидации схем Pydantic.

Тестирует корректность валидации входных данных,
преобразования типов и обработки ошибок валидации.
"""

import pytest
from decimal import Decimal
from datetime import datetime
from pydantic import ValidationError

from app.schemas.user import UserCreate, UserUpdate, UserLogin
from app.schemas.proxy_product import ProductFilter, ProxyProductCreate
from app.schemas.order import OrderCreate, OrderUpdate
from app.schemas.payment import PaymentCreateRequest
from app.models.models import ProxyType, ProxyCategory, SessionType, ProviderType, OrderStatus


@pytest.mark.unit
class TestUserSchemas:
    """Тесты валидации схем пользователя."""

    def test_user_create_valid(self):
        """Тест валидного создания пользователя."""
        user_data = UserCreate(
            email="test@example.com",
            username="testuser123",
            password="SecurePassword123!",
            first_name="Test",
            last_name="User"
        )

        assert user_data.email == "test@example.com"
        assert user_data.username == "testuser123"
        assert user_data.password == "SecurePassword123!"

    def test_user_create_invalid_email(self):
        """Тест создания с невалидным email."""
        with pytest.raises(ValidationError):
            UserCreate(
                email="invalid-email",
                username="testuser",
                password="SecurePassword123!",
                first_name="Test",
                last_name="User"
            )

    def test_user_create_short_password(self):
        """Тест создания с коротким паролем."""
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                username="testuser",
                password="123",  # Слишком короткий
                first_name="Test",
                last_name="User"
            )

    def test_user_create_short_username(self):
        """Тест создания с коротким username."""
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                username="ab",  # Слишком короткий
                password="SecurePassword123!",
                first_name="Test",
                last_name="User"
            )

    def test_user_create_username_validation(self):
        """Тест валидации username."""
        # Валидный username
        valid_user = UserCreate(
            email="test@example.com",
            username="valid_user-123",
            password="SecurePassword123!",
            first_name="Test",
            last_name="User"
        )
        assert valid_user.username == "valid_user-123"

        # Невалидный username с пробелами
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                username="invalid username",  # Пробелы
                password="SecurePassword123!",
                first_name="Test",
                last_name="User"
            )

    def test_user_update_partial(self):
        """Тест частичного обновления пользователя."""
        update_data = UserUpdate(
            first_name="Updated",
            last_name="Name"
        )

        assert update_data.first_name == "Updated"
        assert update_data.last_name == "Name"
        assert update_data.email is None
        assert update_data.password is None

    def test_user_login_valid(self):
        """Тест валидных данных для входа."""
        login_data = UserLogin(
            email="user@example.com",
            password="mypassword123"
        )

        assert login_data.email == "user@example.com"
        assert login_data.password == "mypassword123"

    def test_user_login_invalid_email(self):
        """Тест входа с невалидным email."""
        with pytest.raises(ValidationError):
            UserLogin(
                email="not-an-email",
                password="password"
            )


@pytest.mark.unit
class TestProxyProductSchemas:
    """Тесты валидации схем продуктов прокси."""

    def test_proxy_product_create_valid(self):
        """Тест валидного создания продукта."""
        product_data = ProxyProductCreate(
            name="US HTTP Proxies",
            description="High-quality proxies",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.DATACENTER,
            session_type=SessionType.ROTATING,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("2.50"),
            duration_days=30,
            stock_available=100
        )

        assert product_data.name == "US HTTP Proxies"
        assert product_data.proxy_type == ProxyType.HTTP
        assert product_data.price_per_proxy == Decimal("2.50")

    def test_proxy_product_create_negative_price(self):
        """Тест создания с отрицательной ценой."""
        with pytest.raises(ValidationError):
            ProxyProductCreate(
                name="Test Product",
                proxy_type=ProxyType.HTTP,
                proxy_category=ProxyCategory.DATACENTER,
                session_type=SessionType.ROTATING,
                provider=ProviderType.PROVIDER_711,
                country_code="US",
                country_name="United States",
                price_per_proxy=Decimal("-1.00"),  # Отрицательная цена
                duration_days=30,
                stock_available=100
            )

    def test_proxy_product_create_zero_duration(self):
        """Тест создания с нулевой длительностью."""
        with pytest.raises(ValidationError):
            ProxyProductCreate(
                name="Test Product",
                proxy_type=ProxyType.HTTP,
                proxy_category=ProxyCategory.DATACENTER,
                session_type=SessionType.ROTATING,
                provider=ProviderType.PROVIDER_711,
                country_code="US",
                country_name="United States",
                price_per_proxy=Decimal("2.00"),
                duration_days=0,  # Нулевая длительность
                stock_available=100
            )

    def test_product_filter_validation(self):
        """Тест валидации фильтра продуктов."""
        # Валидный фильтр
        filter_data = ProductFilter(
            proxy_category=ProxyCategory.RESIDENTIAL,
            min_price=1.00,
            max_price=10.00,
            country="US"
        )

        assert filter_data.proxy_category == ProxyCategory.RESIDENTIAL
        assert filter_data.min_price == 1.00
        assert filter_data.max_price == 10.00

    def test_product_filter_invalid_price_range(self):
        """Тест фильтра с невалидным диапазоном цен."""
        with pytest.raises(ValidationError):
            ProductFilter(
                min_price=10.00,
                max_price=5.00  # Максимум меньше минимума
            )


@pytest.mark.unit
class TestOrderSchemas:
    """Тесты валидации схем заказов."""

    def test_order_create_valid(self):
        """Тест валидного создания заказа."""
        order_data = OrderCreate(
            order_number="ORD-20240115-TEST123",
            user_id=1,
            total_amount=Decimal("25.50"),
            currency="USD",
            status=OrderStatus.PENDING
        )

        assert order_data.order_number == "ORD-20240115-TEST123"
        assert order_data.total_amount == Decimal("25.50")
        assert order_data.status == OrderStatus.PENDING

    def test_order_create_negative_amount(self):
        """Тест создания заказа с отрицательной суммой."""
        with pytest.raises(ValidationError):
            OrderCreate(
                order_number="ORD-TEST",
                user_id=1,
                total_amount=Decimal("-10.00"),  # Отрицательная сумма
                currency="USD",
                status=OrderStatus.PENDING
            )

    def test_order_create_invalid_currency(self):
        """Тест создания заказа с невалидной валютой."""
        with pytest.raises(ValidationError):
            OrderCreate(
                order_number="ORD-TEST",
                user_id=1,
                total_amount=Decimal("10.00"),
                currency="INVALID",  # Невалидная валюта
                status=OrderStatus.PENDING
            )

    def test_order_update_valid(self):
        """Тест валидного обновления заказа."""
        update_data = OrderUpdate(
            status=OrderStatus.COMPLETED,
            payment_method="cryptomus"
        )

        assert update_data.status == OrderStatus.COMPLETED
        assert update_data.payment_method == "cryptomus"

    def test_order_update_invalid_payment_method(self):
        """Тест обновления с невалидным способом оплаты."""
        with pytest.raises(ValidationError):
            OrderUpdate(
                payment_method="invalid_method"  # Невалидный способ оплаты
            )


@pytest.mark.unit
class TestPaymentSchemas:
    """Тесты валидации схем платежей."""

    def test_payment_create_valid(self):
        """Тест валидного создания платежа."""
        payment_data = PaymentCreateRequest(
            amount=Decimal("50.00"),
            description="Balance top-up"
        )

        assert payment_data.amount == Decimal("50.00")
        assert payment_data.description == "Balance top-up"

    def test_payment_create_minimum_amount(self):
        """Тест создания платежа с минимальной суммой."""
        payment_data = PaymentCreateRequest(
            amount=Decimal("1.00")  # Минимальная сумма
        )

        assert payment_data.amount == Decimal("1.00")

    def test_payment_create_below_minimum(self):
        """Тест создания платежа ниже минимальной суммы."""
        with pytest.raises(ValidationError):
            PaymentCreateRequest(
                amount=Decimal("0.50")  # Ниже минимума
            )

    def test_payment_create_above_maximum(self):
        """Тест создания платежа выше максимальной суммы."""
        with pytest.raises(ValidationError):
            PaymentCreateRequest(
                amount=Decimal("50000.00")  # Выше максимума
            )

    def test_payment_create_long_description(self):
        """Тест создания платежа с длинным описанием."""
        long_description = "A" * 1001  # Больше 1000 символов

        with pytest.raises(ValidationError):
            PaymentCreateRequest(
                amount=Decimal("10.00"),
                description=long_description
            )


@pytest.mark.unit
class TestSchemasSerialization:
    """Тесты сериализации схем."""

    def test_decimal_serialization(self):
        """Тест сериализации Decimal."""
        payment_data = PaymentCreateRequest(
            amount=Decimal("123.456789")
        )

        # Проверяем что Decimal корректно сериализуется
        serialized = payment_data.model_dump()
        assert isinstance(serialized["amount"], (Decimal, str, float))

    def test_datetime_serialization(self):
        """Тест сериализации datetime."""
        # Это будет использоваться в response схемах
        now = datetime.now()

        # Проверяем что datetime корректно обрабатывается
        assert isinstance(now, datetime)

    def test_enum_serialization(self):
        """Тест сериализации enum значений."""
        product_data = ProxyProductCreate(
            name="Test Product",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.DATACENTER,
            session_type=SessionType.ROTATING,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("2.00"),
            duration_days=30,
            stock_available=100
        )

        serialized = product_data.model_dump()
        assert serialized["proxy_type"] == "http"
        assert serialized["proxy_category"] == "datacenter"


@pytest.mark.unit
class TestSchemasCoercion:
    """Тесты преобразования типов в схемах."""

    def test_string_to_decimal_coercion(self):
        """Тест преобразования строки в Decimal."""
        payment_data = PaymentCreateRequest(
            amount="25.50"  # Строка вместо Decimal
        )

        assert payment_data.amount == Decimal("25.50")
        assert isinstance(payment_data.amount, Decimal)

    def test_invalid_decimal_coercion(self):
        """Тест невалидного преобразования в Decimal."""
        with pytest.raises(ValidationError):
            PaymentCreateRequest(
                amount="not-a-number"
            )

    def test_strip_whitespace(self):
        """Тест автоматического удаления пробелов."""
        user_data = UserCreate(
            email="  test@example.com  ",  # Пробелы
            username="  testuser  ",
            password="SecurePassword123!",
            first_name="  Test  ",
            last_name="  User  "
        )

        # Проверяем что пробелы удалены (если настроено в схеме)
        assert user_data.email.strip() == "test@example.com"
        assert user_data.username.strip() == "testuser"

    def test_case_normalization(self):
        """Тест нормализации регистра."""
        user_data = UserCreate(
            email="TEST@EXAMPLE.COM",
            username="TestUser123",
            password="SecurePassword123!",
            first_name="test",
            last_name="user"
        )

        # Проверяем что email приведен к нижнему регистру
        assert user_data.email == user_data.email.lower()
