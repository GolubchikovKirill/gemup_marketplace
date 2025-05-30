import pytest
from unittest.mock import patch
from decimal import Decimal

from app.services.proxy_service import proxy_service


@pytest.mark.unit
@pytest.mark.asyncio
class TestProxyService:

    @pytest.mark.asyncio
    async def test_get_user_proxies_empty(self, db_session, test_user):
        """Тест получения пустого списка прокси"""
        proxies = await proxy_service.get_user_proxies(db_session, user=test_user)
        assert isinstance(proxies, list)
        assert len(proxies) == 0

    @pytest.mark.asyncio
    @patch('app.integrations.cryptomus.cryptomus_api.create_payment')
    async def test_payment_integration_with_mock(self, mock_create_payment, db_session, test_user):
        """Тест интеграции с платежами через мок"""
        # ИСПРАВЛЕНО: мокаем конкретный метод API
        mock_create_payment.return_value = {
            'state': 0,
            'result': {
                'uuid': 'test-uuid-123',
                'url': 'https://mock-cryptomus.com/pay/test-uuid-123'
            }
        }

        # Тестируем создание платежа
        from app.services.payment_service import payment_service

        result = await payment_service.create_payment(
            db_session,
            user=test_user,
            amount=Decimal('50.00'),
            description="Test payment"
        )

        assert result['amount'] == '50.00'
        assert result['currency'] == 'USD'
        assert 'transaction_id' in result
