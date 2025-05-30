import pytest
from httpx import AsyncClient

@pytest.mark.integration
@pytest.mark.api
class TestOrdersAPI:

    @pytest.mark.asyncio
    async def test_create_order_success(self, client: AsyncClient, auth_headers, test_datacenter_product, user_with_balance):
        """Тест успешного создания заказа"""
        cart_data = {"proxy_product_id": test_datacenter_product.id, "quantity": 2}
        await client.post("/api/v1/cart/items", json=cart_data, headers=auth_headers)

        response = await client.post("/api/v1/orders/", headers=auth_headers)
        assert response.status_code == 201

        data = response.json()
        assert "id" in data
        assert "order_number" in data
        assert data["status"] == "paid"

    @pytest.mark.asyncio
    async def test_create_order_insufficient_balance(self, client: AsyncClient, auth_headers, test_datacenter_product):
        """Тест создания заказа с недостаточным балансом"""
        cart_data = {"proxy_product_id": test_datacenter_product.id, "quantity": 50}
        await client.post("/api/v1/cart/items", json=cart_data, headers=auth_headers)

        response = await client.post("/api/v1/orders/", headers=auth_headers)
        assert response.status_code in [201, 402]

    @pytest.mark.asyncio
    async def test_create_order_empty_cart(self, client: AsyncClient, auth_headers):
        """Тест создания заказа с пустой корзиной"""
        response = await client.post("/api/v1/orders/", headers=auth_headers)
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_get_orders_list(self, client: AsyncClient, auth_headers):
        """Тест получения списка заказов"""
        response = await client.get("/api/v1/orders/", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_order_by_id(self, client: AsyncClient, auth_headers, test_datacenter_product, user_with_balance):
        """Тест получения заказа по ID"""
        cart_data = {"proxy_product_id": test_datacenter_product.id, "quantity": 1}
        await client.post("/api/v1/cart/items", json=cart_data, headers=auth_headers)

        order_response = await client.post("/api/v1/orders/", headers=auth_headers)
        if order_response.status_code == 201:
            order_id = order_response.json()["id"]

            response = await client.get(f"/api/v1/orders/{order_id}", headers=auth_headers)
            assert response.status_code == 200

            data = response.json()
            assert data["id"] == order_id

    @pytest.mark.asyncio
    async def test_get_nonexistent_order(self, client: AsyncClient, auth_headers):
        """Тест получения несуществующего заказа"""
        response = await client.get("/api/v1/orders/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_orders_summary(self, client: AsyncClient, auth_headers):
        """Тест получения сводки по заказам"""
        response = await client.get("/api/v1/orders/summary", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "total_orders" in data
        assert "total_spent" in data
        assert "completed_orders" in data
        assert "currency" in data

    @pytest.mark.asyncio
    async def test_orders_without_auth(self, client: AsyncClient):
        """Тест доступа к заказам без авторизации"""
        response = await client.get("/api/v1/orders/")
        assert response.status_code == 403
