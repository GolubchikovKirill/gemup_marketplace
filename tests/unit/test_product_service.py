import pytest
from decimal import Decimal
from sqlalchemy import text

from app.models.models import ProxyProduct, ProxyCategory, ProxyType, SessionType, ProviderType
from app.schemas.proxy_product import ProductFilter
from app.services.product_service import product_service


@pytest.mark.unit
@pytest.mark.asyncio
class TestProductService:

    async def test_get_products_with_filters(self, db_session):
        """Тест получения продуктов с фильтрами"""
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

        # ИСПРАВЛЕНО: используем правильное имя метода
        filters = ProductFilter(proxy_category=ProxyCategory.RESIDENTIAL)
        products, total = await product_service.get_products_with_filter(
            db_session, filter_params=filters, skip=0, limit=10
        )

        assert len(products) == 1
        assert products[0].proxy_category == ProxyCategory.RESIDENTIAL
        assert total == 1

    async def test_check_stock_availability(self, db_session):
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
            min_quantity=5,
            max_quantity=100,
            stock_available=50,
            is_active=True
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # ИСПРАВЛЕНО: используем правильное имя метода
        availability = await product_service.check_availability(
            db_session, product_id=product.id, quantity=10
        )

        assert availability["is_available"] is True
        assert availability["stock_available"] == 50

    async def test_get_countries(self, db_session):
        """Тест получения списка стран"""
        # ИСПРАВЛЕНО: используем правильное имя метода
        countries = await product_service.get_available_countries(db_session)
        assert isinstance(countries, list)
