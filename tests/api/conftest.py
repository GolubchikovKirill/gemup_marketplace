from decimal import Decimal
from unittest.mock import patch, AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.main import app
from app.models.models import ProxyProduct, ProxyType, ProxyCategory, SessionType, ProviderType


@pytest.fixture
def api_client(db_session: AsyncSession):
    """FastAPI TestClient для HTTP тестов с изолированной БД"""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_external_apis():
    """Автоматически мокаем все внешние API для всех тестов"""
    with patch('app.integrations.cryptomus.CryptomusAPI') as mock_cryptomus, \
            patch('app.integrations.proxy_711.Proxy711API') as mock_711:
        mock_cryptomus_instance = AsyncMock()
        mock_cryptomus.return_value = mock_cryptomus_instance
        mock_cryptomus_instance.create_payment.return_value = {
            "transaction_id": "test_txn_123",
            "payment_url": "https://test.cryptomus.com/pay/test",
            "amount": "50.00",
            "currency": "USD",
            "status": "pending"
        }

        mock_711_instance = AsyncMock()
        mock_711.return_value = mock_711_instance
        mock_711_instance.purchase_proxies.return_value = {
            "order_id": "711-test-123",
            "proxies": ["1.2.3.4:8080", "5.6.7.8:8080"],
            "username": "test_user",
            "password": "test_pass"
        }

        yield


@pytest.fixture
def test_product(db_session: AsyncSession):
    """Создание тестового продукта - СИНХРОННАЯ фикстура"""
    import asyncio

    async def create_product():
        product = ProxyProduct(
            name="Test API Product",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.DATACENTER,
            session_type=SessionType.STICKY,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("2.00"),
            duration_days=30,
            min_quantity=1,
            max_quantity=100,
            stock_available=50,
            is_active=True
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)
        return product

    # Выполняем асинхронную функцию синхронно
    return asyncio.get_event_loop().run_until_complete(create_product())


@pytest.fixture
def test_nodepay_product(db_session: AsyncSession):
    """Создание тестового Nodepay продукта - СИНХРОННАЯ фикстура"""
    import asyncio

    async def create_product():
        product = ProxyProduct(
            name="Nodepay Farming Proxy",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.NODEPAY,
            session_type=SessionType.STICKY,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("5.00"),
            duration_days=30,
            points_per_hour=120,
            farm_efficiency=Decimal("95.5"),
            auto_claim=True,
            multi_account_support=True,
            min_quantity=1,
            max_quantity=50,
            stock_available=25,
            is_active=True
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)
        return product

    return asyncio.get_event_loop().run_until_complete(create_product())


@pytest.fixture
def auth_headers(api_client: TestClient, test_user):
    """Получение заголовков авторизации - СИНХРОННАЯ фикстура"""
    login_data = {
        "username": test_user.email,
        "password": "testpassword123"
    }

    response = api_client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200

    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_with_balance(test_user, db_session: AsyncSession):
    """Пользователь с балансом - СИНХРОННАЯ фикстура"""
    import asyncio

    async def update_balance():
        test_user.balance = Decimal("100.00")
        await db_session.commit()
        await db_session.refresh(test_user)
        return test_user

    return asyncio.get_event_loop().run_until_complete(update_balance())
