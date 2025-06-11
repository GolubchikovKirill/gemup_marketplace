"""
Unit тесты для сервиса продуктов.

Тестирует получение продуктов с фильтрацией, проверку доступности,
управление каталогом и статистику продуктов.
"""

from decimal import Decimal

import pytest
from sqlalchemy import text

from app.core.exceptions import BusinessLogicError
from app.models.models import (
    ProxyProduct, ProxyCategory, ProxyType, SessionType, ProviderType
)
from app.schemas.proxy_product import ProductFilter
from app.services.product_service import product_service


@pytest.mark.unit
@pytest.mark.asyncio
class TestProductService:
    """Тесты сервиса продуктов."""

    async def test_get_products_without_filters(self, db_session):
        """Тест получения всех продуктов без фильтров."""
        # Очищаем таблицу и создаем тестовые продукты
        await db_session.execute(text("DELETE FROM proxy_products"))
        await db_session.commit()

        products_data = [
            {
                "name": "US HTTP Proxies",
                "proxy_category": ProxyCategory.DATACENTER,
                "country_code": "US",
                "price_per_proxy": Decimal("2.00")
            },
            {
                "name": "UK HTTPS Proxies",
                "proxy_category": ProxyCategory.RESIDENTIAL,
                "country_code": "UK",
                "price_per_proxy": Decimal("3.50")
            }
        ]

        for data in products_data:
            product = ProxyProduct(
                name=data["name"],
                proxy_type=ProxyType.HTTP,
                proxy_category=data["proxy_category"],
                session_type=SessionType.ROTATING,
                provider=ProviderType.PROVIDER_711,
                country_code=data["country_code"],
                country_name="Test Country",
                price_per_proxy=data["price_per_proxy"],
                duration_days=30,
                stock_available=100,
                is_active=True
            )
            db_session.add(product)

        await db_session.commit()

        # Получаем продукты без фильтров
        products, total = await product_service.get_products_with_filter(
            db_session, filter_params=ProductFilter(), skip=0, limit=10
        )

        assert len(products) == 2
        assert total == 2

    async def test_get_products_with_category_filter(self, db_session):
        """Тест получения продуктов с фильтром по категории."""
        await db_session.execute(text("DELETE FROM proxy_products"))
        await db_session.commit()

        # Создаем продукты разных категорий
        datacenter_product = ProxyProduct(
            name="Datacenter Product",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.DATACENTER,
            session_type=SessionType.STICKY,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("1.50"),
            duration_days=30,
            stock_available=200,
            is_active=True
        )

        residential_product = ProxyProduct(
            name="Residential Product",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.RESIDENTIAL,
            session_type=SessionType.ROTATING,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("4.00"),
            duration_days=30,
            stock_available=100,
            is_active=True
        )

        db_session.add_all([datacenter_product, residential_product])
        await db_session.commit()

        # Фильтруем по категории DATACENTER
        filters = ProductFilter(proxy_category=ProxyCategory.DATACENTER)
        products, total = await product_service.get_products_with_filter(
            db_session, filter_params=filters, skip=0, limit=10
        )

        assert len(products) == 1
        assert products[0].proxy_category == ProxyCategory.DATACENTER
        assert total == 1

    async def test_get_products_with_price_range_filter(self, db_session):
        """Тест получения продуктов с фильтром по цене."""
        await db_session.execute(text("DELETE FROM proxy_products"))
        await db_session.commit()

        # Создаем продукты с разными ценами
        prices = [Decimal("1.00"), Decimal("2.50"), Decimal("5.00"), Decimal("10.00")]

        for i, price in enumerate(prices):
            product = ProxyProduct(
                name=f"Product {i + 1}",
                proxy_type=ProxyType.HTTP,
                proxy_category=ProxyCategory.DATACENTER,
                session_type=SessionType.ROTATING,
                provider=ProviderType.PROVIDER_711,
                country_code="US",
                country_name="United States",
                price_per_proxy=price,
                duration_days=30,
                stock_available=100,
                is_active=True
            )
            db_session.add(product)

        await db_session.commit()

        # Фильтруем по диапазону цен 2.00 - 6.00
        filters = ProductFilter(min_price=2.00, max_price=6.00)
        products, total = await product_service.get_products_with_filter(
            db_session, filter_params=filters, skip=0, limit=10
        )

        assert len(products) == 2  # Продукты с ценами 2.50 и 5.00
        assert total == 2
        assert all(Decimal("2.00") <= product.price_per_proxy <= Decimal("6.00") for product in products)

    async def test_get_products_with_country_filter(self, db_session):
        """Тест получения продуктов с фильтром по стране."""
        await db_session.execute(text("DELETE FROM proxy_products"))
        await db_session.commit()

        countries = ["US", "UK", "DE"]

        for country in countries:
            product = ProxyProduct(
                name=f"{country} Proxies",
                proxy_type=ProxyType.HTTP,
                proxy_category=ProxyCategory.DATACENTER,
                session_type=SessionType.ROTATING,
                provider=ProviderType.PROVIDER_711,
                country_code=country,
                country_name=f"Country {country}",
                price_per_proxy=Decimal("2.00"),
                duration_days=30,
                stock_available=100,
                is_active=True
            )
            db_session.add(product)

        await db_session.commit()

        # Фильтруем по стране US
        filters = ProductFilter(country="US")
        products, total = await product_service.get_products_with_filter(
            db_session, filter_params=filters, skip=0, limit=10
        )

        assert len(products) == 1
        assert products[0].country_code == "US"
        assert total == 1

    async def test_get_products_with_search_filter(self, db_session):
        """Тест получения продуктов с поиском по названию."""
        await db_session.execute(text("DELETE FROM proxy_products"))
        await db_session.commit()

        products_data = [
            "Premium US HTTP Proxies",
            "Fast UK HTTPS Proxies",
            "Mobile US Proxies",
            "Datacenter DE Proxies"
        ]

        for name in products_data:
            product = ProxyProduct(
                name=name,
                proxy_type=ProxyType.HTTP,
                proxy_category=ProxyCategory.DATACENTER,
                session_type=SessionType.ROTATING,
                provider=ProviderType.PROVIDER_711,
                country_code="US",
                country_name="United States",
                price_per_proxy=Decimal("2.00"),
                duration_days=30,
                stock_available=100,
                is_active=True
            )
            db_session.add(product)

        await db_session.commit()

        # Поиск по ключевому слову "US"
        filters = ProductFilter(search="US")
        products, total = await product_service.get_products_with_filter(
            db_session, filter_params=filters, skip=0, limit=10
        )

        assert len(products) == 2  # Premium US и Mobile US
        assert total == 2
        assert all("US" in product.name for product in products)

    async def test_get_products_with_pagination(self, db_session):
        """Тест получения продуктов с пагинацией."""
        await db_session.execute(text("DELETE FROM proxy_products"))
        await db_session.commit()

        # Создаем 10 продуктов
        for i in range(10):
            product = ProxyProduct(
                name=f"Product {i + 1:02d}",
                proxy_type=ProxyType.HTTP,
                proxy_category=ProxyCategory.DATACENTER,
                session_type=SessionType.ROTATING,
                provider=ProviderType.PROVIDER_711,
                country_code="US",
                country_name="United States",
                price_per_proxy=Decimal("2.00"),
                duration_days=30,
                stock_available=100,
                is_active=True
            )
            db_session.add(product)

        await db_session.commit()

        # Первая страница (5 элементов)
        first_page, total = await product_service.get_products_with_filter(
            db_session, filter_params=ProductFilter(), skip=0, limit=5
        )

        # Вторая страница (5 элементов)
        second_page, _ = await product_service.get_products_with_filter(
            db_session, filter_params=ProductFilter(), skip=5, limit=5
        )

        assert len(first_page) == 5
        assert len(second_page) == 5
        assert total == 10

        # Проверяем что продукты не пересекаются
        first_page_ids = {p.id for p in first_page}
        second_page_ids = {p.id for p in second_page}
        assert first_page_ids.isdisjoint(second_page_ids)

    async def test_check_availability_success(self, db_session):
        """Тест успешной проверки доступности товара."""
        product = ProxyProduct(
            name="Available Product",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.DATACENTER,
            session_type=SessionType.STICKY,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("3.00"),
            duration_days=30,
            min_quantity=1,
            max_quantity=100,
            stock_available=50,
            is_active=True
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        availability = await product_service.check_availability(
            db_session, product_id=product.id, quantity=10
        )

        assert availability["is_available"] is True
        assert availability["stock_available"] == 50
        assert availability["max_quantity"] == 100
        assert availability["requested_quantity"] == 10

    async def test_check_availability_insufficient_stock(self, db_session):
        """Тест проверки доступности при недостаточном количестве на складе."""
        product = ProxyProduct(
            name="Low Stock Product",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.DATACENTER,
            session_type=SessionType.STICKY,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("2.00"),
            duration_days=30,
            stock_available=3,  # Мало на складе
            is_active=True
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        availability = await product_service.check_availability(
            db_session, product_id=product.id, quantity=5
        )

        assert availability["is_available"] is False
        assert availability["stock_available"] == 3
        assert "Only 3 items available" in availability["message"]

    async def test_check_availability_product_not_found(self, db_session):
        """Тест проверки доступности несуществующего продукта."""
        availability = await product_service.check_availability(
            db_session, product_id=99999, quantity=1
        )

        assert availability["is_available"] is False
        assert "Product not found" in availability["message"]

    async def test_check_availability_inactive_product(self, db_session):
        """Тест проверки доступности неактивного продукта."""
        product = ProxyProduct(
            name="Inactive Product",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.DATACENTER,
            session_type=SessionType.STICKY,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("2.00"),
            duration_days=30,
            stock_available=100,
            is_active=False  # Неактивный
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        availability = await product_service.check_availability(
            db_session, product_id=product.id, quantity=1
        )

        assert availability["is_available"] is False
        assert "Product is not available" in availability["message"]

    async def test_get_available_countries(self, db_session):
        """Тест получения списка доступных стран."""
        await db_session.execute(text("DELETE FROM proxy_products"))
        await db_session.commit()

        countries_data = [
            ("US", "United States"),
            ("UK", "United Kingdom"),
            ("DE", "Germany"),
            ("US", "United States")  # Дубликат для проверки уникальности
        ]

        for country_code, country_name in countries_data:
            product = ProxyProduct(
                name=f"{country_code} Proxies",
                proxy_type=ProxyType.HTTP,
                proxy_category=ProxyCategory.DATACENTER,
                session_type=SessionType.ROTATING,
                provider=ProviderType.PROVIDER_711,
                country_code=country_code,
                country_name=country_name,
                price_per_proxy=Decimal("2.00"),
                duration_days=30,
                stock_available=100,
                is_active=True
            )
            db_session.add(product)

        await db_session.commit()

        countries = await product_service.get_available_countries(db_session)

        assert isinstance(countries, list)
        assert len(countries) == 3  # Уникальные страны

        country_codes = [c["code"] for c in countries]
        assert "US" in country_codes
        assert "UK" in country_codes
        assert "DE" in country_codes

    async def test_get_product_by_id(self, db_session, test_proxy_product):
        """Тест получения продукта по ID."""
        product = await product_service.get_product_by_id(
            db_session, product_id=test_proxy_product.id
        )

        assert product is not None
        assert product.id == test_proxy_product.id
        assert product.name == test_proxy_product.name

    async def test_get_product_by_id_not_found(self, db_session):
        """Тест получения несуществующего продукта."""
        product = await product_service.get_product_by_id(
            db_session, product_id=99999
        )

        assert product is None

    async def test_get_featured_products(self, db_session):
        """Тест получения рекомендуемых продуктов."""
        await db_session.execute(text("DELETE FROM proxy_products"))
        await db_session.commit()

        # Создаем обычный и рекомендуемый продукты
        regular_product = ProxyProduct(
            name="Regular Product",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.DATACENTER,
            session_type=SessionType.ROTATING,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("2.00"),
            duration_days=30,
            stock_available=100,
            is_active=True,
            is_featured=False
        )

        featured_product = ProxyProduct(
            name="Featured Product",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.DATACENTER,
            session_type=SessionType.ROTATING,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("3.00"),
            duration_days=30,
            stock_available=100,
            is_active=True,
            is_featured=True
        )

        db_session.add_all([regular_product, featured_product])
        await db_session.commit()

        featured_products = await product_service.get_featured_products(
            db_session, limit=10
        )

        assert len(featured_products) == 1
        assert featured_products[0].is_featured is True
        assert featured_products[0].name == "Featured Product"

    async def test_get_products_by_category(self, db_session):
        """Тест получения продуктов по категории."""
        await db_session.execute(text("DELETE FROM proxy_products"))
        await db_session.commit()

        categories = [ProxyCategory.DATACENTER, ProxyCategory.RESIDENTIAL, ProxyCategory.DATACENTER]

        for i, category in enumerate(categories):
            product = ProxyProduct(
                name=f"Product {i + 1}",
                proxy_type=ProxyType.HTTP,
                proxy_category=category,
                session_type=SessionType.ROTATING,
                provider=ProviderType.PROVIDER_711,
                country_code="US",
                country_name="United States",
                price_per_proxy=Decimal("2.00"),
                duration_days=30,
                stock_available=100,
                is_active=True
            )
            db_session.add(product)

        await db_session.commit()

        datacenter_products = await product_service.get_products_by_category(
            db_session, category=ProxyCategory.DATACENTER
        )

        assert len(datacenter_products) == 2
        assert all(p.proxy_category == ProxyCategory.DATACENTER for p in datacenter_products)

    async def test_search_products(self, db_session):
        """Тест поиска продуктов по ключевым словам."""
        await db_session.execute(text("DELETE FROM proxy_products"))
        await db_session.commit()

        products_data = [
            ("Premium US HTTP Proxies", "High-quality datacenter proxies"),
            ("Fast UK HTTPS Proxies", "Residential proxies for UK"),
            ("Mobile Proxies USA", "Mobile network proxies"),
            ("Germany Datacenter Proxies", "German datacenter solution")
        ]

        for name, description in products_data:
            product = ProxyProduct(
                name=name,
                description=description,
                proxy_type=ProxyType.HTTP,
                proxy_category=ProxyCategory.DATACENTER,
                session_type=SessionType.ROTATING,
                provider=ProviderType.PROVIDER_711,
                country_code="US",
                country_name="United States",
                price_per_proxy=Decimal("2.00"),
                duration_days=30,
                stock_available=100,
                is_active=True
            )
            db_session.add(product)

        await db_session.commit()

        # Поиск по "proxies"
        results = await product_service.search_products(
            db_session, search_term="proxies"
        )

        assert len(results) >= 4  # Все содержат "proxies"

        # Поиск по "UK"
        uk_results = await product_service.search_products(
            db_session, search_term="UK"
        )

        assert len(uk_results) == 1
        assert "UK" in uk_results[0].name

    async def test_update_product_stock(self, db_session, test_proxy_product):
        """Тест обновления количества товара на складе."""
        original_stock = test_proxy_product.stock_available

        updated_product = await product_service.update_product_stock(
            db_session,
            product_id=test_proxy_product.id,
            quantity_change=-5
        )

        assert updated_product.stock_available == original_stock - 5

        # Тест увеличения
        updated_again = await product_service.update_product_stock(
            db_session,
            product_id=test_proxy_product.id,
            quantity_change=10
        )

        assert updated_again.stock_available == original_stock + 5

    async def test_update_product_stock_insufficient(self, db_session):
        """Тест обновления склада при недостаточном количестве."""
        product = ProxyProduct(
            name="Low Stock Product",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.DATACENTER,
            session_type=SessionType.STICKY,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("2.00"),
            duration_days=30,
            stock_available=3,
            is_active=True
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        with pytest.raises(BusinessLogicError, match="Insufficient stock"):
            await product_service.update_product_stock(
                db_session,
                product_id=product.id,
                quantity_change=-5  # Больше чем есть
            )

    async def test_get_product_statistics(self, db_session):
        """Тест получения статистики продуктов."""
        await db_session.execute(text("DELETE FROM proxy_products"))
        await db_session.commit()

        # Создаем продукты разных категорий
        categories = [ProxyCategory.DATACENTER, ProxyCategory.RESIDENTIAL, ProxyCategory.DATACENTER]

        for i, category in enumerate(categories):
            product = ProxyProduct(
                name=f"Product {i + 1}",
                proxy_type=ProxyType.HTTP,
                proxy_category=category,
                session_type=SessionType.ROTATING,
                provider=ProviderType.PROVIDER_711,
                country_code="US",
                country_name="United States",
                price_per_proxy=Decimal(f"{i + 2}.00"),
                duration_days=30,
                stock_available=100,
                is_active=True
            )
            db_session.add(product)

        await db_session.commit()

        stats = await product_service.get_product_statistics(db_session)

        assert stats is not None
        assert "total_products" in stats
        assert "active_products" in stats
        assert "by_category" in stats
        assert stats["total_products"] == 3

    async def test_validate_product_data(self):
        """Тест валидации данных продукта."""
        # Валидные данные
        valid_data = {
            "price_per_proxy": Decimal("2.00"),
            "min_quantity": 1,
            "max_quantity": 100,
            "stock_available": 50
        }

        # Не должно вызывать исключений
        product_service._validate_product_data(valid_data)

        # Невалидные данные
        invalid_data = {
            "price_per_proxy": Decimal("0.00"),  # Нулевая цена
            "min_quantity": 0,  # Нулевое минимальное количество
            "max_quantity": 0,  # Нулевое максимальное количество
        }

        with pytest.raises(BusinessLogicError):
            product_service._validate_product_data(invalid_data)

    async def test_calculate_total_price(self, test_proxy_product):
        """Тест расчета общей стоимости."""
        quantity = 5

        total_price = product_service.calculate_total_price(
            test_proxy_product, quantity
        )

        expected_price = test_proxy_product.price_per_proxy * quantity
        assert total_price == expected_price

    async def test_get_similar_products(self, db_session, test_proxy_product):
        """Тест получения похожих продуктов."""
        # Создаем похожие продукты
        similar_products = []
        for i in range(3):
            product = ProxyProduct(
                name=f"Similar Product {i + 1}",
                proxy_type=test_proxy_product.proxy_type,
                proxy_category=test_proxy_product.proxy_category,
                session_type=SessionType.ROTATING,
                provider=ProviderType.PROVIDER_711,
                country_code=test_proxy_product.country_code,
                country_name=test_proxy_product.country_name,
                price_per_proxy=Decimal("2.50"),
                duration_days=30,
                stock_available=100,
                is_active=True
            )
            db_session.add(product)
            similar_products.append(product)

        await db_session.commit()

        results = await product_service.get_similar_products(
            db_session, product_id=test_proxy_product.id, limit=5
        )

        assert len(results) >= 3
        # Все результаты должны иметь ту же категорию и страну
        assert all(p.proxy_category == test_proxy_product.proxy_category for p in results)
        assert all(p.country_code == test_proxy_product.country_code for p in results)
