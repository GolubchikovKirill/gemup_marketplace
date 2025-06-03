"""
Unit тесты для сервиса платежей.

Тестирует создание платежей, обработку webhook, проверку статусов
и интеграцию с платежными провайдерами.
"""

from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest

from app.core.exceptions import BusinessLogicError
from app.models.models import TransactionType, TransactionStatus
from app.services.payment_service import payment_service


@pytest.mark.unit
@pytest.mark.asyncio
class TestPaymentService:
    """Тесты сервиса платежей."""

    async def test_create_payment_success(self, db_session, test_user):
        """Тест успешного создания платежа."""
        with patch('app.integrations.cryptomus.cryptomus_api.create_payment') as mock_create:
            mock_create.return_value = {
                'state': 0,
                'result': {
                    'uuid': 'payment-uuid-123',
                    'url': 'https://pay.cryptomus.com/pay/payment-uuid-123'
                }
            }

            with patch.object(payment_service.transaction_crud, 'create_transaction') as mock_create_tx:
                mock_transaction = MagicMock()
                mock_transaction.transaction_id = 'tx_123'
                mock_transaction.amount = Decimal('25.00')
                mock_create_tx.return_value = mock_transaction

                result = await payment_service.create_payment(
                    db_session,
                    user=test_user,
                    amount=Decimal('25.00'),
                    description="Test payment"
                )

        assert result is not None
        assert result['amount'] == '25.00'
        assert result['currency'] == 'USD'
        assert result['status'] == 'pending'
        assert 'transaction_id' in result
        assert 'payment_url' in result

    async def test_create_payment_minimum_amount_validation(self, db_session, test_user):
        """Тест валидации минимальной суммы платежа."""
        with pytest.raises(BusinessLogicError, match="Minimum payment amount"):
            await payment_service.create_payment(
                db_session,
                user=test_user,
                amount=Decimal('0.50')  # Меньше минимума
            )

    async def test_create_payment_maximum_amount_validation(self, db_session, test_user):
        """Тест валидации максимальной суммы платежа."""
        with pytest.raises(BusinessLogicError, match="Maximum payment amount"):
            await payment_service.create_payment(
                db_session,
                user=test_user,
                amount=Decimal('15000.00')  # Больше максимума
            )

    async def test_create_payment_guest_user_restriction(self, db_session, test_guest_user):
        """Тест ограничения создания платежей для гостевых пользователей."""
        with pytest.raises(BusinessLogicError, match="Guest users cannot make payments"):
            await payment_service.create_payment(
                db_session,
                user=test_guest_user,
                amount=Decimal('25.00')
            )

    async def test_create_payment_inactive_user(self, db_session, test_user):
        """Тест создания платежа неактивным пользователем."""
        test_user.is_active = False

        with pytest.raises(BusinessLogicError, match="User account is not active"):
            await payment_service.create_payment(
                db_session,
                user=test_user,
                amount=Decimal('25.00')
            )

    async def test_create_payment_cryptomus_api_error(self, db_session, test_user):
        """Тест обработки ошибки Cryptomus API."""
        with patch('app.integrations.cryptomus.cryptomus_api.create_payment') as mock_create:
            mock_create.side_effect = Exception("Cryptomus API error")

            with patch.object(payment_service.transaction_crud, 'create_transaction') as mock_create_tx:
                mock_transaction = MagicMock()
                mock_create_tx.return_value = mock_transaction

                with pytest.raises(Exception, match="Cryptomus API error"):
                    await payment_service.create_payment(
                        db_session,
                        user=test_user,
                        amount=Decimal('25.00')
                    )

    async def test_process_webhook_success(self, db_session, test_user):
        """Тест успешной обработки webhook."""
        # Создаем мок транзакции
        mock_transaction = MagicMock()
        mock_transaction.id = 1
        mock_transaction.transaction_id = 'tx_webhook_test'
        mock_transaction.user_id = test_user.id
        mock_transaction.amount = Decimal('50.00')
        mock_transaction.status = TransactionStatus.PENDING

        webhook_data = {
            "order_id": "tx_webhook_test",
            "status": "paid",
            "amount": "50.00",
            "currency": "USD",
            "sign": "valid_signature"
        }

        with patch.object(payment_service, '_verify_webhook_signature_wrapper') as mock_verify:
            mock_verify.return_value = True

            with patch.object(payment_service.transaction_crud, 'get_by_transaction_id') as mock_get_tx:
                mock_get_tx.return_value = mock_transaction

                with patch.object(payment_service, '_process_successful_payment') as mock_process:
                    mock_process.return_value = None

                    result = await payment_service.process_webhook(db_session, webhook_data)

        assert result is True
        mock_process.assert_called_once()

    async def test_process_webhook_invalid_signature(self, db_session):
        """Тест обработки webhook с невалидной подписью."""
        webhook_data = {
            "order_id": "tx_invalid_sign",
            "status": "paid",
            "amount": "25.00",
            "sign": "invalid_signature"
        }

        with patch.object(payment_service, '_verify_webhook_signature_wrapper') as mock_verify:
            mock_verify.return_value = False

            result = await payment_service.process_webhook(db_session, webhook_data)

        assert result is False

    async def test_process_webhook_transaction_not_found(self, db_session):
        """Тест обработки webhook для несуществующей транзакции."""
        webhook_data = {
            "order_id": "nonexistent_transaction",
            "status": "paid",
            "amount": "25.00"
        }

        with patch.object(payment_service, '_verify_webhook_signature_wrapper') as mock_verify:
            mock_verify.return_value = True

            with patch.object(payment_service.transaction_crud, 'get_by_transaction_id') as mock_get_tx:
                mock_get_tx.return_value = None

                result = await payment_service.process_webhook(db_session, webhook_data)

        assert result is False

    async def test_process_webhook_amount_mismatch(self, db_session):
        """Тест обработки webhook с несовпадающей суммой."""
        mock_transaction = MagicMock()
        mock_transaction.amount = Decimal('50.00')

        webhook_data = {
            "order_id": "tx_amount_mismatch",
            "status": "paid",
            "amount": "25.00",  # Не совпадает с транзакцией
            "currency": "USD"
        }

        with patch.object(payment_service, '_verify_webhook_signature_wrapper') as mock_verify:
            mock_verify.return_value = True

            with patch.object(payment_service.transaction_crud, 'get_by_transaction_id') as mock_get_tx:
                mock_get_tx.return_value = mock_transaction

                result = await payment_service.process_webhook(db_session, webhook_data)

        assert result is False

    async def test_get_payment_status_success(self, db_session, test_user):
        """Тест получения статуса платежа."""
        mock_transaction = MagicMock()
        mock_transaction.transaction_id = 'tx_status_test'
        mock_transaction.amount = Decimal('30.00')
        mock_transaction.currency = 'USD'
        mock_transaction.status = TransactionStatus.COMPLETED
        mock_transaction.created_at = "2024-01-15T10:30:00Z"

        with patch.object(payment_service.transaction_crud, 'get_by_transaction_id') as mock_get:
            mock_get.return_value = mock_transaction

            status = await payment_service.get_payment_status(
                db_session, transaction_id='tx_status_test'
            )

        assert status is not None
        assert status['transaction_id'] == 'tx_status_test'
        assert status['status'] == TransactionStatus.COMPLETED
        assert 'amount' in status

    async def test_get_payment_status_not_found(self, db_session):
        """Тест получения статуса несуществующего платежа."""
        with patch.object(payment_service.transaction_crud, 'get_by_transaction_id') as mock_get:
            mock_get.return_value = None

            with pytest.raises(BusinessLogicError, match="Transaction not found"):
                await payment_service.get_payment_status(
                    db_session, transaction_id='nonexistent_tx'
                )

    async def test_process_successful_payment_balance_top_up(self, db_session, test_user):
        """Тест обработки успешного платежа для пополнения баланса."""
        mock_transaction = MagicMock()
        mock_transaction.user_id = test_user.id
        mock_transaction.amount = Decimal('100.00')
        mock_transaction.transaction_type = TransactionType.DEPOSIT
        mock_transaction.order_id = None  # Пополнение баланса

        initial_balance = test_user.balance

        with patch.object(payment_service.user_crud, 'update_balance') as mock_update_balance:
            mock_updated_user = MagicMock()
            mock_updated_user.balance = initial_balance + Decimal('100.00')
            mock_update_balance.return_value = mock_updated_user

            with patch.object(payment_service.transaction_crud, 'update_status') as mock_update_status:
                await payment_service._process_successful_payment(
                    db_session, mock_transaction, "100.00"
                )

        mock_update_balance.assert_called_once()
        mock_update_status.assert_called_once_with(
            db_session, mock_transaction, TransactionStatus.COMPLETED
        )

    async def test_process_successful_payment_with_order(self, db_session, test_user, test_order):
        """Тест обработки успешного платежа для заказа."""
        mock_transaction = MagicMock()
        mock_transaction.user_id = test_user.id
        mock_transaction.amount = Decimal('25.00')
        mock_transaction.order_id = test_order.id

        with patch.object(payment_service.order_service, 'process_order_payment') as mock_process_order:
            mock_process_order.return_value = True

            with patch.object(payment_service.transaction_crud, 'update_status'):
                await payment_service._process_successful_payment(
                    db_session, mock_transaction, "25.00"
                )

        mock_process_order.assert_called_once_with(db_session, test_order.id)

    async def test_refund_payment_success(self, db_session, test_user):
        """Тест успешного возврата платежа."""
        mock_transaction = MagicMock()
        mock_transaction.id = 1
        mock_transaction.user_id = test_user.id
        mock_transaction.amount = Decimal('75.00')
        mock_transaction.status = TransactionStatus.COMPLETED

        with patch.object(payment_service.transaction_crud, 'get_by_transaction_id') as mock_get:
            mock_get.return_value = mock_transaction

            with patch.object(payment_service.user_crud, 'update_balance') as mock_update_balance:
                with patch.object(payment_service.transaction_crud, 'create_refund_transaction') as mock_create_refund:
                    mock_refund_tx = MagicMock()
                    mock_create_refund.return_value = mock_refund_tx

                    result = await payment_service.refund_payment(
                        db_session,
                        transaction_id='tx_refund_test',
                        reason='User request'
                    )

        assert result is not None
        mock_update_balance.assert_called_once()
        mock_create_refund.assert_called_once()

    async def test_refund_payment_already_refunded(self, db_session):
        """Тест возврата уже возвращенного платежа."""
        mock_transaction = MagicMock()
        mock_transaction.status = TransactionStatus.REFUNDED

        with patch.object(payment_service.transaction_crud, 'get_by_transaction_id') as mock_get:
            mock_get.return_value = mock_transaction

            with pytest.raises(BusinessLogicError, match="Transaction is already refunded"):
                await payment_service.refund_payment(
                    db_session,
                    transaction_id='tx_already_refunded'
                )

    async def test_verify_webhook_signature_wrapper(self):
        """Тест обертки проверки подписи webhook."""
        webhook_data = {
            "order_id": "test_order",
            "status": "paid",
            "amount": "25.00",
            "sign": "test_signature"
        }

        with patch('app.integrations.cryptomus.cryptomus_api.verify_webhook_signature') as mock_verify:
            mock_verify.return_value = True

            result = payment_service._verify_webhook_signature_wrapper(webhook_data)

        assert result is True
        mock_verify.assert_called_once()

    async def test_calculate_fees(self):
        """Тест расчета комиссий платежа."""
        amount = Decimal('100.00')

        fees = payment_service._calculate_payment_fees(amount)

        assert isinstance(fees, dict)
        assert 'service_fee' in fees
        assert 'payment_gateway_fee' in fees
        assert 'total_fee' in fees

    async def test_validate_payment_amount(self):
        """Тест валидации суммы платежа."""
        # Валидные суммы
        payment_service._validate_payment_amount(Decimal('1.00'))
        payment_service._validate_payment_amount(Decimal('1000.00'))

        # Невалидные суммы
        with pytest.raises(BusinessLogicError, match="Minimum payment amount"):
            payment_service._validate_payment_amount(Decimal('0.50'))

        with pytest.raises(BusinessLogicError, match="Maximum payment amount"):
            payment_service._validate_payment_amount(Decimal('15000.00'))

    async def test_generate_payment_description(self, test_user):
        """Тест генерации описания платежа."""
        description = payment_service._generate_payment_description(
            test_user, Decimal('50.00'), "Balance top-up"
        )

        assert isinstance(description, str)
        assert str(test_user.id) in description
        assert "50.00" in description

    async def test_get_user_payment_history(self, db_session, test_user):
        """Тест получения истории платежей пользователя."""
        mock_transactions = []
        for i in range(5):
            tx = MagicMock()
            tx.id = i + 1
            tx.amount = Decimal(f'{(i + 1) * 10}.00')
            tx.status = TransactionStatus.COMPLETED
            mock_transactions.append(tx)

        with patch.object(payment_service.transaction_crud, 'get_user_transactions') as mock_get:
            mock_get.return_value = mock_transactions

            history = await payment_service.get_user_payment_history(
                db_session, user_id=test_user.id
            )

        assert len(history) == 5
        assert all(tx.status == TransactionStatus.COMPLETED for tx in history)

    async def test_cancel_pending_payment(self, db_session):
        """Тест отмены ожидающего платежа."""
        mock_transaction = MagicMock()
        mock_transaction.status = TransactionStatus.PENDING

        with patch.object(payment_service.transaction_crud, 'get_by_transaction_id') as mock_get:
            mock_get.return_value = mock_transaction

            with patch.object(payment_service.transaction_crud, 'update_status') as mock_update:
                result = await payment_service.cancel_pending_payment(
                    db_session, transaction_id='tx_cancel_test'
                )

        assert result is True
        mock_update.assert_called_once_with(
            db_session, mock_transaction, TransactionStatus.CANCELLED
        )

    async def test_cancel_payment_not_pending(self, db_session):
        """Тест отмены не ожидающего платежа."""
        mock_transaction = MagicMock()
        mock_transaction.status = TransactionStatus.COMPLETED

        with patch.object(payment_service.transaction_crud, 'get_by_transaction_id') as mock_get:
            mock_get.return_value = mock_transaction

            with pytest.raises(BusinessLogicError, match="Only pending payments can be cancelled"):
                await payment_service.cancel_pending_payment(
                    db_session, transaction_id='tx_not_pending'
                )
