import pytest
from decimal import Decimal
from sqlalchemy import text
from app.models.models import ProxyProduct, ProxyType, ProxyCategory, SessionType, ProviderType
from app.schemas.proxy_product import ProductFilter
from app.services.product_service import product_service


@pytest.mark.unit
@pytest.mark.asyncio
class TestProductService:

    async def test_get_product_by_id(self, db_session):
        """Тест получения продукта по ID"""
        # Создаем продукт с обязательным proxy_category
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

    async def test_get_products_with_filters(self, db_session):
        """Тест получения продуктов с фильтрами"""
        # ИСПРАВЛЕНО: используем text() для SQL запросов
        await db_session.execute(text("DELETE FROM proxy_products"))
        await db_session.commit()

        # Создаем продукты разных категорий
        residential = ProxyProduct(
            name="Residential Product",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.RESIDENTIAL,
            session_type=SessionType.ROTATING,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("3.00"),
            duration_days=30,
            stock_available=100,
            is_active=True
        )

        datacenter = ProxyProduct(
            name="Datacenter Product",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.DATACENTER,
            session_type=SessionType.STICKY,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("1.00"),
            duration_days=7,
            stock_available=200,
            is_active=True
        )

        db_session.add_all([residential, datacenter])
        await db_session.commit()

        # Тест фильтрации по категории
        filters = ProductFilter(proxy_category=ProxyCategory.RESIDENTIAL)
        products, total = await product_service.get_products_with_filters(
            db_session, filters, page=1, size=10
        )

        assert len(products) == 1
        assert products[0].proxy_category == ProxyCategory.RESIDENTIAL

    async def test_check_stock_availability(self, db_session):
        """Тест проверки доступности товара"""
        # Создаем продукт
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
            min_quantity=5,
            max_quantity=100,
            stock_available=50,
            is_active=True
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # Тест успешной проверки
        is_available = await product_service.check_stock_availability(
            db_session, product.id, 10
        )
        assert is_available is True

        # Тест: количество меньше минимального
        is_available = await product_service.check_stock_availability(
            db_session, product.id, 3
        )
        assert is_available is False

    async def test_get_countries(self, db_session):
        """Тест получения списка стран"""
        countries = await product_service.get_countries(db_session)
        assert isinstance(countries, list)
