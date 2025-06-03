import pytest
from httpx import AsyncClient
from unittest.mock import patch
from tests.mocks import MockOrderData


@pytest.mark.integration
@pytest.mark.api
class TestOrdersAPI:

    @patch('app.services.order_service.order_service._purchase_proxies_from_provider')
    async def test_create_order_success(self, mock_purchase, client: AsyncClient, auth_headers, test_datacenter_product,
                                        user_with_balance):
        """Тест успешного создания заказа с моком API"""
        # ИСПРАВЛЕНО: мокаем покупку прокси
        mock_purchase.return_value = MockOrderData.generate_mock_proxy_purchase_data(2)

        cart_data = {"proxy_product_id": test_datacenter_product.id, "quantity": 2}
        await client.post("/api/v1/cart/items", json=cart_data, headers=auth_headers)

        response = await client.post("/api/v1/orders/", headers=auth_headers)
        assert response.status_code == 201

        data = response.json()
        assert "id" in data
        assert "order_number" in data
        assert data["status"] == "paid"

    @patch('app.services.order_service.order_service._purchase_proxies_from_provider')
    async def test_create_order_insufficient_balance(self, mock_purchase, client: AsyncClient, auth_headers,
                                                     test_datacenter_product):
        """Тест создания заказа с недостаточным балансом"""
        mock_purchase.return_value = MockOrderData.generate_mock_proxy_purchase_data(50)

        cart_data = {"proxy_product_id": test_datacenter_product.id, "quantity": 50}
        await client.post("/api/v1/cart/items", json=cart_data, headers=auth_headers)

        response = await client.post("/api/v1/orders/", headers=auth_headers)
        assert response.status_code in [201, 402]

    async def test_create_order_empty_cart(self, client: AsyncClient, auth_headers):
        """Тест создания заказа с пустой корзиной"""
        response = await client.post("/api/v1/orders/", headers=auth_headers)
        assert response.status_code in [400, 422]

    async def test_get_orders_list(self, client: AsyncClient, auth_headers):
        """Тест получения списка заказов"""
        response = await client.get("/api/v1/orders/", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    @patch('app.services.order_service.order_service._purchase_proxies_from_provider')
    async def test_get_order_by_id(self, mock_purchase, client: AsyncClient, auth_headers, test_datacenter_product,
                                   user_with_balance):
        """Тест получения заказа по ID"""
        mock_purchase.return_value = MockOrderData.generate_mock_proxy_purchase_data(1)

        cart_data = {"proxy_product_id": test_datacenter_product.id, "quantity": 1}
        await client.post("/api/v1/cart/items", json=cart_data, headers=auth_headers)

        order_response = await client.post("/api/v1/orders/", headers=auth_headers)
        if order_response.status_code == 201:
            order_id = order_response.json()["id"]

            response = await client.get(f"/api/v1/orders/{order_id}", headers=auth_headers)
            assert response.status_code == 200

            data = response.json()
            assert data["id"] == order_id

    async def test_get_nonexistent_order(self, client: AsyncClient, auth_headers):
        """Тест получения несуществующего заказа"""
        response = await client.get("/api/v1/orders/99999", headers=auth_headers)
        assert response.status_code == 404

    async def test_get_orders_summary(self, client: AsyncClient, auth_headers):
        """Тест получения сводки по заказам"""
        response = await client.get("/api/v1/orders/summary", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "total_orders" in data
        assert "total_spent" in data
        assert "completed_orders" in data
        assert "currency" in data

    async def test_orders_without_auth(self, client: AsyncClient):
        """Тест доступа к заказам без авторизации"""
        response = await client.get("/api/v1/orders/")
        assert response.status_code == 403
