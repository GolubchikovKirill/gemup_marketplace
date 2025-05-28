from decimal import Decimal
from unittest.mock import patch

import pytest

from app.core.exceptions import BusinessLogicError
from app.models.models import TransactionType
from app.services.payment_service import payment_service, PaymentBusinessRules


@pytest.mark.unit
@pytest.mark.asyncio
class TestPaymentService:

    async def test_payment_business_rules_valid(self, db_session, test_user):
        """Тест валидации бизнес-правил - успешный случай"""
        validator = PaymentBusinessRules()

        result = await validator.validate({
            'amount': Decimal('10.00'),
            'user_id': test_user.id
        }, db_session)

        assert result is True

    async def test_payment_business_rules_min_amount(self, db_session, test_user):
        """Тест валидации минимальной суммы"""
        validator = PaymentBusinessRules()

        with pytest.raises(BusinessLogicError, match="Minimum payment amount"):
            await validator.validate({
                'amount': Decimal('0.50'),  # Меньше минимума
                'user_id': test_user.id
            }, db_session)

    async def test_payment_business_rules_max_amount(self, db_session, test_user):
        """Тест валидации максимальной суммы"""
        validator = PaymentBusinessRules()

        with pytest.raises(BusinessLogicError, match="Maximum payment amount"):
            await validator.validate({
                'amount': Decimal('15000.00'),  # Больше максимума
                'user_id': test_user.id
            }, db_session)

    async def test_payment_business_rules_guest_user(self, db_session, test_guest_user):
        """Тест валидации для гостевого пользователя"""
        validator = PaymentBusinessRules()

        with pytest.raises(BusinessLogicError, match="Guest users cannot make payments"):
            await validator.validate({
                'amount': Decimal('10.00'),
                'user_id': test_guest_user.id
            }, db_session)

    @patch('app.services.payment_service.cryptomus_api.create_payment')
    async def test_create_payment_success(self, mock_create_payment, db_session, test_user):
        """Тест успешного создания платежа"""
        # Мокаем ответ от Cryptomus
        mock_create_payment.return_value = {
            'state': 0,
            'result': {
                'uuid': 'test-uuid-123',
                'url': 'https://pay.cryptomus.com/pay/test-uuid-123'
            }
        }

        result = await payment_service.create_payment(
            db_session,
            user=test_user,
            amount=Decimal('25.00'),
            description="Test payment"
        )

        assert result['amount'] == Decimal('25.00')
        assert result['currency'] == 'USD'
        assert result['status'] == 'pending'
        assert 'transaction_id' in result
        assert 'payment_url' in result
        assert 'expires_at' in result

    @patch('app.services.payment_service.cryptomus_api.create_payment')
    async def test_create_payment_cryptomus_error(self, mock_create_payment, db_session, test_user):
        """Тест ошибки от Cryptomus"""
        # Мокаем ошибку от Cryptomus
        mock_create_payment.return_value = {
            'state': 1,
            'message': 'Invalid merchant'
        }

        with pytest.raises(BusinessLogicError, match="Payment creation failed"):
            await payment_service.create_payment(
                db_session,
                user=test_user,
                amount=Decimal('25.00')
            )

    async def test_process_webhook_success(self, db_session, test_user):
        """Тест обработки успешного webhook"""
        # Создаем транзакцию
        from app.crud.transaction import transaction_crud
        transaction = await transaction_crud.create_transaction(
            db_session,
            user_id=test_user.id,
            amount=50.0,
            currency="USD",  # ИСПРАВЛЕНО: передаем currency
            transaction_type=TransactionType.DEPOSIT,
            description="Test transaction"
        )

        # Мокаем webhook данные
        webhook_data = {
            'order_id': transaction.transaction_id,
            'status': 'paid',
            'amount': '50.00',
            'currency': 'USD',
            'sign': 'test-signature'
        }

        # Мокаем проверку подписи
        with patch('app.services.payment_service.cryptomus_api._verify_webhook_signature', return_value=True):
            result = await payment_service.process_webhook(db_session, webhook_data)

        assert result is True

        # Проверяем, что баланс пользователя обновился
        await db_session.refresh(test_user)
        assert test_user.balance >= Decimal('50.00')

    async def test_process_webhook_invalid_signature(self, db_session):
        """Тест обработки webhook с неверной подписью"""
        webhook_data = {
            'order_id': 'test-order-123',
            'status': 'paid',
            'amount': '50.00',
            'currency': 'USD',
            'sign': 'invalid-signature'
        }

        # Мокаем неверную подпись
        with patch('app.services.payment_service.cryptomus_api._verify_webhook_signature', return_value=False):
            result = await payment_service.process_webhook(db_session, webhook_data)

        assert result is False

    async def test_get_payment_status(self, db_session, test_user):
        """Тест получения статуса платежа"""
        # Создаем транзакцию
        from app.crud.transaction import transaction_crud
        transaction = await transaction_crud.create_transaction(
            db_session,
            user_id=test_user.id,
            amount=25.0,
            currency="USD",  # ИСПРАВЛЕНО: передаем currency
            transaction_type=TransactionType.DEPOSIT,
            description="Test status check"
        )

        status = await payment_service.get_payment_status(
            db_session,
            transaction.transaction_id
        )

        assert status['transaction_id'] == transaction.transaction_id
        assert status['amount'] == 25.0
        assert status['currency'] == 'USD'
        assert 'status' in status
        assert 'created_at' in status

    async def test_get_payment_status_not_found(self, db_session):
        """Тест получения статуса несуществующего платежа"""
        with pytest.raises(BusinessLogicError, match="Transaction not found"):
            await payment_service.get_payment_status(
                db_session,
                "non-existent-transaction"
            )
