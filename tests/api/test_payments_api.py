"""
API тесты для платежных операций.

Тестирует все endpoints связанные с платежами,
включая создание, получение статуса и обработку webhook.
"""

import pytest

from unittest.mock import patch, AsyncMock
from starlette.testclient import TestClient


@pytest.mark.api
class TestPaymentsAPI:
    """Тесты API платежей"""

    @patch('app.services.payment_service.payment_service.create_payment')
    async def test_create_payment_success(self, mock_create_payment, api_client: TestClient, auth_headers):
        """Тест успешного создания платежа"""
        # Настраиваем мок
        mock_create_payment.return_value = {
            "transaction_id": "TXN-TEST-12345",
            "payment_url": "https://pay.cryptomus.com/test-payment",
            "amount": "50.00",
            "currency": "USD",
            "status": "pending"
        }

        payment_data = {
            "amount": 50.00,
            "description": "Test payment for balance top-up"
        }

        response = api_client.post("/api/v1/payments/create", json=payment_data, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["transaction_id"] == "TXN-TEST-12345"
        assert data["payment_url"] == "https://pay.cryptomus.com/test-payment"
        assert data["amount"] == "50.00"
        assert data["currency"] == "USD"
        assert data["status"] == "pending"
        assert "expires_in" in data

        # Проверяем что сервис был вызван с правильными параметрами
        mock_create_payment.assert_called_once()

    async def test_create_payment_invalid_amount_too_low(self, api_client: TestClient, auth_headers):
        """Тест создания платежа с слишком маленькой суммой"""
        payment_data = {
            "amount": 0.50,  # Меньше минимума $1.00
            "description": "Invalid amount test"
        }

        response = api_client.post("/api/v1/payments/create", json=payment_data, headers=auth_headers)

        assert response.status_code == 400

    async def test_create_payment_invalid_amount_too_high(self, api_client: TestClient, auth_headers):
        """Тест создания платежа с слишком большой суммой"""
        payment_data = {
            "amount": 15000.00,  # Больше максимума $10000.00
            "description": "Invalid amount test"
        }

        response = api_client.post("/api/v1/payments/create", json=payment_data, headers=auth_headers)

        assert response.status_code == 400

    async def test_create_payment_missing_amount(self, api_client: TestClient, auth_headers):
        """Тест создания платежа без указания суммы"""
        payment_data = {
            "description": "Missing amount test"
        }

        response = api_client.post("/api/v1/payments/create", json=payment_data, headers=auth_headers)

        assert response.status_code == 422  # Validation error

    async def test_create_payment_without_auth(self, api_client: TestClient):
        """Тест создания платежа без авторизации"""
        payment_data = {
            "amount": 50.00,
            "description": "Unauthorized test"
        }

        response = api_client.post("/api/v1/payments/create", json=payment_data)

        assert response.status_code == 403  # Forbidden

    @patch('app.crud.transaction.transaction_crud.get_by_transaction_id')
    @patch('app.services.payment_service.payment_service.get_payment_status')
    async def test_get_payment_status_success(self, mock_get_status, mock_get_transaction,
                                              api_client: TestClient, auth_headers, test_user):
        """Тест успешного получения статуса платежа"""
        # Мокируем транзакцию
        mock_transaction = AsyncMock()
        mock_transaction.user_id = test_user.id
        mock_get_transaction.return_value = mock_transaction

        # Мокируем статус платежа
        mock_get_status.return_value = {
            "transaction_id": "TXN-TEST-12345",
            "amount": "50.00",
            "currency": "USD",
            "status": "completed",
            "created_at": "2024-03-15T10:30:00Z",
            "updated_at": "2024-03-15T10:45:00Z"
        }

        response = api_client.get("/api/v1/payments/status/TXN-TEST-12345", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["transaction_id"] == "TXN-TEST-12345"
        assert data["amount"] == "50.00"
        assert data["currency"] == "USD"
        assert data["status"] == "completed"

    async def test_get_payment_status_not_found(self, api_client: TestClient, auth_headers):
        """Тест получения статуса несуществующего платежа"""
        response = api_client.get("/api/v1/payments/status/NONEXISTENT", headers=auth_headers)

        assert response.status_code == 404

    @patch('app.crud.transaction.transaction_crud.get_by_transaction_id')
    async def test_get_payment_status_access_denied(self, mock_get_transaction,
                                                    api_client: TestClient, auth_headers):
        """Тест получения статуса платежа другого пользователя"""
        # Мокируем транзакцию с другим user_id
        mock_transaction = AsyncMock()
        mock_transaction.user_id = 999  # Другой пользователь
        mock_get_transaction.return_value = mock_transaction

        response = api_client.get("/api/v1/payments/status/TXN-OTHER-USER", headers=auth_headers)

        assert response.status_code == 403

    async def test_get_payment_status_without_auth(self, api_client: TestClient):
        """Тест получения статуса платежа без авторизации"""
        response = api_client.get("/api/v1/payments/status/TXN-TEST-12345")

        assert response.status_code == 403

    @patch('app.services.payment_service.payment_service.get_user_transactions')
    async def test_get_payment_history_success(self, mock_get_transactions,
                                               api_client: TestClient, auth_headers):
        """Тест получения истории платежей"""
        mock_get_transactions.return_value = {
            "transactions": [
                {
                    "transaction_id": "TXN-1",
                    "amount": "25.00",
                    "currency": "USD",
                    "type": "deposit",
                    "status": "completed",
                    "description": "Balance top-up",
                    "created_at": "2024-03-15T10:30:00Z"
                },
                {
                    "transaction_id": "TXN-2",
                    "amount": "50.00",
                    "currency": "USD",
                    "type": "deposit",
                    "status": "pending",
                    "description": "Balance top-up",
                    "created_at": "2024-03-16T14:20:00Z"
                }
            ]
        }

        response = api_client.get("/api/v1/payments/history", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["transaction_id"] == "TXN-1"
        assert data[1]["transaction_id"] == "TXN-2"

    async def test_get_payment_history_empty(self, api_client: TestClient, auth_headers):
        """Тест получения пустой истории платежей"""
        with patch('app.services.payment_service.payment_service.get_user_transactions') as mock_get:
            mock_get.return_value = {"transactions": []}

            response = api_client.get("/api/v1/payments/history", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 0

    async def test_get_payment_history_without_auth(self, api_client: TestClient):
        """Тест получения истории без авторизации"""
        response = api_client.get("/api/v1/payments/history")

        assert response.status_code == 403

    @patch('app.services.payment_service.payment_service.process_webhook')
    async def test_cryptomus_webhook_success(self, mock_process_webhook, api_client: TestClient):
        """Тест успешной обработки webhook от Cryptomus"""
        mock_process_webhook.return_value = True

        webhook_data = {
            "order_id": "TXN-WEBHOOK-TEST",
            "status": "paid",
            "amount": "75.00",
            "currency": "USD",
            "uuid": "crypto-uuid-123",
            "sign": "valid_signature"
        }

        response = api_client.post("/api/v1/payments/webhook/cryptomus", json=webhook_data)

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Webhook processed successfully"

        mock_process_webhook.assert_called_once()

    @patch('app.services.payment_service.payment_service.process_webhook')
    async def test_cryptomus_webhook_processing_failed(self, mock_process_webhook, api_client: TestClient):
        """Тест неудачной обработки webhook"""
        mock_process_webhook.return_value = False

        webhook_data = {
            "order_id": "TXN-WEBHOOK-FAIL",
            "status": "paid",
            "amount": "25.00",
            "currency": "USD"
        }

        response = api_client.post("/api/v1/payments/webhook/cryptomus", json=webhook_data)

        # Даже при неудаче webhook должен возвращать 200
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Webhook received but processing failed"

    async def test_cryptomus_webhook_invalid_data(self, api_client: TestClient):
        """Тест webhook с некорректными данными"""
        webhook_data = {
            "invalid": "data"
        }

        response = api_client.post("/api/v1/payments/webhook/cryptomus", json=webhook_data)

        # Webhook всегда должен возвращать 200
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    @patch('app.services.payment_service.payment_service.process_webhook')
    async def test_test_webhook_success(self, mock_process_webhook, api_client: TestClient):
        """Тест тестового webhook endpoint"""
        mock_process_webhook.return_value = True

        webhook_data = {
            "order_id": "TEST-WEBHOOK-123",
            "status": "paid",
            "amount": "100.00",
            "currency": "USD"
        }

        response = api_client.post("/api/v1/payments/test-webhook", json=webhook_data)

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Test webhook processed successfully"

    @patch('app.services.payment_service.payment_service.process_webhook')
    async def test_test_webhook_failure(self, mock_process_webhook, api_client: TestClient):
        """Тест неудачного тестового webhook"""
        mock_process_webhook.return_value = False

        webhook_data = {
            "order_id": "TEST-WEBHOOK-FAIL",
            "status": "failed",
            "amount": "50.00",
            "currency": "USD"
        }

        response = api_client.post("/api/v1/payments/test-webhook", json=webhook_data)

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Test webhook processing failed"

    async def test_get_payment_methods(self, api_client: TestClient):
        """Тест получения доступных методов оплаты"""
        response = api_client.get("/api/v1/payments/methods")

        assert response.status_code == 200
        data = response.json()

        assert "methods" in data
        assert "default_currency" in data
        assert data["default_currency"] == "USD"

        methods = data["methods"]
        assert isinstance(methods, list)
        assert len(methods) > 0

        # Проверяем структуру первого метода
        method = methods[0]
        assert "id" in method
        assert "name" in method
        assert "description" in method
        assert "currencies" in method
