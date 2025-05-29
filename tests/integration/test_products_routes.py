import pytest
from httpx import AsyncClient
from decimal import Decimal
from sqlalchemy import text
from app.models.models import ProxyProduct, ProxyType, ProxyCategory, SessionType, ProviderType


@pytest.mark.integration
@pytest.mark.api
class TestProductsAPI:

    @pytest.mark.asyncio
    async def test_get_products_empty(self, client: AsyncClient):
        """Тест получения пустого списка продуктов"""
        response = await client.get("/api/v1/products/")
        assert response.status_code == 200

        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_get_products_with_category_filter(self, client: AsyncClient, db_session):
        """Тест фильтрации по категории прокси"""
        # ИСПРАВЛЕНО: используем text() для SQL запросов
        await db_session.execute(text("DELETE FROM proxy_products"))
        await db_session.commit()

        # Создаем продукты разных категорий
        residential = ProxyProduct(
            name="Residential Proxy",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.RESIDENTIAL,
            session_type=SessionType.ROTATING,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("3.00"),
            duration_days=30,
            is_active=True,
            stock_available=100
        )

        db_session.add(residential)
        await db_session.commit()

        # Тест фильтрации по residential
        response = await client.get("/api/v1/products/?proxy_category=residential")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        # ИСПРАВЛЕНО: проверяем правильное поле в ответе
        product_data = data["items"][0]
        assert "proxy_category" in product_data
        assert product_data["proxy_category"] == "residential"

    @pytest.mark.asyncio
    async def test_get_products_with_speed_and_uptime_filters(self, client: AsyncClient, db_session):
        """Тест фильтрации по скорости и uptime"""
        # ИСПРАВЛЕНО: используем text() для SQL запросов
        await db_session.execute(text("DELETE FROM proxy_products"))
        await db_session.commit()

        product = ProxyProduct(
            name="High Performance Proxy",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.ISP,
            session_type=SessionType.STICKY,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("2.50"),
            duration_days=30,
            speed_mbps=100,
            uptime_guarantee=Decimal("99.9"),
            is_active=True,
            stock_available=50
        )

        db_session.add(product)
        await db_session.commit()

        # Тест фильтрации по скорости
        response = await client.get("/api/v1/products/?min_speed=50")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        product_data = data["items"][0]
        # ИСПРАВЛЕНО: проверяем правильные поля в ответе
        assert "speed_mbps" in product_data
        assert product_data["speed_mbps"] == 100

    @pytest.mark.asyncio
    async def test_get_categories_stats(self, client: AsyncClient, db_session):
        """Тест получения статистики по категориям"""
        # ИСПРАВЛЕНО: используем text() для SQL запросов
        await db_session.execute(text("DELETE FROM proxy_products"))
        await db_session.commit()

        # Создаем продукты разных категорий
        products = [
            ProxyProduct(
                name=f"Residential {i}",
                proxy_type=ProxyType.HTTP,
                proxy_category=ProxyCategory.RESIDENTIAL,
                session_type=SessionType.ROTATING,
                provider=ProviderType.PROVIDER_711,
                country_code="US",
                country_name="United States",
                price_per_proxy=Decimal(f"{2 + i}.00"),
                duration_days=30,
                is_active=True,
                stock_available=100
            ) for i in range(3)
        ]

        db_session.add_all(products)
        await db_session.commit()

        response = await client.get("/api/v1/products/categories/stats")
        assert response.status_code == 200
        data = response.json()

        assert "residential" in data
        assert data["residential"]["count"] == 3

    @pytest.mark.asyncio
    async def test_get_products_by_category(self, client: AsyncClient, db_session):
        """Тест получения продуктов по категории"""
        # ИСПРАВЛЕНО: используем text() для SQL запросов
        await db_session.execute(text("DELETE FROM proxy_products"))
        await db_session.commit()

        product = ProxyProduct(
            name="Test Residential",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.RESIDENTIAL,
            session_type=SessionType.ROTATING,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("3.00"),
            duration_days=30,
            is_active=True,
            stock_available=100
        )

        db_session.add(product)
        await db_session.commit()

        response = await client.get("/api/v1/products/categories/residential")
        assert response.status_code == 200
        data = response.json()

        assert data["category"] == "residential"
        assert len(data["products"]) == 1

    @pytest.mark.asyncio
    async def test_get_product_by_id(self, client: AsyncClient, db_session):
        """Тест получения продукта по ID"""
        product = ProxyProduct(
            name="Test Product",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.DATACENTER,
            session_type=SessionType.STICKY,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("1.50"),
            duration_days=30,
            is_active=True,
            stock_available=100
        )

        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        response = await client.get(f"/api/v1/products/{product.id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == product.id
        assert data["name"] == "Test Product"

    @pytest.mark.asyncio
    async def test_get_countries(self, client: AsyncClient, db_session):
        """Тест получения списка стран"""
        # Создаем продукт для теста
        product = ProxyProduct(
            name="Test Product",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.DATACENTER,
            session_type=SessionType.STICKY,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("1.50"),
            duration_days=30,
            is_active=True,
            stock_available=100
        )

        db_session.add(product)
        await db_session.commit()

        response = await client.get("/api/v1/products/meta/countries")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_check_product_availability(self, client: AsyncClient, db_session):
        """Тест проверки доступности товара"""
        product = ProxyProduct(
            name="Test Product",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.DATACENTER,
            session_type=SessionType.STICKY,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("1.50"),
            duration_days=30,
            min_quantity=1,
            max_quantity=100,
            stock_available=50,
            is_active=True
        )

        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        response = await client.get(f"/api/v1/products/{product.id}/availability?quantity=10")
        assert response.status_code == 200

        data = response.json()
        assert data["is_available"] is True
        assert data["stock_available"] == 50
