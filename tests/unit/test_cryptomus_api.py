"""
Unit тесты для интеграции с Cryptomus API.

Тестирует создание платежей, проверку подписей и обработку webhook
согласно реальной документации Cryptomus API.
"""

import base64
import hashlib
import json
from decimal import Decimal
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from app.integrations.cryptomus import CryptomusAPI


@pytest.mark.unit
class TestCryptomusAPI:
    """Тесты интеграции с Cryptomus API."""

    def test_init_without_credentials(self):
        """Тест инициализации без учетных данных."""
        api = CryptomusAPI()
        assert api.api_key is None
        assert api.merchant_id is None

    def test_init_with_credentials(self):
        """Тест инициализации с учетными данными."""
        api = CryptomusAPI(
            api_key="test_api_key",
            merchant_id="test_merchant"
        )
        assert api.api_key == "test_api_key"
        assert api.merchant_id == "test_merchant"

    def test_generate_signature_no_key(self):
        """Тест генерации подписи без API ключа."""
        api = CryptomusAPI()
        data = {"test": "data"}

        result = api.generate_signature(data)
        assert result == ""

    def test_generate_signature_with_key(self):
        """Тест генерации подписи с API ключом согласно документации Cryptomus."""
        api = CryptomusAPI(api_key="test_api_key")
        data = {"amount": "10.00", "currency": "USD", "order_id": "test_order"}

        result = api.generate_signature(data)

        # Проверяем что результат не пустой и является строкой
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_signature_consistent(self):
        """Тест что генерация подписи детерминистична."""
        api = CryptomusAPI(api_key="test_api_key")
        data = {"amount": "10.00", "currency": "USD", "order_id": "test_order"}

        sign1 = api.generate_signature(data)
        sign2 = api.generate_signature(data)

        assert sign1 == sign2

    def test_generate_signature_cryptomus_format(self):
        """Тест генерации подписи в формате Cryptomus (MD5 от base64)."""
        api = CryptomusAPI(api_key="test_api_key")
        data = {"amount": "10.00", "currency": "USD"}

        # Manually calculate expected signature based on Cryptomus docs
        json_data = json.dumps(data, separators=(',', ':'), sort_keys=True)
        encoded_data = base64.b64encode(json_data.encode()).decode()
        expected_sign = hashlib.md5((encoded_data + "test_api_key").encode()).hexdigest()

        result = api.generate_signature(data)
        assert result == expected_sign

    def test_verify_webhook_signature_valid(self):
        """Тест проверки валидной подписи webhook."""
        api = CryptomusAPI(api_key="test_api_key")
        webhook_data = {
            "order_id": "test_order_123",
            "status": "paid",
            "amount": "25.00",
            "currency": "USD"
        }

        # Генерируем правильную подпись
        expected_sign = api.generate_signature(webhook_data)

        result = api.verify_webhook_signature(webhook_data, expected_sign)
        assert result is True

    def test_verify_webhook_signature_invalid(self):
        """Тест проверки невалидной подписи webhook."""
        api = CryptomusAPI(api_key="test_api_key")
        webhook_data = {
            "order_id": "test_order_123",
            "status": "paid",
            "amount": "25.00",
            "currency": "USD"
        }

        result = api.verify_webhook_signature(webhook_data, "invalid_signature")
        assert result is False

    def test_verify_webhook_signature_no_api_key(self):
        """Тест проверки подписи без API ключа."""
        api = CryptomusAPI()
        webhook_data = {"order_id": "test", "status": "paid"}

        result = api.verify_webhook_signature(webhook_data, "any_signature")
        assert result is False

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_create_payment_success(self, mock_client_class):
        """Тест успешного создания платежа согласно Cryptomus API."""
        # Настраиваем мок ответа
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'state': 0,
            'result': {
                'uuid': 'payment-uuid-123',
                'order_id': 'test_order_456',
                'amount': '25.00',
                'currency': 'USD',
                'url': 'https://pay.cryptomus.com/pay/payment-uuid-123',
                'expired_at': 1640995200,
                'status': 'pending'
            }
        }
        mock_response.raise_for_status.return_value = None

        # Настраиваем мок клиента
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        api = CryptomusAPI(
            api_key="test_api_key",
            merchant_id="test_merchant"
        )

        result = await api.create_payment(
            amount=Decimal('25.00'),
            currency="USD",
            order_id="test_order_456"
        )

        # Проверяем результат
        assert result['state'] == 0
        assert 'result' in result
        assert result['result']['uuid'] == 'payment-uuid-123'
        assert result['result']['order_id'] == 'test_order_456'
        assert 'pay.cryptomus.com' in result['result']['url']

        # Проверяем что HTTP запрос был сделан с правильными заголовками
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args

        # Проверяем URL
        assert call_args[1]['url'] == 'https://api.cryptomus.com/v1/payment'

        # Проверяем заголовки
        headers = call_args[1]['headers']
        assert headers['Content-Type'] == 'application/json'
        assert headers['merchant'] == 'test_merchant'
        assert 'sign' in headers

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_create_payment_api_error(self, mock_client_class):
        """Тест создания платежа с ошибкой API."""
        # Настраиваем мок ошибки
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'state': 1,
            'errors': ['Invalid amount format'],
            'message': 'Validation failed'
        }
        mock_response.raise_for_status.side_effect = Exception("HTTP 400: Bad Request")

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        api = CryptomusAPI(
            api_key="test_api_key",
            merchant_id="test_merchant"
        )

        with pytest.raises(Exception, match="HTTP 400"):
            await api.create_payment(
                amount=Decimal('0.001'),  # Слишком малая сумма
                currency="USD",
                order_id="test_order_error"
            )

    @pytest.mark.asyncio
    async def test_create_payment_no_credentials(self):
        """Тест создания платежа без учетных данных."""
        api = CryptomusAPI()

        with pytest.raises(ValueError, match="API key and merchant ID are required"):
            await api.create_payment(
                amount=Decimal('10.00'),
                currency="USD",
                order_id="test_order"
            )

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_get_payment_info_success(self, mock_client_class):
        """Тест получения информации о платеже."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'state': 0,
            'result': {
                'uuid': 'payment-uuid-123',
                'order_id': 'test_order_789',
                'amount': '25.00',
                'currency': 'USD',
                'payment_status': 'paid',
                'status': 'paid',
                'is_final': True,
                'created_at': '2024-01-01T12:00:00+00:00',
                'updated_at': '2024-01-01T12:05:00+00:00'
            }
        }
        mock_response.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        api = CryptomusAPI(
            api_key="test_api_key",
            merchant_id="test_merchant"
        )

        result = await api.get_payment_info("test_order_789")

        assert result['state'] == 0
        assert result['result']['payment_status'] == 'paid'
        assert result['result']['amount'] == '25.00'
        assert result['result']['order_id'] == 'test_order_789'

        # Проверяем что был вызван правильный endpoint
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert 'payment/info' in call_args[1]['url']

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_network_error_handling(self, mock_client_class):
        """Тест обработки сетевых ошибок."""
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Connection timeout")
        mock_client_class.return_value.__aenter__.return_value = mock_client

        api = CryptomusAPI(
            api_key="test_api_key",
            merchant_id="test_merchant"
        )

        with pytest.raises(Exception, match="Connection timeout"):
            await api.create_payment(
                amount=Decimal('10.00'),
                currency="USD",
                order_id="test_order"
            )

    def test_prepare_payment_data(self):
        """Тест подготовки данных для платежа."""
        api = CryptomusAPI(
            api_key="test_api_key",
            merchant_id="test_merchant"
        )

        payment_data = {
            'amount': '15.50',
            'currency': 'USD',
            'order_id': 'test_order_prepare',
            'url_callback': 'https://example.com/webhook'
        }

        prepared_data, headers = api.prepare_request_data(payment_data)

        assert prepared_data['amount'] == '15.50'
        assert prepared_data['currency'] == 'USD'
        assert prepared_data['order_id'] == 'test_order_prepare'

        # Проверяем заголовки
        assert headers['merchant'] == 'test_merchant'
        assert headers['Content-Type'] == 'application/json'
        assert 'sign' in headers

    def test_webhook_signature_calculation(self):
        """Тест расчета подписи webhook в соответствии с документацией."""
        api = CryptomusAPI(api_key="test_secret_key")

        # Данные webhook как в документации
        webhook_data = {
            "uuid": "e1830f1b-50fc-432e-80ec-15b58ccac867",
            "order_id": "test_order_123",
            "amount": "10.50",
            "currency": "USD",
            "status": "paid"
        }

        signature = api.generate_signature(webhook_data)

        # Проверяем что подпись валидна
        is_valid = api.verify_webhook_signature(webhook_data, signature)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_request_timeout_handling(self):
        """Тест обработки таймаута запроса."""
        api = CryptomusAPI(
            api_key="test_api_key",
            merchant_id="test_merchant",
            timeout=0.1  # Очень короткий таймаут
        )

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = Exception("Request timeout")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(Exception, match="Request timeout"):
                await api.create_payment(
                    amount=Decimal('10.00'),
                    currency="USD",
                    order_id="timeout_test"
                )

    def test_data_serialization_for_signature(self):
        """Тест сериализации данных для подписи."""
        api = CryptomusAPI(api_key="test_key")

        # Тестируем что порядок ключей не влияет на подпись
        data1 = {"amount": "10.00", "currency": "USD", "order_id": "test"}
        data2 = {"order_id": "test", "amount": "10.00", "currency": "USD"}

        sign1 = api.generate_signature(data1)
        sign2 = api.generate_signature(data2)

        assert sign1 == sign2  # Подписи должны быть одинаковыми

    def test_empty_data_signature(self):
        """Тест генерации подписи для пустых данных."""
        api = CryptomusAPI(api_key="test_key")

        signature = api.generate_signature({})
        assert isinstance(signature, str)
        assert len(signature) > 0

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_create_payment_with_callback_url(self, mock_client_class):
        """Тест создания платежа с URL для webhook."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'state': 0,
            'result': {
                'uuid': 'payment-uuid-456',
                'url': 'https://pay.cryptomus.com/pay/payment-uuid-456'
            }
        }
        mock_response.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        api = CryptomusAPI(
            api_key="test_api_key",
            merchant_id="test_merchant"
        )

        result = await api.create_payment(
            amount=Decimal('50.00'),
            currency="USD",
            order_id="test_order_webhook",
            url_callback="https://mysite.com/webhook"
        )

        assert result['state'] == 0

        # Проверяем что callback URL был передан в запросе
        call_args = mock_client.post.call_args
        request_data = json.loads(call_args[1]['data'])
        assert 'url_callback' in request_data
        assert request_data['url_callback'] == "https://mysite.com/webhook"

    def test_webhook_data_modification_detection(self):
        """Тест обнаружения изменения данных webhook."""
        api = CryptomusAPI(api_key="secret_key")

        original_data = {
            "order_id": "order_123",
            "amount": "100.00",
            "currency": "USD",
            "status": "paid"
        }

        # Генерируем подпись для оригинальных данных
        original_signature = api.generate_signature(original_data)

        # Изменяем данные
        modified_data = original_data.copy()
        modified_data["amount"] = "200.00"  # Изменяем сумму

        # Проверяем что подпись больше не валидна
        is_valid = api.verify_webhook_signature(modified_data, original_signature)
        assert is_valid is False

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_error_response_handling(self, mock_client_class):
        """Тест обработки различных типов ошибок API."""
        # Тестируем разные коды ошибок
        error_responses = [
            {'state': 1, 'errors': ['Invalid currency']},
            {'state': 2, 'message': 'Authentication failed'},
            {'state': 3, 'errors': ['Insufficient balance']}
        ]

        api = CryptomusAPI(
            api_key="test_api_key",
            merchant_id="test_merchant"
        )

        for error_response in error_responses:
            mock_response = MagicMock()
            mock_response.json.return_value = error_response
            mock_response.raise_for_status.side_effect = Exception(f"HTTP Error: {error_response}")

            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(Exception):
                await api.create_payment(
                    amount=Decimal('10.00'),
                    currency="INVALID",
                    order_id="error_test"
                )
