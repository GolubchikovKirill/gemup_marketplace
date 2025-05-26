import pytest
from datetime import datetime, timedelta
from app.models.models import User, ProxyProduct, ProxyType, SessionType, ProviderType


@pytest.mark.unit
class TestUserModel:

    def test_user_creation(self):
        """Тест создания модели пользователя"""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password",
            first_name="Test",
            last_name="User"
        )

        assert user.email == "test@example.com"
        assert user.is_guest == False
        assert user.is_active == True
        assert user.balance == 0.0

    def test_guest_user_creation(self):
        """Тест создания гостевого пользователя"""
        expires_at = datetime.now() + timedelta(hours=24)

        guest = User(
            is_guest=True,
            guest_session_id="session-123",
            guest_expires_at=expires_at
        )

        assert guest.is_guest == True
        assert guest.guest_session_id == "session-123"
        assert guest.email is None


@pytest.mark.unit
class TestProxyProductModel:

    def test_proxy_product_creation(self):
        """Тест создания модели продукта прокси"""
        product = ProxyProduct(
            name="US HTTP Proxies",
            description="High-quality US HTTP proxies",
            proxy_type=ProxyType.HTTP,
            session_type=SessionType.ROTATING,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            city="New York",
            price_per_proxy=1.50,
            stock_available=1000
        )

        assert product.name == "US HTTP Proxies"
        assert product.proxy_type == ProxyType.HTTP
        assert product.price_per_proxy == 1.50
        assert product.is_active == True
