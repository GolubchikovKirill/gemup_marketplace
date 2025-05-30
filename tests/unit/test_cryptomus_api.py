import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from decimal import Decimal

from app.integrations.cryptomus import CryptomusAPI


@pytest.mark.unit
class TestCryptomusAPI:

    @pytest.mark.asyncio
    async def test_verify_webhook_signature_no_secret(self):
        """Тест проверки подписи без секрета"""
        api = CryptomusAPI()
        api.webhook_secret = None

        data = {"order_id": "test", "status": "paid"}
        result = api._verify_webhook_signature(data, "any_signature")
        assert result is False

    @pytest.mark.asyncio
    async def test_verify_webhook_signature_with_secret(self):
        """Тест проверки подписи с секретом"""
        api = CryptomusAPI()
        api.webhook_secret = "test-secret"

        data = {"order_id": "test", "status": "paid"}
        expected_sign = api._generate_webhook_sign(data)

        result = api._verify_webhook_signature(data, expected_sign)
        assert result is True

    @pytest.mark.asyncio
    async def test_generate_sign_no_key(self):
        """Тест генерации подписи без ключа"""
        api = CryptomusAPI()
        api.api_key = None

        data = {"test": "data"}
        result = api._generate_sign(data)
        assert result == ""

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_create_payment_success(self, mock_client_class):
        """Тест успешного создания платежа"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'state': 0,
            'result': {
                'uuid': 'test-uuid-123',
                'url': 'https://pay.cryptomus.com/pay/test-uuid-123'
            }
        }
        mock_response.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        api = CryptomusAPI()
        api.api_key = "real-api-key-for-test"
        api.merchant_id = "test-merchant"
        api.base_url = "https://api.cryptomus.com/v1"

        result = await api.create_payment(
            amount=Decimal('10.00'),
            currency="USD",
            order_id="test-order-123"
        )

        assert result['state'] == 0
        assert 'result' in result
        assert 'uuid' in result['result']
