import pytest
from unittest.mock import patch
from decimal import Decimal

from app.models.models import TransactionType
from app.services.payment_service import payment_service


@pytest.mark.unit
@pytest.mark.asyncio
class TestPaymentService:

    @pytest.mark.asyncio
    @patch('app.integrations.cryptomus.cryptomus_api.create_payment')
    async def test_create_payment_success(self, mock_create_payment, db_session, test_user):
        """Тест успешного создания платежа"""
        mock_create_payment.return_value = {
            'state': 0,
            'result': {
                'uuid': 'test-uuid-123',
                'url': 'https://mock-cryptomus.com/pay/test-uuid-123'
            }
        }

        result = await payment_service.create_payment(
            db_session,
            user=test_user,
            amount=Decimal('25.00'),
            description="Test payment"
        )

        assert result['amount'] == '25.00'
        assert result['currency'] == 'USD'
        assert result['status'] == 'pending'

    @pytest.mark.asyncio
    @patch('app.integrations.cryptomus.cryptomus_api._verify_webhook_signature')
    async def test_process_webhook_success(self, mock_verify, db_session, test_user):
        """Тест успешной обработки webhook"""
        # ИСПРАВЛЕНО: мокаем проверку подписи
        mock_verify.return_value = True

        # Создаем транзакцию
        from app.crud.transaction import transaction_crud
        transaction = await transaction_crud.create_transaction(
            db_session,
            user_id=test_user.id,
            amount=Decimal('50.0'),
            currency="USD",
            transaction_type=TransactionType.DEPOSIT
        )

        webhook_data = {
            "order_id": transaction.transaction_id,
            "status": "paid",
            "amount": "50.0",
            "currency": "USD",
            "sign": "valid_signature"  # ДОБАВЛЕНО: подпись
        }

        result = await payment_service.process_webhook(db_session, webhook_data)
        assert result is True

    @pytest.mark.asyncio
    async def test_create_payment_insufficient_amount(self, db_session, test_user):
        """Тест создания платежа с недостаточной суммой"""
        from app.core.exceptions import BusinessLogicError

        with pytest.raises(BusinessLogicError, match="Minimum payment amount"):
            await payment_service.create_payment(
                db_session,
                user=test_user,
                amount=Decimal('0.50')
            )

    @pytest.mark.asyncio
    async def test_create_payment_guest_user(self, db_session, test_guest_user):
        """Тест создания платежа гостевым пользователем"""
        from app.core.exceptions import BusinessLogicError

        with pytest.raises(BusinessLogicError, match="Guest users cannot make payments"):
            await payment_service.create_payment(
                db_session,
                user=test_guest_user,
                amount=Decimal('25.00')
            )

    @pytest.mark.asyncio
    async def test_get_payment_status(self, db_session, test_user):
        """Тест получения статуса платежа"""
        from app.crud.transaction import transaction_crud
        transaction = await transaction_crud.create_transaction(
            db_session,
            user_id=test_user.id,
            amount=Decimal('25.0'),
            currency="USD",
            transaction_type=TransactionType.DEPOSIT,
            description="Test status check"
        )

        status = await payment_service.get_payment_status(
            db_session,
            transaction.transaction_id
        )

        assert status['transaction_id'] == transaction.transaction_id
        assert status['amount'] in ['25.0', '25.00', '25.0000000000']

    @pytest.mark.asyncio
    async def test_process_webhook_transaction_not_found(self, db_session):
        """Тест обработки webhook для несуществующей транзакции"""
        webhook_data = {
            "order_id": "nonexistent_transaction",
            "status": "paid",
            "amount": "50.0"
        }

        result = await payment_service.process_webhook(db_session, webhook_data)
        assert result is False

    @pytest.mark.asyncio
    async def test_get_payment_status_not_found(self, db_session):
        """Тест получения статуса несуществующего платежа"""
        from app.core.exceptions import BusinessLogicError

        with pytest.raises(BusinessLogicError, match="Transaction not found"):
            await payment_service.get_payment_status(
                db_session,
                "nonexistent_transaction_id"
            )

    @pytest.mark.asyncio
    async def test_create_payment_maximum_amount(self, db_session, test_user):
        """Тест создания платежа с максимальной суммой"""
        from app.core.exceptions import BusinessLogicError

        with pytest.raises(BusinessLogicError, match="Maximum payment amount"):
            await payment_service.create_payment(
                db_session,
                user=test_user,
                amount=Decimal('15000.00')
            )
