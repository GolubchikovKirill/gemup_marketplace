import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BusinessLogicError
from app.crud.transaction import transaction_crud
from app.crud.user import user_crud
from app.integrations.cryptomus import cryptomus_api
from app.models.models import Transaction, TransactionType, TransactionStatus, User
from app.schemas.transaction import TransactionCreate
from app.services.base import BaseService, BusinessRuleValidator

logger = logging.getLogger(__name__)


class PaymentBusinessRules(BusinessRuleValidator):
    """Валидатор бизнес-правил для платежей"""

    async def validate(self, data: dict, db: AsyncSession) -> bool:
        """Валидация правил платежа"""
        amount = data.get('amount')
        user_id = data.get('user_id')

        # Проверяем минимальную сумму
        if amount < Decimal('1.00'):
            raise BusinessLogicError("Minimum payment amount is $1.00")

        # Проверяем максимальную сумму
        if amount > Decimal('10000.00'):
            raise BusinessLogicError("Maximum payment amount is $10,000.00")

        # Проверяем существование пользователя
        user = await user_crud.get(db, obj_id=user_id)
        if not user:
            raise BusinessLogicError("User not found")

        if user.is_guest:
            raise BusinessLogicError("Guest users cannot make payments")

        return True


class PaymentService(BaseService[Transaction, TransactionCreate, dict]):
    """Сервис для работы с платежами"""

    def __init__(self):
        super().__init__(Transaction)
        self.business_rules = PaymentBusinessRules()

    async def create_payment(
            self,
            db: AsyncSession,
            user: User,
            amount: Decimal,
            currency: str = "USD",
            description: str = "Balance top-up"
    ) -> Dict[str, Any]:
        """Создание платежа для пополнения баланса"""
        try:
            # Валидируем бизнес-правила
            await self.business_rules.validate({
                'amount': amount,
                'user_id': user.id
            }, db)

            # Создаем транзакцию в базе
            transaction = await transaction_crud.create_transaction(
                db,
                user_id=user.id,
                amount=amount,  # ИСПРАВЛЕНО: передаем Decimal
                currency=currency,
                transaction_type=TransactionType.DEPOSIT,
                payment_provider="cryptomus",
                description=description
            )

            # Создаем платеж в Cryptomus
            payment_result = await cryptomus_api.create_payment(
                amount=amount,
                currency=currency,
                order_id=transaction.transaction_id,
                callback_url=f"{self._get_base_url()}/api/v1/payments/webhook/cryptomus"
            )

            # Обновляем транзакцию данными от Cryptomus
            if payment_result.get('state') == 0:
                result_data = payment_result.get('result', {})

                await transaction_crud.update_status(
                    db,
                    transaction=transaction,
                    status=TransactionStatus.PENDING,
                    external_transaction_id=result_data.get('uuid'),
                    payment_url=result_data.get('url')
                )

                logger.info(f"Payment created for user {user.id}: {amount} {currency}")

                # ИСПРАВЛЕНО: возвращаем строки для PaymentResponse
                return {
                    "transaction_id": transaction.transaction_id,
                    "payment_url": result_data.get('url'),
                    "amount": str(amount),  # ИСПРАВЛЕНО: конвертируем в строку
                    "currency": currency,
                    "status": "pending",
                    "expires_at": self._calculate_expiry_time()
                }
            else:
                # Ошибка создания платежа
                await transaction_crud.update_status(
                    db,
                    transaction=transaction,
                    status=TransactionStatus.FAILED
                )

                error_msg = payment_result.get('message', 'Unknown error')
                raise BusinessLogicError(f"Payment creation failed: {error_msg}")

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error creating payment: {e}")
            raise BusinessLogicError(f"Payment creation failed: {str(e)}")

    async def process_webhook(
            self,
            db: AsyncSession,
            webhook_data: Dict[str, Any]
    ) -> bool:
        """Обработка webhook от Cryptomus"""
        try:
            # Проверяем подпись webhook
            received_sign = webhook_data.get('sign')
            if not cryptomus_api._verify_webhook_signature(webhook_data, received_sign):
                logger.warning("Invalid webhook signature")
                return False

            # Получаем данные платежа
            order_id = webhook_data.get('order_id')
            status = webhook_data.get('status')
            amount = webhook_data.get('amount')
            currency = webhook_data.get('currency')

            if not order_id:
                logger.warning("Missing order_id in webhook")
                return False

            # Находим транзакцию
            transaction = await transaction_crud.get_by_transaction_id(
                db, transaction_id=order_id
            )

            if not transaction:
                logger.warning(f"Transaction not found: {order_id}")
                return False

            # Обрабатываем статус
            if status == 'paid' or status == 'paid_over':
                # Платеж успешен - пополняем баланс
                await self._process_successful_payment(db, transaction, amount)

            elif status == 'fail' or status == 'cancel':
                # Платеж неуспешен
                await transaction_crud.update_status(
                    db,
                    transaction=transaction,
                    status=TransactionStatus.FAILED
                )

            elif status == 'process':
                # Платеж в обработке
                await transaction_crud.update_status(
                    db,
                    transaction=transaction,
                    status=TransactionStatus.PENDING
                )

            logger.info(f"Webhook processed: {order_id}, status: {status}")
            return True

        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return False

    @staticmethod
    async def _process_successful_payment(
            db: AsyncSession,
            transaction: Transaction,
            amount: str
    ):
        """Обработка успешного платежа"""
        try:
            # Обновляем статус транзакции
            await transaction_crud.update_status(
                db,
                transaction=transaction,
                status=TransactionStatus.COMPLETED
            )

            # Пополняем баланс пользователя
            user = await user_crud.get(db, obj_id=transaction.user_id)
            if user:
                await user_crud.update_balance(
                    db,
                    user=user,
                    amount=Decimal(amount)  # ИСПРАВЛЕНО: конвертируем в Decimal
                )

                logger.info(f"Balance updated for user {user.id}: +{amount}")

        except Exception as e:
            logger.error(f"Error processing successful payment: {e}")
            raise

    @staticmethod
    async def get_payment_status(
            db: AsyncSession,
            transaction_id: str
    ) -> Dict[str, Any]:
        """Получение статуса платежа"""
        try:
            transaction = await transaction_crud.get_by_transaction_id(
                db, transaction_id=transaction_id
            )

            if not transaction:
                raise BusinessLogicError("Transaction not found")

            # Если есть external_transaction_id, получаем актуальную информацию
            if transaction.external_transaction_id:
                try:
                    payment_info = await cryptomus_api.get_payment_info(
                        transaction.external_transaction_id
                    )

                    if payment_info.get('state') == 0:
                        result_data = payment_info.get('result', {})
                        return {
                            "transaction_id": transaction.transaction_id,
                            "status": result_data.get('payment_status', str(transaction.status)),
                            "amount": str(transaction.amount),  # ИСПРАВЛЕНО: конвертируем в строку
                            "currency": transaction.currency,
                            "created_at": transaction.created_at,
                            "payment_url": transaction.payment_url
                        }

                except Exception as e:
                    logger.warning(f"Failed to get payment info from Cryptomus: {e}")

            # Возвращаем информацию из базы
            return {
                "transaction_id": transaction.transaction_id,
                "status": str(transaction.status),
                "amount": str(transaction.amount),  # ИСПРАВЛЕНО: конвертируем в строку
                "currency": transaction.currency,
                "created_at": transaction.created_at,
                "payment_url": transaction.payment_url
            }

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error getting payment status: {e}")
            raise BusinessLogicError(f"Failed to get payment status: {str(e)}")

    @staticmethod
    def _get_base_url() -> str:
        """Получение базового URL приложения"""
        return getattr(settings, 'base_url', 'http://localhost:8080')  # ИСПРАВЛЕНО: порт 8080

    @staticmethod
    def _calculate_expiry_time() -> datetime:
        """Расчет времени истечения платежа"""
        from datetime import timedelta
        return datetime.now() + timedelta(hours=1)

    # Реализация абстрактных методов BaseService
    async def create(self, db: AsyncSession, obj_in: TransactionCreate) -> Transaction:
        return await transaction_crud.create(db, obj_in=obj_in)

    async def get(self, db: AsyncSession, obj_id: int) -> Optional[Transaction]:
        return await transaction_crud.get(db, obj_id=obj_id)

    async def update(self, db: AsyncSession, db_obj: Transaction, obj_in: dict) -> Transaction:
        return await transaction_crud.update(db, db_obj=db_obj, obj_in=obj_in)

    async def delete(self, db: AsyncSession, obj_id: int) -> bool:
        await transaction_crud.remove(db, obj_id=obj_id)
        return True

    async def get_multi(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Transaction]:
        return await transaction_crud.get_multi(db, skip=skip, limit=limit)


# Создаем экземпляр сервиса
payment_service = PaymentService()
