import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.api
class TestProductsAPI:

    @pytest.mark.asyncio
    async def test_get_products_list(self, client: AsyncClient):
        """Тест получения списка продуктов"""
        response = await client.get("/api/v1/products/")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data

    @pytest.mark.asyncio
    async def test_get_products_with_filters(self, client: AsyncClient):
        """Тест фильтрации продуктов"""
        # Фильтр по типу прокси
        response = await client.get("/api/v1/products/?proxy_type=http")
        assert response.status_code == 200

        # Фильтр по стране
        response = await client.get("/api/v1/products/?country_code=US")
        assert response.status_code == 200

        # Фильтр по цене
        response = await client.get("/api/v1/products/?min_price=1.0&max_price=3.0")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_products_pagination(self, client: AsyncClient):
        """Тест пагинации"""
        response = await client.get("/api/v1/products/?page=1&size=10")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["size"] == 10

    @pytest.mark.asyncio
    async def test_get_product_by_id(self, client: AsyncClient):
        """Тест получения продукта по ID"""
        # Тестируем существующий продукт
        response = await client.get("/api/v1/products/1")
        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert "name" in data
            assert "price_per_proxy" in data
        else:
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_nonexistent_product(self, client: AsyncClient):
        """Тест получения несуществующего продукта"""
        response = await client.get("/api/v1/products/99999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_countries(self, client: AsyncClient):
        """Тест получения списка стран"""
        response = await client.get("/api/v1/products/meta/countries")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        if data:  # Если есть данные
            country = data[0]
            assert "code" in country
            assert "name" in country
            assert "cities" in country

    @pytest.mark.asyncio
    async def test_get_cities_by_country(self, client: AsyncClient):
        """Тест получения городов по стране"""
        response = await client.get("/api/v1/products/meta/cities/US")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_cities_invalid_country(self, client: AsyncClient):
        """Тест получения городов для несуществующей страны"""
        response = await client.get("/api/v1/products/meta/cities/XX")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    @pytest.mark.asyncio
    async def test_check_product_availability(self, client: AsyncClient):
        """Тест проверки доступности продукта"""
        response = await client.get("/api/v1/products/1/availability?quantity=1")
        if response.status_code == 200:
            data = response.json()
            assert "product_id" in data
            assert "requested_quantity" in data
            assert "is_available" in data
        else:
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_check_availability_invalid_quantity(self, client: AsyncClient):
        """Тест проверки доступности с неверным количеством"""
        response = await client.get("/api/v1/products/1/availability?quantity=0")
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_search_products(self, client: AsyncClient):
        """Тест поиска продуктов"""
        response = await client.get("/api/v1/products/?search=HTTP")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
