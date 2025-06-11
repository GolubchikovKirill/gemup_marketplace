"""
Центральная конфигурация pytest с фикстурами для тестирования.

Обеспечивает изолированную тестовую среду с отдельной БД,
фикстурами для пользователей, продуктов и других тестовых данных.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Generator, AsyncGenerator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import get_db
from app.core.main import app
from app.models.models import (
    Base, User, ProxyProduct, Order, OrderItem, Transaction, ProxyPurchase,
    ProxyType, ProxyCategory, SessionType, ProviderType, OrderStatus, TransactionType
)
from app.schemas.user import UserCreate, GuestUserCreate

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    poolclass=StaticPool,
    connect_args={
        "check_same_thread": False,
    },
)

TestingSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a fresh database session for each test.
    Ensures complete isolation between tests.
    """
    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
def client(db_session: AsyncSession) -> Generator[TestClient, None, None]:
    """
    Create a test client with dependency injection.
    """

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Create an async test client for testing async endpoints.
    """

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test registered user."""
    from app.crud.user import user_crud

    unique_id = str(uuid.uuid4())[:8]
    user_data = UserCreate(
        email=f"testuser-{unique_id}@example.com",
        username=f"testuser-{unique_id}",
        password="testpassword123",
        first_name="Test",
        last_name="User"
    )

    user = await user_crud.create_registered_user(db_session, user_in=user_data)
    return user


@pytest_asyncio.fixture
async def test_admin_user(db_session: AsyncSession) -> User:
    """Create a test admin user."""
    from app.crud.user import user_crud

    unique_id = str(uuid.uuid4())[:8]
    user_data = UserCreate(
        email=f"admin-{unique_id}@example.com",
        username=f"admin-{unique_id}",
        password="adminpassword123",
        first_name="Admin",
        last_name="User"
    )

    user = await user_crud.create_registered_user(db_session, user_in=user_data)
    user.is_admin = True  # Если есть такое поле
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def test_guest_user(db_session: AsyncSession) -> User:
    """Create a test guest user."""
    from app.crud.user import user_crud

    session_id = f"guest-session-{str(uuid.uuid4())[:8]}"
    guest_data = GuestUserCreate(session_id=session_id)

    guest = await user_crud.create_guest_user(db_session, obj_in=guest_data)
    return guest


@pytest_asyncio.fixture
async def test_proxy_product(db_session: AsyncSession) -> ProxyProduct:
    """Create a test proxy product."""
    product = ProxyProduct(
        name="Test US HTTP Proxies",
        description="High-quality test proxies for automated testing",
        proxy_type=ProxyType.HTTP,
        proxy_category=ProxyCategory.DATACENTER,
        session_type=SessionType.ROTATING,
        provider=ProviderType.PROVIDER_711,
        country_code="US",
        country_name="United States",
        city="New York",
        price_per_proxy=Decimal("2.00"),
        price_per_gb=Decimal("0.50"),
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
        is_featured=True,
        provider_product_id="711_test_product_123"
    )

    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def test_order(db_session: AsyncSession, test_user: User, test_proxy_product: ProxyProduct) -> Order:
    """Create a test order with order items."""
    unique_id = str(uuid.uuid4())[:8]

    order = Order(
        order_number=f"ORD-TEST-{unique_id}",
        user_id=test_user.id,
        total_amount=Decimal("10.00"),
        currency="USD",
        status=OrderStatus.PENDING,
        payment_method="balance"
    )

    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    # Add order item
    order_item = OrderItem(
        order_id=order.id,
        proxy_product_id=test_proxy_product.id,
        quantity=5,
        unit_price=Decimal("2.00"),
        total_price=Decimal("10.00"),
        generation_params='{"format": "ip:port:user:pass"}'
    )

    db_session.add(order_item)
    await db_session.commit()

    return order


@pytest_asyncio.fixture
async def test_transaction(db_session: AsyncSession, test_user: User, test_order: Order) -> Transaction:
    """Create a test transaction."""
    from app.crud.transaction import transaction_crud

    transaction = await transaction_crud.create_transaction(
        db_session,
        user_id=test_user.id,
        amount=Decimal("10.00"),
        currency="USD",
        transaction_type=TransactionType.DEPOSIT,
        description="Test transaction",
        order_id=test_order.id
    )

    return transaction


@pytest_asyncio.fixture
async def test_proxy_purchase(db_session: AsyncSession, test_user: User, test_order: Order,
                              test_proxy_product: ProxyProduct) -> ProxyPurchase:
    """Create a test proxy purchase."""
    from app.crud.proxy_purchase import proxy_purchase_crud

    expires_at = datetime.now() + timedelta(days=30)

    purchase = await proxy_purchase_crud.create_purchase(
        db_session,
        user_id=test_user.id,
        proxy_product_id=test_proxy_product.id,
        order_id=test_order.id,
        proxy_list="192.168.1.1:8080:testuser:testpass\n192.168.1.2:8080:testuser:testpass",
        username="testuser",
        password="testpass",
        expires_at=expires_at,
        provider_order_id="711_test_order_456"
    )

    return purchase


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """Create authorization headers for authenticated requests."""
    from app.core.auth import auth_handler

    access_token = auth_handler.create_access_token(
        data={"sub": str(test_user.id), "type": "access"}
    )

    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def admin_headers(test_admin_user: User) -> dict:
    """Create authorization headers for admin requests."""
    from app.core.auth import auth_handler

    access_token = auth_handler.create_access_token(
        data={"sub": str(test_admin_user.id), "type": "access"}
    )

    return {"Authorization": f"Bearer {access_token}"}


# Мок данные для тестирования
class MockData:
    """Mock data for testing external APIs."""

    @staticmethod
    def cryptomus_success_response():
        return {
            'state': 0,
            'result': {
                'uuid': 'test-payment-uuid-123',
                'url': 'https://pay.cryptomus.com/pay/test-payment-uuid-123'
            }
        }

    @staticmethod
    def proxy_711_success_response():
        return {
            "success": True,
            "order_id": "711_test_order_789",
            "proxies": "203.0.113.1:8080:user123:pass456\n203.0.113.2:8080:user123:pass456",
            "username": "user123",
            "password": "pass456",
            "expires_at": "2025-03-01T00:00:00Z",
            "status": "active"
        }

    @staticmethod
    def webhook_data(order_id: str = "test-transaction-123"):
        return {
            "order_id": order_id,
            "status": "paid",
            "amount": "25.00",
            "currency": "USD",
            "sign": "valid_test_signature"
        }


# Pytest markers
pytest_plugins = ["pytest_asyncio"]


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "crud: mark test as a CRUD test")
    config.addinivalue_line("markers", "api: mark test as an API test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "external: mark test as requiring external services")


# Test database cleanup
@pytest.fixture(autouse=True)
async def cleanup_database(db_session: AsyncSession):
    """Clean up database after each test."""
    yield
    # This will be called after each test
    await db_session.rollback()


# Mock external services
@pytest.fixture
def mock_cryptomus_api():
    """Mock Cryptomus API responses."""
    from unittest.mock import patch

    with patch('app.integrations.cryptomus.cryptomus_api') as mock:
        mock.create_payment.return_value = MockData.cryptomus_success_response()
        yield mock


@pytest.fixture
def mock_proxy_711_api():
    """Mock 711Proxy API responses."""
    from unittest.mock import patch

    with patch('app.integrations.proxy_711.proxy_711_api') as mock:
        mock.purchase_proxies.return_value = MockData.proxy_711_success_response()
        yield mock


# Performance testing fixtures
@pytest.fixture
def performance_timer():
    """Timer for performance testing."""
    import time

    class Timer:
        def __init__(self):
            self.start_time = None

        def start(self):
            self.start_time = time.time()

        def elapsed(self):
            if self.start_time is None:
                return 0
            return time.time() - self.start_time

    return Timer()


# Redis fixture (если используется)
@pytest_asyncio.fixture
async def redis_client():
    """Create Redis client for testing."""
    try:
        from app.core.redis import redis_client
        await redis_client.connect()
        yield redis_client
        await redis_client.disconnect()
    except ImportError:
        # Redis not configured
        yield None
