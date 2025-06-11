"""
API тесты для обработки ошибок.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
class TestErrorHandling:
    """Тесты обработки ошибок в API."""

    def test_404_not_found(self, api_client: TestClient):
        """Тест 404 ошибки."""
        response = api_client.get("/api/v1/nonexistent-endpoint")
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data or "message" in data

    def test_method_not_allowed(self, api_client: TestClient):
        """Тест неподдерживаемого HTTP метода."""
        response = api_client.put("/api/v1/products/")  # PUT вместо GET
        assert response.status_code == 405

    def test_malformed_json(self, api_client: TestClient, auth_headers):
        """Тест с некорректным JSON."""
        response = api_client.post(
            "/api/v1/cart/items",
            data="invalid json{",
            headers={**auth_headers, "content-type": "application/json"}
        )
        assert response.status_code == 422

    def test_missing_required_fields(self, api_client: TestClient, auth_headers):
        """Тест с отсутствующими обязательными полями."""
        incomplete_data = {"quantity": 1}  # Нет proxy_product_id

        response = api_client.post("/api/v1/cart/items", json=incomplete_data, headers=auth_headers)
        assert response.status_code == 422

        data = response.json()
        assert "detail" in data

    def test_invalid_data_types(self, api_client: TestClient, auth_headers):
        """Тест с неверными типами данных."""
        invalid_data = {
            "proxy_product_id": "not_a_number",
            "quantity": "also_not_a_number"
        }

        response = api_client.post("/api/v1/cart/items", json=invalid_data, headers=auth_headers)
        assert response.status_code == 422

    def test_large_request_body(self, api_client: TestClient, auth_headers):
        """Тест с очень большим телом запроса."""
        large_data = {
            "description": "A" * 100000  # 100KB строка
        }

        response = api_client.post("/api/v1/payments/create", json=large_data, headers=auth_headers)
        assert response.status_code in [400, 413, 422]

    def test_sql_injection_in_endpoints(self, api_client: TestClient):
        """Тест защиты от SQL инъекций в endpoints."""
        sql_payload = "'; DROP TABLE users; --"

        response = api_client.get(f"/api/v1/products/?search={sql_payload}")
        assert response.status_code in [200, 400]  # Не должно быть 500

    def test_concurrent_requests_stability(self, api_client: TestClient):
        """Тест стабильности при параллельных запросах."""
        import threading

        results = []

        def make_request():
            try:
                response = api_client.get("/api/v1/products/")
                results.append(response.status_code)
            except Exception as e:
                results.append(f"error: {e}")

        # Создаем 10 параллельных запросов
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Большинство запросов должны быть успешными
        successful = sum(1 for r in results if r == 200)
        assert successful >= 8  # Минимум 80% успешных
