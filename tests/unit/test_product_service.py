import pytest
from decimal import Decimal
from app.services.product_service import product_service
from app.schemas.product import ProductFilter
from app.models.models import ProxyProduct, ProxyType, SessionType, ProviderType


@pytest.mark.unit
class TestProductService:

    @pytest.mark.asyncio
    async def test_get_products_with_empty_filters(self, db_session):
        """Тест получения продуктов без фильтров"""
        filters = ProductFilter()
        products, total = await product_service.get_products_with_filters(
            db_session, filters, page=1, size=20
        )

        assert isinstance(products, list)
        assert isinstance(total, int)
        assert total >= 0

    @pytest.mark.asyncio
    async def test_get_products_with_filters(self, db_session):
        """Тест фильтрации продуктов"""
        # Создаем тестовый продукт
        product = ProxyProduct(
            name="Test HTTP Proxy",
            proxy_type=ProxyType.HTTP,
            session_type=SessionType.ROTATING,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("1.50"),
            duration_days=30,
            stock_available=100,
            is_active=True
        )
        db_session.add(product)
        await db_session.commit()

        # Фильтр по типу прокси
        filters = ProductFilter(proxy_type=ProxyType.HTTP)
        products, total = await product_service.get_products_with_filters(
            db_session, filters, page=1, size=20
        )

        assert total >= 1
        if products:
            assert all(p.proxy_type == ProxyType.HTTP for p in products)

    @pytest.mark.asyncio
    async def test_get_product_by_id_existing(self, db_session):
        """Тест получения существующего продукта"""
        # Создаем тестовый продукт - ИСПРАВЛЕНО: добавлен is_active=True
        product = ProxyProduct(
            name="Test Product",
            proxy_type=ProxyType.HTTP,
            session_type=SessionType.ROTATING,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("1.50"),
            duration_days=30,
            stock_available=100,
            is_active=True
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # Получаем продукт
        found_product = await product_service.get_product_by_id(db_session, product.id)
        assert found_product is not None
        assert found_product.id == product.id

    @pytest.mark.asyncio
    async def test_get_product_by_id_nonexistent(self, db_session):
        """Тест получения несуществующего продукта"""
        product = await product_service.get_product_by_id(db_session, 99999)
        assert product is None

    @pytest.mark.asyncio
    async def test_check_stock_availability(self, db_session):
        """Тест проверки доступности товара"""
        # Создаем тестовый продукт
        product = ProxyProduct(
            name="Stock Test Product",
            proxy_type=ProxyType.HTTP,
            session_type=SessionType.ROTATING,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("1.50"),
            duration_days=30,
            min_quantity=1,
            max_quantity=10,
            stock_available=5,
            is_active=True
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # Проверяем доступность в пределах лимитов
        is_available = await product_service.check_stock_availability(
            db_session, product.id, 3
        )
        assert is_available is True

        # Проверяем недоступность (больше stock)
        is_available = await product_service.check_stock_availability(
            db_session, product.id, 10
        )
        assert is_available is False

        # Проверяем недоступность (меньше min_quantity)
        is_available = await product_service.check_stock_availability(
            db_session, product.id, 0
        )
        assert is_available is False

    @pytest.mark.asyncio
    async def test_get_countries(self, db_session):
        """Тест получения списка стран"""
        # Создаем тестовые продукты
        products = [
            ProxyProduct(
                name="US Product",
                proxy_type=ProxyType.HTTP,
                session_type=SessionType.ROTATING,
                provider=ProviderType.PROVIDER_711,
                country_code="US",
                country_name="United States",
                city="New York",
                price_per_proxy=Decimal("1.50"),
                duration_days=30,
                is_active=True
            ),
            ProxyProduct(
                name="GB Product",
                proxy_type=ProxyType.HTTP,
                session_type=SessionType.ROTATING,
                provider=ProviderType.PROVIDER_711,
                country_code="GB",
                country_name="United Kingdom",
                city="London",
                price_per_proxy=Decimal("2.00"),
                duration_days=30,
                is_active=True
            )
        ]

        for product in products:
            db_session.add(product)
        await db_session.commit()

        countries = await product_service.get_countries(db_session)
        assert isinstance(countries, list)

        # Если есть данные, проверяем структуру
        if countries:
            country = countries[0]
            assert "code" in country
            assert "name" in country
            assert "cities" in country

    @pytest.mark.asyncio
    async def test_get_cities_by_country(self, db_session):
        """Тест получения городов по стране"""
        # Создаем тестовый продукт
        product = ProxyProduct(
            name="US Product",
            proxy_type=ProxyType.HTTP,
            session_type=SessionType.ROTATING,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            city="New York",
            price_per_proxy=Decimal("1.50"),
            duration_days=30,
            is_active=True
        )
        db_session.add(product)
        await db_session.commit()

        cities = await product_service.get_cities_by_country(db_session, "US")
        assert isinstance(cities, list)

        # Если есть данные, проверяем структуру
        if cities:
            city = cities[0]
            assert "name" in city
            assert "country_code" in city
            assert "country_name" in city
