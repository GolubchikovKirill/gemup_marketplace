"""
Сервис для управления платежами.

Обеспечивает создание платежей, обработку webhook'ов и управление
транзакциями через различные платежные системы.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessLogicError
from app.crud.order import order_crud
from app.crud.transaction import transaction_crud
from app.crud.user import user_crud
from app.integrations import get_payment_provider, IntegrationError
from app.models.models import Transaction, TransactionStatus, OrderStatus
from app.schemas.payment import (
    PaymentCreateRequest, PaymentResponse, PaymentVerificationRequest, PaymentVerificationResponse
)
from app.schemas.transaction import TransactionCreate, TransactionUpdate
from app.services.base import BaseService, BusinessRuleValidator

logger = logging.getLogger(__name__)


class PaymentBusinessRules(BusinessRuleValidator):
    """Валидатор бизнес-правил для платежей."""

    async def validate(self, data: Dict[str, Any], db: AsyncSession) -> bool:
        """
        Валидация бизнес-правил для платежей.

        Args:
            data: Данные для валидации
            db: Сессия базы данных

        Returns:
            bool: Результат валидации

        Raises:
            BusinessLogicError: При нарушении бизнес-правил
        """
        try:
            amount = data.get("amount")
            currency = data.get("currency", "USD")
            order_id = data.get("order_id")

            # Валидация суммы
            if not amount or amount <= 0:
                raise BusinessLogicError("Payment amount must be positive")

            if amount > Decimal('100000.00'):  # Максимальная сумма платежа
                raise BusinessLogicError("Payment amount exceeds maximum limit")

            # Валидация валюты
            supported_currencies = ["USD", "EUR", "RUB", "BTC", "ETH", "USDT"]
            if currency not in supported_currencies:
                raise BusinessLogicError(f"Unsupported currency: {currency}")

            # Валидация заказа
            if order_id:
                order = await order_crud.get(db, id=order_id)
                if not order:
                    raise BusinessLogicError("Order not found")

                if order.status not in [OrderStatus.PENDING]:
                    raise BusinessLogicError(f"Cannot create payment for order with status {order.status}")

            logger.debug("Payment business rules validation passed")
            return True

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error during payment business rules validation: {e}")
            raise BusinessLogicError(f"Validation failed: {str(e)}")


class PaymentService(BaseService[Transaction, TransactionCreate, TransactionUpdate]):
    """
    Сервис для управления платежами.

    Предоставляет функциональность для создания платежей через различные
    платежные системы, обработки webhook'ов и управления транзакциями.
    """

    def __init__(self):
        super().__init__(Transaction)
        self.crud = transaction_crud
        self.business_rules = PaymentBusinessRules()

    async def create_payment(
        self,
        db: AsyncSession,
        *,
        payment_request: PaymentCreateRequest,
        user_id: Optional[int] = None
    ) -> PaymentResponse:
        """
        Создание платежа через выбранную платежную систему.

        Args:
            db: Сессия базы данных
            payment_request: Параметры платежа
            user_id: ID пользователя (опционально)

        Returns:
            PaymentResponse: Данные созданного платежа

        Raises:
            BusinessLogicError: При ошибках создания платежа
        """
        try:
            # Валидация бизнес-правил
            validation_data = {
                "amount": payment_request.amount,
                "currency": payment_request.currency,
                "order_id": payment_request.order_id
            }
            await self.business_rules.validate(validation_data, db)

            # Получаем заказ если указан
            if payment_request.order_id:
                order = await order_crud.get(db, id=payment_request.order_id)
                if not order:
                    raise BusinessLogicError("Order not found")

            # Создаем транзакцию в нашей БД
            transaction_data = TransactionCreate(
                user_id=user_id,
                order_id=payment_request.order_id,
                amount=payment_request.amount,
                currency=payment_request.currency,
                payment_method=payment_request.payment_method,
                status=TransactionStatus.PENDING,
                description=payment_request.description or f"Payment for order {payment_request.order_id}"
            )

            transaction = await self.crud.create(db, obj_in=transaction_data)

            # Создаем платеж через провайдера
            if payment_request.payment_method == "cryptomus":
                payment_data = await self._create_cryptomus_payment(
                    transaction, payment_request
                )
            else:
                raise BusinessLogicError(f"Unsupported payment method: {payment_request.payment_method}")

            # Обновляем транзакцию с данными провайдера
            transaction.provider_payment_id = payment_data.get("uuid")
            transaction.provider_metadata = str(payment_data)
            await db.commit()

            logger.info(f"Payment created: {transaction.id} via {payment_request.payment_method}")

            return PaymentResponse(
                transaction_id=transaction.id,
                payment_url=payment_data.get("url", ""),
                payment_id=payment_data.get("uuid", ""),
                amount=str(payment_request.amount),
                currency=payment_request.currency,
                status="pending",
                expires_at=payment_data.get("expires_at"),
                qr_code=payment_data.get("qr", ""),
                payment_method=payment_request.payment_method
            )

        except BusinessLogicError:
            raise
        except IntegrationError as e:
            logger.error(f"Integration error creating payment: {e}")
            raise BusinessLogicError(f"Payment creation failed: {e.message}")
        except Exception as e:
            logger.error(f"Error creating payment: {e}")
            raise BusinessLogicError(f"Failed to create payment: {str(e)}")

    async def handle_webhook(
        self,
        db: AsyncSession,
        *,
        provider: str,
        webhook_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Обработка webhook от платежной системы.

        Args:
            db: Сессия базы данных
            provider: Название провайдера
            webhook_data: Данные webhook

        Returns:
            Dict[str, Any]: Результат обработки

        Raises:
            BusinessLogicError: При ошибках обработки
        """
        try:
            if provider == "cryptomus":
                return await self._handle_cryptomus_webhook(db, webhook_data)
            else:
                raise BusinessLogicError(f"Unsupported webhook provider: {provider}")

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error handling webhook from {provider}: {e}")
            raise BusinessLogicError(f"Webhook processing failed: {str(e)}")

    async def verify_payment(
        self,
        db: AsyncSession,
        *,
        verification_request: PaymentVerificationRequest
    ) -> PaymentVerificationResponse:
        """
        Проверка статуса платежа у провайдера.

        Args:
            db: Сессия базы данных
            verification_request: Параметры проверки

        Returns:
            PaymentVerificationResponse: Результат проверки

        Raises:
            BusinessLogicError: При ошибках проверки
        """
        try:
            transaction = await self.crud.get(db, id=verification_request.transaction_id)
            if not transaction:
                raise BusinessLogicError("Transaction not found")

            if not transaction.provider_payment_id:
                raise BusinessLogicError("No provider payment ID")

            # Проверяем статус у провайдера
            if transaction.payment_method == "cryptomus":
                payment_info = await self._verify_cryptomus_payment(
                    transaction.provider_payment_id
                )
            else:
                raise BusinessLogicError(f"Unsupported payment method: {transaction.payment_method}")

            # Обновляем статус транзакции если изменился
            new_status = self._map_provider_status(
                transaction.payment_method,
                payment_info.get("status", "")
            )

            if new_status != transaction.status:
                await self._update_transaction_status(db, transaction, new_status, payment_info)

            return PaymentVerificationResponse(
                transaction_id=transaction.id,
                status=transaction.status.value,
                provider_status=payment_info.get("status", ""),
                amount=str(transaction.amount),
                currency=transaction.currency,
                verified_at=datetime.now(timezone.utc).isoformat()
            )

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error verifying payment: {e}")
            raise BusinessLogicError(f"Payment verification failed: {str(e)}")

    async def get_payment_methods(self) -> List[Dict[str, Any]]:
        """
        Получение списка доступных методов оплаты.

        Returns:
            List[Dict[str, Any]]: Список методов оплаты
        """
        try:
            methods = []

            # Проверяем доступность Cryptomus
            try:
                cryptomus_api = get_payment_provider("cryptomus")
                if await cryptomus_api.test_connection():
                    methods.append({
                        "id": "cryptomus",
                        "name": "Cryptomus",
                        "type": "crypto",
                        "currencies": ["USD", "EUR", "RUB", "BTC", "ETH", "USDT"],
                        "min_amount": "1.00",
                        "max_amount": "100000.00",
                        "description": "Cryptocurrency payments",
                        "available": True
                    })
                else:
                    methods.append({
                        "id": "cryptomus",
                        "name": "Cryptomus",
                        "type": "crypto",
                        "available": False,
                        "error": "Service temporarily unavailable"
                    })
            except Exception as e:
                logger.warning(f"Cryptomus availability check failed: {e}")

            return methods

        except Exception as e:
            logger.error(f"Error getting payment methods: {e}")
            return []

    async def get_transaction_history(
        self,
        db: AsyncSession,
        *,
        user_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Transaction]:
        """
        Получение истории транзакций.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя (опционально)
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            List[Transaction]: Список транзакций
        """
        try:
            if user_id:
                return await self.crud.get_user_transactions(
                    db, user_id=user_id, skip=skip, limit=limit
                )
            else:
                return await self.crud.get_multi(db, skip=skip, limit=limit)

        except Exception as e:
            logger.error(f"Error getting transaction history: {e}")
            return []

    async def cancel_payment(
        self,
        db: AsyncSession,
        *,
        transaction_id: int,
        user_id: Optional[int] = None
    ) -> bool:
        """
        Отмена платежа.

        Args:
            db: Сессия базы данных
            transaction_id: ID транзакции
            user_id: ID пользователя (для проверки прав)

        Returns:
            bool: Успешность отмены

        Raises:
            BusinessLogicError: При ошибках отмены
        """
        try:
            transaction = await self.crud.get(db, id=transaction_id)
            if not transaction:
                raise BusinessLogicError("Transaction not found")

            if user_id and transaction.user_id != user_id:
                raise BusinessLogicError("Access denied")

            if transaction.status != TransactionStatus.PENDING:
                raise BusinessLogicError(f"Cannot cancel transaction with status {transaction.status}")

            # Пытаемся отменить у провайдера
            if transaction.payment_method == "cryptomus" and transaction.provider_payment_id:
                try:
                    cryptomus_api = get_payment_provider("cryptomus")
                    await cryptomus_api.cancel_payment(transaction.provider_payment_id)
                except Exception as e:
                    logger.warning(f"Failed to cancel payment with provider: {e}")

            # Обновляем статус в нашей БД
            transaction.status = TransactionStatus.CANCELLED
            transaction.updated_at = datetime.now(timezone.utc)
            await db.commit()

            logger.info(f"Payment cancelled: {transaction_id}")
            return True

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error cancelling payment: {e}")
            return False

    async def get_payment_statistics(
        self,
        db: AsyncSession,
        *,
        user_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Получение статистики платежей.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя (опционально)
            days: Период в днях

        Returns:
            Dict[str, Any]: Статистика платежей
        """
        try:
            return await self.crud.get_payment_stats(db, user_id=user_id, days=days)

        except Exception as e:
            logger.error(f"Error getting payment statistics: {e}")
            return {
                "total_transactions": 0,
                "completed_transactions": 0,
                "total_amount": "0.00000000",
                "success_rate": 0.0,
                "period_days": days
            }

    # Приватные методы для работы с провайдерами

    async def _create_cryptomus_payment(
        self,
        transaction: Transaction,
        payment_request: PaymentCreateRequest
    ) -> Dict[str, Any]:
        """
        Создание платежа через Cryptomus.

        Args:
            transaction: Транзакция
            payment_request: Параметры платежа

        Returns:
            Dict[str, Any]: Данные платежа от Cryptomus
        """
        try:
            cryptomus_api = get_payment_provider("cryptomus")

            return await cryptomus_api.create_payment(
                amount=payment_request.amount,
                currency=payment_request.currency,
                order_id=str(transaction.id),
                callback_url=payment_request.callback_url,
                success_url=payment_request.success_url,
                fail_url=payment_request.fail_url,
                description=payment_request.description
            )

        except Exception as e:
            logger.error(f"Error creating Cryptomus payment: {e}")
            raise

    async def _handle_cryptomus_webhook(
        self,
        db: AsyncSession,
        webhook_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Обработка webhook от Cryptomus.

        Args:
            db: Сессия базы данных
            webhook_data: Данные webhook

        Returns:
            Dict[str, Any]: Результат обработки
        """
        try:
            # Проверяем подпись webhook
            cryptomus_api = get_payment_provider("cryptomus")
            received_sign = webhook_data.get("sign", "")

            if not cryptomus_api.verify_webhook_signature(webhook_data, received_sign):
                raise BusinessLogicError("Invalid webhook signature")

            # Получаем транзакцию
            order_id = webhook_data.get("order_id")
            if not order_id:
                raise BusinessLogicError("No order_id in webhook")

            transaction = await self.crud.get(db, id=int(order_id))
            if not transaction:
                raise BusinessLogicError(f"Transaction {order_id} not found")

            # Обновляем статус
            provider_status = webhook_data.get("status", "")
            new_status = self._map_cryptomus_status(provider_status)

            await self._update_transaction_status(db, transaction, new_status, webhook_data)

            logger.info(f"Processed Cryptomus webhook for transaction {transaction.id}")

            return {
                "status": "success",
                "transaction_id": transaction.id,
                "new_status": new_status.value
            }

        except Exception as e:
            logger.error(f"Error processing Cryptomus webhook: {e}")
            raise

    async def _verify_cryptomus_payment(self, payment_uuid: str) -> Dict[str, Any]:
        """
        Проверка статуса платежа в Cryptomus.

        Args:
            payment_uuid: UUID платежа

        Returns:
            Dict[str, Any]: Информация о платеже
        """
        try:
            cryptomus_api = get_payment_provider("cryptomus")
            return await cryptomus_api.get_payment_info(payment_uuid)

        except Exception as e:
            logger.error(f"Error verifying Cryptomus payment: {e}")
            raise

    def _map_provider_status(self, payment_method: str, provider_status: str) -> TransactionStatus:
        """
        Маппинг статуса провайдера в наш внутренний статус.

        Args:
            payment_method: Метод оплаты
            provider_status: Статус от провайдера

        Returns:
            TransactionStatus: Внутренний статус
        """
        if payment_method == "cryptomus":
            return self._map_cryptomus_status(provider_status)
        else:
            return TransactionStatus.PENDING

    def _map_cryptomus_status(self, cryptomus_status: str) -> TransactionStatus:
        """
        Маппинг статуса Cryptomus в наш внутренний статус.

        Args:
            cryptomus_status: Статус от Cryptomus

        Returns:
            TransactionStatus: Внутренний статус
        """
        status_mapping = {
            "pending": TransactionStatus.PENDING,
            "process": TransactionStatus.PENDING,
            "paid": TransactionStatus.COMPLETED,
            "paid_over": TransactionStatus.COMPLETED,
            "payment_wait": TransactionStatus.PENDING,
            "confirming": TransactionStatus.PENDING,
            "confirmed": TransactionStatus.COMPLETED,
            "check": TransactionStatus.PENDING,
            "cancel": TransactionStatus.CANCELLED,
            "fail": TransactionStatus.FAILED,
            "wrong_amount": TransactionStatus.FAILED,
            "timeout": TransactionStatus.FAILED,
            "expired": TransactionStatus.FAILED
        }

        return status_mapping.get(cryptomus_status.lower(), TransactionStatus.PENDING)

    async def _update_transaction_status(
        self,
        db: AsyncSession,
        transaction: Transaction,
        new_status: TransactionStatus,
        provider_data: Dict[str, Any]
    ) -> None:
        """
        Обновление статуса транзакции и связанных объектов.

        Args:
            db: Сессия базы данных
            transaction: Транзакция
            new_status: Новый статус
            provider_data: Данные от провайдера
        """
        try:
            old_status = transaction.status
            transaction.status = new_status
            transaction.provider_metadata = str(provider_data)
            transaction.updated_at = datetime.now(timezone.utc)

            # Если платеж завершен успешно
            if new_status == TransactionStatus.COMPLETED and old_status != TransactionStatus.COMPLETED:
                await self._process_successful_payment(db, transaction)

            # Если платеж отменен или провален
            elif new_status in [TransactionStatus.CANCELLED, TransactionStatus.FAILED]:
                await self._process_failed_payment(db, transaction)

            await db.commit()
            logger.info(f"Transaction {transaction.id} status updated: {old_status} -> {new_status}")

        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating transaction status: {e}")
            raise

    async def _process_successful_payment(self, db: AsyncSession, transaction: Transaction) -> None:
        """
        Обработка успешного платежа.

        Args:
            db: Сессия базы данных
            transaction: Транзакция
        """
        try:
            # Обновляем баланс пользователя
            if transaction.user_id:
                user = await user_crud.get(db, id=transaction.user_id)
                if user:
                    await user_crud.update_balance(db, user=user, amount=transaction.amount)

            # Обновляем статус заказа
            if transaction.order_id:
                order = await order_crud.get(db, id=transaction.order_id)
                if order:
                    await order_crud.update_status(db, order=order, status=OrderStatus.PAID)

            logger.info(f"Processed successful payment for transaction {transaction.id}")

        except Exception as e:
            logger.error(f"Error processing successful payment: {e}")
            raise

    async def _process_failed_payment(self, db: AsyncSession, transaction: Transaction) -> None:
        """
        Обработка неудачного платежа.

        Args:
            db: Сессия базы данных
            transaction: Транзакция
        """
        try:
            # Обновляем статус заказа
            if transaction.order_id:
                order = await order_crud.get(db, id=transaction.order_id)
                if order and order.status == OrderStatus.PENDING:
                    await order_crud.update_status(db, order=order, status=OrderStatus.CANCELLED)

            logger.info(f"Processed failed payment for transaction {transaction.id}")

        except Exception as e:
            logger.error(f"Error processing failed payment: {e}")
            raise

    async def _send_payment_notification(
        self,
        transaction: Transaction,
        status: str,
        user_email: Optional[str] = None
    ) -> None:
        """
        Отправка уведомления о платеже.

        Args:
            transaction: Транзакция
            status: Статус платежа
            user_email: Email пользователя
        """
        try:
            # Здесь можно добавить отправку email/SMS уведомлений
            logger.info(f"Payment notification sent for transaction {transaction.id}: {status}")

        except Exception as e:
            logger.error(f"Error sending payment notification: {e}")

    async def _calculate_fees(self, amount: Decimal, payment_method: str) -> Decimal:
        """
        Расчет комиссий за платеж.

        Args:
            amount: Сумма платежа
            payment_method: Метод оплаты

        Returns:
            Decimal: Размер комиссии
        """
        try:
            # Комиссии по методам оплаты
            fee_rates = {
                "cryptomus": Decimal("0.02"),  # 2%
                "card": Decimal("0.03"),       # 3%
                "bank": Decimal("0.01")        # 1%
            }

            fee_rate = fee_rates.get(payment_method, Decimal("0.025"))  # 2.5% по умолчанию
            return amount * fee_rate

        except Exception as e:
            logger.error(f"Error calculating fees: {e}")
            return Decimal("0")

    async def _validate_payment_limits(
        self,
        db: AsyncSession,
        user_id: Optional[int],
        amount: Decimal,
        currency: str
    ) -> bool:
        """
        Проверка лимитов платежей.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            amount: Сумма платежа
            currency: Валюта

        Returns:
            bool: True если лимиты не превышены

        Raises:
            BusinessLogicError: При превышении лимитов
        """
        try:
            # Дневные лимиты
            daily_limit = Decimal("10000.00")  # $10,000 в день

            if user_id:
                # Проверяем дневной лимит пользователя
                daily_total = await self.crud.get_daily_total(db, user_id=user_id)
                if daily_total + amount > daily_limit:
                    raise BusinessLogicError(f"Daily limit exceeded. Limit: {daily_limit}, Current: {daily_total}")

            # Минимальные суммы
            min_amounts = {
                "USD": Decimal("1.00"),
                "EUR": Decimal("1.00"),
                "RUB": Decimal("100.00"),
                "BTC": Decimal("0.0001"),
                "ETH": Decimal("0.001"),
                "USDT": Decimal("1.00")
            }

            min_amount = min_amounts.get(currency, Decimal("1.00"))
            if amount < min_amount:
                raise BusinessLogicError(f"Amount below minimum. Minimum: {min_amount} {currency}")

            return True

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error validating payment limits: {e}")
            return True  # Разрешаем в случае ошибки

    # Реализация абстрактных методов BaseService
    async def create(self, db: AsyncSession, *, obj_in: TransactionCreate) -> Transaction:
        return await self.crud.create(db, obj_in=obj_in)

    async def get(self, db: AsyncSession, *, id: int) -> Optional[Transaction]:
        return await self.crud.get(db, id=id)

    async def update(self, db: AsyncSession, *, db_obj: Transaction, obj_in: TransactionUpdate) -> Transaction:
        return await self.crud.update(db, db_obj=db_obj, obj_in=obj_in)

    async def delete(self, db: AsyncSession, *, id: int) -> bool:
        result = await self.crud.delete(db, id=id)
        return result is not None

    async def get_multi(self, db: AsyncSession, *, skip: int = 0, limit: int = 100) -> List[Transaction]:
        return await self.crud.get_multi(db, skip=skip, limit=limit)


payment_service = PaymentService()
