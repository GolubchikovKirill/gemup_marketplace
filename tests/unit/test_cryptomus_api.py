import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from decimal import Decimal
from app.integrations.cryptomus import CryptomusAPI


@pytest.mark.unit
class TestCryptomusAPI:

    def test_generate_sign(self):
        """Тест генерации подписи"""
        api = CryptomusAPI()
        api.api_key = "test-api-key"

        test_data = {
            "amount": "10.00",
            "currency": "USD",
            "merchant": "test-merchant"
        }

        sign = api._generate_sign(test_data)
        assert isinstance(sign, str)
        assert len(sign) == 32  # MD5 hash length

    def test_verify_webhook_signature(self):
        """Тест проверки подписи webhook"""
        api = CryptomusAPI()
        api.webhook_secret = "test-webhook-secret"

        test_data = {
            "order_id": "test-order-123",
            "status": "paid",
            "amount": "10.00"
        }

        # Генерируем правильную подпись
        correct_sign = api._generate_webhook_sign(test_data)

        # Проверяем правильную подпись
        assert api._verify_webhook_signature(test_data, correct_sign) is True

        # Проверяем неправильную подпись
        assert api._verify_webhook_signature(test_data, "wrong-signature") is False

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_create_payment_success(self, mock_client_class):
        """Тест успешного создания платежа"""
        # Мокаем успешный ответ
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'state': 0,
            'result': {
                'uuid': 'test-uuid-123',
                'url': 'https://pay.cryptomus.com/pay/test-uuid-123'
            }
        }
        mock_response.raise_for_status.return_value = None

        # Мокаем клиент
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        api = CryptomusAPI()
        api.api_key = "test-api-key"
        api.merchant_id = "test-merchant"
        api.base_url = "https://api.cryptomus.com/v1"

        result = await api.create_payment(
            amount=Decimal('10.00'),
            currency="USD",
            order_id="test-order-123"
        )

        assert result['state'] == 0
        assert 'result' in result
        assert result['result']['uuid'] == 'test-uuid-123'

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_create_payment_http_error(self, mock_client_class):
        """Тест ошибки HTTP при создании платежа"""
        # Мокаем HTTP ошибку
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("HTTP Error")
        mock_client_class.return_value.__aenter__.return_value = mock_client

        api = CryptomusAPI()
        api.api_key = "test-api-key"
        api.merchant_id = "test-merchant"
        api.base_url = "https://api.cryptomus.com/v1"

        with pytest.raises(Exception, match="Payment creation failed"):
            await api.create_payment(
                amount=Decimal('10.00'),
                currency="USD",
                order_id="test-order-123"
            )

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_get_payment_info(self, mock_client_class):
        """Тест получения информации о платеже"""
        # Мокаем успешный ответ
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'state': 0,
            'result': {
                'uuid': 'test-uuid-123',
                'payment_status': 'paid',
                'amount': '10.00'
            }
        }
        mock_response.raise_for_status.return_value = None

        # Мокаем клиент
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        api = CryptomusAPI()
        api.api_key = "test-api-key"
        api.merchant_id = "test-merchant"
        api.base_url = "https://api.cryptomus.com/v1"

        result = await api.get_payment_info("test-uuid-123")

        assert result['state'] == 0
        assert result['result']['payment_status'] == 'paid'
