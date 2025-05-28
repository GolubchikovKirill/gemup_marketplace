import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from decimal import Decimal
from app.integrations.proxy_711 import Proxy711API


@pytest.mark.unit
class TestProxy711API:

    def test_init(self):
        """Тест инициализации API"""
        api = Proxy711API()
        assert api.base_url is not None
        assert api.api_key is not None

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_get_available_products_success(self, mock_client_class):
        """Тест успешного получения продуктов"""
        # Мокаем успешный ответ
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "id": "1",
                "name": "US HTTP Proxies",
                "country": "US",
                "type": "http",
                "price": 1.5
            }
        ]
        mock_response.raise_for_status.return_value = None

        # Мокаем клиент
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        api = Proxy711API()
        api.api_key = "test-api-key"
        api.base_url = "https://api.711proxy.com"

        products = await api.get_available_products()

        assert len(products) == 1
        assert products[0]["name"] == "US HTTP Proxies"

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_purchase_proxies_success(self, mock_client_class):
        """Тест успешной покупки прокси"""
        # Мокаем успешный ответ
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "order_id": "711-order-123",
            "proxies": ["1.2.3.4:8080", "5.6.7.8:8080"],
            "username": "user123",
            "password": "pass123",
            "status": "active"
        }
        mock_response.raise_for_status.return_value = None

        # Мокаем клиент
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        api = Proxy711API()
        api.api_key = "test-api-key"
        api.base_url = "https://api.711proxy.com"

        result = await api.purchase_proxies(
            product_id="1",
            quantity=2,
            duration_days=30,
            country_code="US"
        )

        assert result["order_id"] == "711-order-123"
        assert len(result["proxies"]) == 2
        assert result["username"] == "user123"

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_purchase_proxies_error(self, mock_client_class):
        """Тест ошибки при покупке прокси"""
        # Мокаем ошибку
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("API Error")
        mock_client_class.return_value.__aenter__.return_value = mock_client

        api = Proxy711API()
        api.api_key = "test-api-key"
        api.base_url = "https://api.711proxy.com"

        with pytest.raises(Exception, match="Failed to purchase proxies"):
            await api.purchase_proxies(
                product_id="1",
                quantity=2,
                duration_days=30,
                country_code="US"
            )

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_get_proxy_list_success(self, mock_client_class):
        """Тест получения списка прокси"""
        # Мокаем успешный ответ
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "proxies": ["1.2.3.4:8080", "5.6.7.8:8080"],
            "username": "user123",
            "password": "pass123",
            "expires_at": "2025-02-28T00:00:00Z"
        }
        mock_response.raise_for_status.return_value = None

        # Мокаем клиент
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        api = Proxy711API()
        api.api_key = "test-api-key"
        api.base_url = "https://api.711proxy.com"

        result = await api.get_proxy_list("711-order-123")

        assert len(result["proxies"]) == 2
        assert result["username"] == "user123"

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_extend_proxies_success(self, mock_client_class):
        """Тест продления прокси"""
        # Мокаем успешный ответ
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "order_id": "711-order-123",
            "extended_days": 30,
            "new_expires_at": "2025-03-30T00:00:00Z",
            "status": "extended"
        }
        mock_response.raise_for_status.return_value = None

        # Мокаем клиент
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        api = Proxy711API()
        api.api_key = "test-api-key"
        api.base_url = "https://api.711proxy.com"

        result = await api.extend_proxies("711-order-123", 30)

        assert result["extended_days"] == 30
        assert result["status"] == "extended"
