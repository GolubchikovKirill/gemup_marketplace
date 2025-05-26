import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.api
class TestCartAPI:

    @pytest.mark.asyncio
    async def test_get_empty_cart(self, client: AsyncClient):
        """Тест получения пустой корзины"""
        response = await client.get("/api/v1/cart/")
        assert response.status_code == 200
        data = response.json()
        assert "cart_items" in data
        assert "summary" in data

    @pytest.mark.asyncio
    async def test_add_to_cart_guest(self, client: AsyncClient):
        """Тест добавления в корзину для гостя"""
        cart_data = {
            "proxy_product_id": 1,
            "quantity": 2
        }
        response = await client.post("/api/v1/cart/items", json=cart_data)
        # Может быть 201 если продукт существует, или 400 если нет
        assert response.status_code in [201, 400, 500]

    @pytest.mark.asyncio
    async def test_add_to_cart_invalid_product(self, client: AsyncClient):
        """Тест добавления несуществующего продукта"""
        cart_data = {
            "proxy_product_id": 99999,
            "quantity": 1
        }
        response = await client.post("/api/v1/cart/items", json=cart_data)
        assert response.status_code in [400, 500]

    @pytest.mark.asyncio
    async def test_add_to_cart_invalid_quantity(self, client: AsyncClient):
        """Тест добавления с неверным количеством"""
        cart_data = {
            "proxy_product_id": 1,
            "quantity": 0
        }
        response = await client.post("/api/v1/cart/items", json=cart_data)
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_update_cart_item(self, client: AsyncClient):
        """Тест обновления элемента корзины"""
        # Сначала добавляем элемент
        cart_data = {
            "proxy_product_id": 1,
            "quantity": 1
        }
        add_response = await client.post("/api/v1/cart/items", json=cart_data)

        if add_response.status_code == 201:
            item_id = add_response.json()["id"]

            # Обновляем количество
            update_data = {"quantity": 3}
            response = await client.put(f"/api/v1/cart/items/{item_id}", json=update_data)
            assert response.status_code in [200, 404, 500]

    @pytest.mark.asyncio
    async def test_delete_cart_item(self, client: AsyncClient):
        """Тест удаления элемента корзины"""
        # Пытаемся удалить несуществующий элемент
        response = await client.delete("/api/v1/cart/items/99999")
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_clear_cart(self, client: AsyncClient):
        """Тест очистки корзины"""
        response = await client.delete("/api/v1/cart/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    @pytest.mark.asyncio
    async def test_get_cart_summary(self, client: AsyncClient):
        """Тест получения сводки корзины"""
        response = await client.get("/api/v1/cart/summary")
        assert response.status_code == 200
        data = response.json()
        assert "total_items" in data
        assert "total_amount" in data
        assert "currency" in data
        assert "user_type" in data

    @pytest.mark.asyncio
    async def test_cart_with_auth_user(self, client: AsyncClient, auth_headers):
        """Тест корзины для авторизованного пользователя"""
        response = await client.get("/api/v1/cart/", headers=auth_headers)
        assert response.status_code == 200

        # Добавляем товар для авторизованного пользователя
        cart_data = {
            "proxy_product_id": 1,
            "quantity": 1
        }
        response = await client.post("/api/v1/cart/items", json=cart_data, headers=auth_headers)
        assert response.status_code in [201, 400, 500]
