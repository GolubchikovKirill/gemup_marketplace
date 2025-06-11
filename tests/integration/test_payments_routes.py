import pytest
from httpx import AsyncClient
from decimal import Decimal
from unittest.mock import patch


@pytest.mark.integration
@pytest.mark.api
class TestPaymentsAPI:

    @patch('app.integrations.cryptomus.cryptomus_api.create_payment')
    async def test_create_payment_success(self, mock_create_payment, client: AsyncClient, auth_headers, test_user):
        """Тест создания платежа с моком"""
        mock_create_payment.return_value = {
            'state': 0,
            'result': {
                'uuid': 'test-uuid-123',
                'url': 'https://mock-cryptomus.com/pay/test-uuid-123'
            }
        }

        # ИСПРАВЛЕНО: убираем currency из данных
        payment_data = {
            "amount": 50.0,
            "description": "Test payment"
        }

        response = await client.post(
            "/api/v1/payments/create",
            json=payment_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "transaction_id" in data
        assert "payment_url" in data
        assert data["amount"] == "50.0"
        assert data["currency"] == "USD"

    async def test_create_payment_invalid_amount(self, client: AsyncClient, auth_headers):
        """Тест создания платежа с неверной суммой"""
        payment_data = {
            "amount": 0.5
        }

        response = await client.post(
            "/api/v1/payments/create",
            json=payment_data,
            headers=auth_headers
        )

        assert response.status_code in [400, 422]

    async def test_get_payment_status(self, client: AsyncClient, auth_headers, db_session, test_user):
        """Тест получения статуса платежа"""
        # Создаем транзакцию напрямую в базе
        from app.crud.transaction import transaction_crud
        from app.models.models import TransactionType

        transaction = await transaction_crud.create_transaction(
            db_session,
            user_id=test_user.id,
            amount=Decimal("25.0"),
            currency="USD",
            transaction_type=TransactionType.DEPOSIT,
            description="Test transaction"
        )

        response = await client.get(
            f"/api/v1/payments/status/{transaction.transaction_id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["transaction_id"] == transaction.transaction_id
        assert data["amount"] in ["25.0", "25.00", "25.0000000000"]

    async def test_get_payment_status_not_found(self, client: AsyncClient, auth_headers):
        """Тест получения статуса несуществующего платежа"""
        response = await client.get(
            "/api/v1/payments/status/nonexistent",
            headers=auth_headers
        )

        assert response.status_code == 404

    async def test_get_payment_history(self, client: AsyncClient, auth_headers):
        """Тест получения истории платежей"""
        response = await client.get(
            "/api/v1/payments/history",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @patch('app.services.payment_service.payment_service.process_webhook')
    async def test_cryptomus_webhook(self, mock_process_webhook, client: AsyncClient, db_session, test_user):
        """Тест обработки webhook от Cryptomus"""
        mock_process_webhook.return_value = True

        webhook_data = {
            "order_id": "test_order_123",
            "status": "paid",
            "amount": "50.0",
            "currency": "USD"
        }

        response = await client.post(
            "/api/v1/payments/webhook/cryptomus",
            json=webhook_data
        )

        assert response.status_code == 200

    async def test_test_webhook(self, client: AsyncClient):
        """Тест тестового webhook"""
        webhook_data = {
            "order_id": "test_order_123",
            "status": "paid",
            "amount": "25.0",
            "currency": "USD"
        }

        response = await client.post(
            "/api/v1/payments/test-webhook",
            json=webhook_data
        )

        assert response.status_code == 200
