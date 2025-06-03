"""
Unit тесты для интеграции с 711 Proxy API.

Тестирует покупку прокси, получение статуса заказов,
проверку доступных продуктов и обработку ошибок API.
"""

from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from app.integrations.proxy_711 import Proxy711API


@pytest.mark.unit
class TestProxy711API:
    """Тесты интеграции с 711Proxy API."""

    def test_init_without_api_key(self):
        """Тест инициализации без API ключа."""
        api = Proxy711API()
        assert api.api_key is None or api.api_key == ""

    def test_init_with_api_key(self):
        """Тест инициализации с API ключом."""
        api = Proxy711API(api_key="test_api_key_711")
        assert api.api_key == "test_api_key_711"

    @pytest.mark.asyncio
    async def test_purchase_proxies_no_api_key(self):
        """Тест покупки прокси без API ключа."""
        api = Proxy711API()

        with pytest.raises(ValueError, match="711Proxy API key not configured"):
            await api.purchase_proxies(product_id=1, quantity=5)

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_purchase_proxies_success(self, mock_client_class):
        """Тест успешной покупки прокси."""
        # Настраиваем мок ответа
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "order_id": "711_order_test_123",
                "proxies": [
                    {"ip": "203.0.113.1", "port": "8080", "username": "user123", "password": "pass456"},
                    {"ip": "203.0.113.2", "port": "8080", "username": "user123", "password": "pass456"}
                ],
                "credentials": {
                    "username": "user123",
                    "password": "pass456"
                },
                "expires_at": "2024-12-31T23:59:59Z",
                "status": "active",
                "total_proxies": 2
            }
        }
        mock_response.raise_for_status.return_value = None

        # Настраиваем мок клиента
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        api = Proxy711API(api_key="test_api_key")

        result = await api.purchase_proxies(product_id=15, quantity=2)

        # Проверяем результат
        assert result["provider_order_id"] == "711_order_test_123"
        assert result["username"] == "user123"
        assert result["password"] == "pass456"
        assert len(result["proxy_list"]) == 2
        assert "203.0.113.1:8080" in str(result["proxy_list"])

        # Проверяем что HTTP запрос был сделан
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_purchase_proxies_api_error(self, mock_client_class):
        """Тест ошибки API при покупке прокси."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Invalid product ID"
        mock_response.raise_for_status.side_effect = Exception("HTTP 400: Bad Request")

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        api = Proxy711API(api_key="test_api_key")

        with pytest.raises(Exception, match="711Proxy API returned 400"):
            await api.purchase_proxies(product_id=999, quantity=1)

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_purchase_proxies_insufficient_stock(self, mock_client_class):
        """Тест покупки при недостаточном количестве на складе."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "success": False,
            "error": "Insufficient stock",
            "available_quantity": 3
        }
        mock_response.raise_for_status.side_effect = Exception("HTTP 400")

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        api = Proxy711API(api_key="test_api_key")

        with pytest.raises(Exception):
            await api.purchase_proxies(product_id=1, quantity=10)

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_get_available_products_success(self, mock_client_class):
        """Тест успешного получения списка продуктов."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "data": [
                {
                    "id": 1,
                    "name": "US HTTP Proxies",
                    "type": "http",
                    "country": "US",
                    "price": 2.5,
                    "available_quantity": 1000,
                    "min_quantity": 1,
                    "max_quantity": 500
                },
                {
                    "id": 2,
                    "name": "UK HTTPS Proxies",
                    "type": "https",
                    "country": "UK",
                    "price": 3.0,
                    "available_quantity": 750,
                    "min_quantity": 1,
                    "max_quantity": 300
                }
            ]
        }
        mock_response.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        api = Proxy711API(api_key="test_api_key")

        products = await api.get_available_products()

        assert len(products) == 2
        assert products[0]["id"] == 1
        assert products[0]["name"] == "US HTTP Proxies"
        assert products[1]["country"] == "UK"

        # Проверяем что был сделан GET запрос
        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_get_proxy_status_success(self, mock_client_class):
        """Тест получения статуса заказа прокси."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "order_id": "711_order_status_test",
                "status": "active",
                "expires_at": "2024-12-31T23:59:59Z",
                "proxies_count": 5,
                "traffic_used": "2.5 GB",
                "traffic_limit": "100 GB",
                "last_used": "2024-01-15T10:30:00Z"
            }
        }
        mock_response.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        api = Proxy711API(api_key="test_api_key")

        status_info = await api.get_proxy_status("711_order_status_test")

        assert status_info["order_id"] == "711_order_status_test"
        assert status_info["status"] == "active"
        assert status_info["proxies_count"] == 5
        assert status_info["traffic_used"] == "2.5 GB"

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_get_proxy_status_not_found(self, mock_client_class):
        """Тест получения статуса несуществующего заказа."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Order not found"
        mock_response.raise_for_status.side_effect = Exception("HTTP 404")

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        api = Proxy711API(api_key="test_api_key")

        with pytest.raises(Exception, match="HTTP 404"):
            await api.get_proxy_status("nonexistent_order")

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_test_connection_success(self, mock_client_class):
        """Тест успешного тестирования подключения."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "message": "API connection successful",
            "api_version": "1.0"
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        api = Proxy711API(api_key="test_api_key")

        result = await api.test_connection()

        assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_no_api_key(self):
        """Тест подключения без API ключа."""
        api = Proxy711API()

        result = await api.test_connection()

        assert result is False

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_test_connection_failure(self, mock_client_class):
        """Тест неудачного подключения."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Connection timeout")
        mock_client_class.return_value.__aenter__.return_value = mock_client

        api = Proxy711API(api_key="test_api_key")

        result = await api.test_connection()

        assert result is False

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_extend_proxy_subscription(self, mock_client_class):
        """Тест продления подписки прокси."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "order_id": "711_extend_test",
                "new_expires_at": "2024-12-31T23:59:59Z",
                "extended_days": 30,
                "cost": "15.00"
            }
        }
        mock_response.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        api = Proxy711API(api_key="test_api_key")

        result = await api.extend_proxy_subscription(
            order_id="711_extend_test",
            days=30
        )

        assert result["order_id"] == "711_extend_test"
        assert result["extended_days"] == 30
        assert result["cost"] == "15.00"

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_get_proxy_list_formatted(self, mock_client_class):
        """Тест получения списка прокси в отформатированном виде."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "order_id": "711_format_test",
                "proxies": [
                    {"ip": "203.0.113.10", "port": "8080"},
                    {"ip": "203.0.113.11", "port": "8080"}
                ],
                "credentials": {
                    "username": "format_user",
                    "password": "format_pass"
                }
            }
        }
        mock_response.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        api = Proxy711API(api_key="test_api_key")

        # Тестируем разные форматы
        formats_to_test = [
            "ip:port:user:pass",
            "user:pass@ip:port",
            "ip:port",
            "https://user:pass@ip:port"
        ]

        for format_type in formats_to_test:
            result = await api.get_proxy_list_formatted(
                order_id="711_format_test",
                format_type=format_type
            )

            assert isinstance(result, list)
            assert len(result) == 2

            if format_type == "ip:port:user:pass":
                assert "203.0.113.10:8080:format_user:format_pass" in result
            elif format_type == "user:pass@ip:port":
                assert "format_user:format_pass@203.0.113.10:8080" in result

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_network_timeout_handling(self, mock_client_class):
        """Тест обработки таймаута сети."""
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Request timeout")
        mock_client_class.return_value.__aenter__.return_value = mock_client

        api = Proxy711API(api_key="test_api_key", timeout=0.1)

        with pytest.raises(Exception, match="Request timeout"):
            await api.purchase_proxies(product_id=1, quantity=1)

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_invalid_json_response(self, mock_client_class):
        """Тест обработки невалидного JSON ответа."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.text = "Invalid JSON response"

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        api = Proxy711API(api_key="test_api_key")

        with pytest.raises(Exception):
            await api.get_available_products()

    def test_format_proxy_credentials(self):
        """Тест форматирования учетных данных прокси."""
        api = Proxy711API()

        proxy_data = {
            "ip": "203.0.113.1",
            "port": "8080",
            "username": "testuser",
            "password": "testpass"
        }

        # Тестируем разные форматы
        formats = {
            "ip:port:user:pass": "203.0.113.1:8080:testuser:testpass",
            "user:pass@ip:port": "testuser:testpass@203.0.113.1:8080",
            "ip:port": "203.0.113.1:8080",
            "https://user:pass@ip:port": "https://testuser:testpass@203.0.113.1:8080"
        }

        for format_type, expected in formats.items():
            result = api.format_proxy_credentials(proxy_data, format_type)
            assert result == expected

    def test_validate_purchase_params(self):
        """Тест валидации параметров покупки."""
        api = Proxy711API(api_key="test_api_key")

        # Валидные параметры
        api.validate_purchase_params(product_id=1, quantity=5)

        # Невалидные параметры
        with pytest.raises(ValueError, match="Product ID must be positive"):
            api.validate_purchase_params(product_id=0, quantity=5)

        with pytest.raises(ValueError, match="Quantity must be positive"):
            api.validate_purchase_params(product_id=1, quantity=0)

        with pytest.raises(ValueError, match="Quantity cannot exceed"):
            api.validate_purchase_params(product_id=1, quantity=10000)

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_rate_limiting_headers(self, mock_client_class):
        """Тест обработки заголовков rate limiting."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}
        mock_response.text = "Rate limit exceeded"
        mock_response.raise_for_status.side_effect = Exception("HTTP 429")

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        api = Proxy711API(api_key="test_api_key")

        with pytest.raises(Exception, match="HTTP 429"):
            await api.purchase_proxies(product_id=1, quantity=1)
