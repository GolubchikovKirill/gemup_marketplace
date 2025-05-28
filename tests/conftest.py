from decimal import Decimal
from typing import AsyncGenerator

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import get_db, Base
from app.core.main import app
from app.crud.user import user_crud
from app.schemas.user import UserCreate

# Тестовая база данных в памяти
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Создание тестового движка базы данных"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(test_engine):
    """Создание фабрики сессий"""
    return async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )


@pytest_asyncio.fixture
async def db_session(session_factory) -> AsyncGenerator[AsyncSession, None]:
    """Создание тестовой сессии базы данных"""
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Создание тестового HTTP клиента"""
    # Используем один и тот же db_session для всех запросов!
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    from httpx import ASGITransport
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    """Создание тестового пользователя"""
    import uuid
    unique_id = str(uuid.uuid4())[:8]

    user_data = UserCreate(
        email=f"test-{unique_id}@example.com",
        username=f"testuser-{unique_id}",
        password="testpassword123",
        first_name="Test",
        last_name="User"
    )

    user = await user_crud.create_registered_user(db_session, user_in=user_data)
    # Устанавливаем достаточный баланс для тестов
    user.balance = Decimal("100.00")
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_guest_user(db_session: AsyncSession):
    """Создание тестового гостевого пользователя"""
    import uuid
    session_id = f"test-session-{str(uuid.uuid4())[:8]}"

    guest = await user_crud.create_guest_user(db_session, session_id=session_id)
    await db_session.commit()
    await db_session.refresh(guest)
    return guest


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, test_user):
    """Создание заголовков авторизации"""
    login_data = {
        "username": test_user.email,
        "password": "testpassword123"
    }

    response = await client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200, f"Login failed: {response.text}"

    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
