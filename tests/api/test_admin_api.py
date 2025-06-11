"""
API тесты для административных функций.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
class TestAdminAPI:
    """Тесты административного API."""

    def test_admin_get_all_users(self, api_client: TestClient, admin_headers):
        """Тест получения всех пользователей (только админ)."""
        response = api_client.get("/api/v1/admin/users", headers=admin_headers)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list) or "users" in data

    def test_admin_get_all_users_unauthorized(self, api_client: TestClient, auth_headers):
        """Тест доступа к админ функциям обычным пользователем."""
        response = api_client.get("/api/v1/admin/users", headers=auth_headers)
        assert response.status_code == 403

    def test_admin_get_system_stats(self, api_client: TestClient, admin_headers):
        """Тест получения системной статистики."""
        response = api_client.get("/api/v1/admin/stats", headers=admin_headers)
        assert response.status_code == 200

        data = response.json()
        expected_fields = ["total_users", "total_orders", "total_revenue"]
        for field in expected_fields:
            assert field in data

    def test_admin_manage_products(self, api_client: TestClient, admin_headers):
        """Тест управления продуктами."""
        product_data = {
            "name": "Admin Test Product",
            "proxy_type": "http",
            "proxy_category": "datacenter",
            "price_per_proxy": 3.00,
            "duration_days": 30,
            "stock_available": 100
        }

        response = api_client.post("/api/v1/admin/products", json=product_data, headers=admin_headers)
        assert response.status_code in [201, 200]


@pytest.fixture
def admin_headers(api_client: TestClient, test_admin_user):
    """Заголовки для админа."""
    login_data = {
        "username": test_admin_user.email,
        "password": "testpassword123"
    }

    response = api_client.post("/api/v1/auth/login", data=login_data)
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    else:
        # Если нет отдельного админа, используем обычного пользователя
        return {}
