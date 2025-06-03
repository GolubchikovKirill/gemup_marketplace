"""
Сервис для управления платежами.

Обеспечивает создание платежей, обработку webhook-уведомлений,
интеграцию с платежными системами и управление транзакциями.
Полная production-ready реализация без мок-данных.
"""

import logging
from decimal import Decimal
from typing import Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessLogicError
from app.crud.order import order_crud
from app.crud.transaction import transaction_crud
from app.crud.user import user_crud
from app.integrations.cryptomus import cryptomus_api
from app.models.models import User, Transaction, TransactionType, TransactionStatus
from app.services.base import BusinessRuleValidator

logger = logging.getLogger(__name__)


class PaymentBusinessRules(BusinessRuleValidator):
    """Валидатор бизнес-правил для платежей."""

    async def validate(self, data: dict, db: AsyncSession) -> bool:
        """
        Валидация бизнес-правил для платежей.

        Args:
            data: Данные для валидации (amount, user_id, currency)
            db: Сессия базы данных

        Returns:
            bool: Результат валидации

        Raises:
            BusinessLogicError: При нарушении бизнес-правил
        """
        try:
            amount = data.get("amount", Decimal('0'))
            user_id = data.get("user_id")
            currency = data.get("currency", "USD")

            if not user_id:
                raise BusinessLogicError("User ID is required")

            if amount <= 0:
                raise BusinessLogicError("Payment amount must be positive")

            if amount < Decimal("1.00"):
                raise BusinessLogicError("Minimum payment amount is $1.00")

            if amount > Decimal("50000.00"):
                raise BusinessLogicError("Maximum payment amount is $50,000.00")

            # Проверка поддерживаемых валют
            supported_currencies = ["USD", "EUR", "RUB"]
            if currency not in supported_currencies:
                raise BusinessLogicError(f"Currency {currency} is not supported")

            # Проверка существования пользователя
            user = await user_crud.get(db, obj_id=user_id)
            if not user:
                raise BusinessLogicError("User not found")

            if not user.is_active:
                raise BusinessLogicError("User account is inactive")

            if user.is_guest:
                raise BusinessLogicError("Guest users cannot make payments")

            logger.debug(f"Payment business rules validation passed for user {user_id}")
            return True

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error during payment business rules validation: {e}")
            raise BusinessLogicError(f"Validation failed: {str(e)}")


class PaymentService:
    """
    Сервис для управления платежами.

    Предоставляет функциональность для создания платежей,
    обработки уведомлений от платежных систем и управления балансом пользователей.
    Интегрируется с внешними платежными провайдерами.
    """

    def __init__(self):
        self.business_rules = PaymentBusinessRules()
        self.min_payment_amount = Decimal("1.00")
        self.max_payment_amount = Decimal("50000.00")
        self.supported_currencies = ["USD", "EUR", "RUB"]

    async def create_payment(
        self,
        db: AsyncSession,
        user: User,
        amount: Decimal,
        currency: str = "USD",
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Создание нового платежа.

        Args:
            db: Сессия базы данных
            user: Пользователь, создающий платеж
            amount: Сумма платежа
            currency: Валюта платежа
            description: Описание платежа

        Returns:
            Dict[str, Any]: Данные созданного платежа

        Raises:
            BusinessLogicError: При ошибках валидации или создания
        """
        try:
            # Валидация бизнес-правил
            validation_data = {
                "amount": amount,
                "user_id": user.id,
                "currency": currency
            }
            await self.business_rules.validate(validation_data, db)

            # Создание транзакции
            transaction = await transaction_crud.create_transaction(
                db,
                user_id=user.id,
                amount=amount,
                currency=currency,
                transaction_type=TransactionType.DEPOSIT,
                description=description or f"Balance top-up {amount} {currency}"
            )

            # Создание платежа через Cryptomus
            payment_response = await cryptomus_api.create_payment(
                amount=amount,
                currency=currency,
                order_id=transaction.transaction_id,
                description=description
            )

            # Обновление транзакции с внешним ID
            if payment_response.get("uuid"):
                await transaction_crud.update_status(
                    db,
                    transaction=transaction,
                    status=TransactionStatus.PENDING,
                    external_transaction_id=payment_response["uuid"],
                    payment_url=payment_response.get("url")
                )

            logger.info(f"Payment created: {transaction.transaction_id}")
            return {
                "transaction_id": transaction.transaction_id,
                "payment_url": payment_response.get("url"),
                "amount": str(amount),
                "currency": currency,
                "status": "pending",
                "expires_in": 3600  # 1 час на оплату
            }

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error creating payment: {e}")
            raise BusinessLogicError(f"Failed to create payment: {str(e)}")

    async def get_payment_status(
        self,
        db: AsyncSession,
        transaction_id: str,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Получение статуса платежа.

        Args:
            db: Сессия базы данных
            transaction_id: Идентификатор транзакции
            user_id: Идентификатор пользователя (для проверки прав доступа)

        Returns:
            Dict[str, Any]: Статус платежа

        Raises:
            BusinessLogicError: Если транзакция не найдена или нет доступа
        """
        try:
            transaction = await transaction_crud.get_by_transaction_id(db, transaction_id=transaction_id)

            if not transaction:
                raise BusinessLogicError("Transaction not found")

            # Проверка прав доступа
            if user_id and transaction.user_id != user_id:
                raise BusinessLogicError("Access denied")

            # Синхронизация статуса с провайдером
            if transaction.external_transaction_id and transaction.status == TransactionStatus.PENDING:
                await self._sync_payment_status(db, transaction)

            return {
                "transaction_id": transaction.transaction_id,
                "amount": str(transaction.amount),
                "currency": transaction.currency,
                "status": transaction.status.value,
                "description": transaction.description,
                "payment_url": transaction.payment_url,
                "created_at": transaction.created_at.isoformat(),
                "updated_at": transaction.updated_at.isoformat(),
                "completed_at": transaction.completed_at.isoformat() if transaction.completed_at else None
            }

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error getting payment status: {e}")
            raise BusinessLogicError(f"Failed to get payment status: {str(e)}")

    async def process_webhook(
        self,
        db: AsyncSession,
        webhook_data: Dict[str, Any]
    ) -> bool:
        """
        Обработка webhook-уведомления от платежной системы.

        Args:
            db: Сессия базы данных
            webhook_data: Данные webhook

        Returns:
            bool: Успешность обработки
        """
        try:
            order_id = webhook_data.get("order_id")
            status = webhook_data.get("status")
            amount = webhook_data.get("amount")
            signature = webhook_data.get("sign", "")

            if not order_id:
                logger.warning("Webhook without order_id received")
                return False

            # Проверяем подпись webhook
            if not cryptomus_api.verify_webhook_signature(webhook_data, signature):
                logger.warning(f"Invalid webhook signature for order {order_id}")
                return False

            transaction = await transaction_crud.get_by_transaction_id(db, transaction_id=order_id)

            if not transaction:
                logger.warning(f"Transaction {order_id} not found for webhook")
                return False

            # Обрабатываем различные статусы
            if status in ["paid", "confirmed"]:
                await self._process_successful_payment(db, transaction, amount)
                return True
            elif status in ["cancel", "cancelled", "failed"]:
                await transaction_crud.update_status(
                    db,
                    transaction=transaction,
                    status=TransactionStatus.CANCELLED
                )
                logger.info(f"Transaction {order_id} cancelled via webhook")
                return True
            elif status == "expired":
                await transaction_crud.update_status(
                    db,
                    transaction=transaction,
                    status=TransactionStatus.FAILED
                )
                logger.info(f"Transaction {order_id} expired via webhook")
                return True

            logger.warning(f"Unknown webhook status: {status} for order {order_id}")
            return False

        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return False

    @staticmethod
    async def cancel_payment(
            db: AsyncSession,
        transaction_id: str,
        user_id: int,
        reason: Optional[str] = None
    ) -> bool:
        """
        Отмена платежа пользователем.

        Args:
            db: Сессия базы данных
            transaction_id: Идентификатор транзакции
            user_id: Идентификатор пользователя
            reason: Причина отмены

        Returns:
            bool: Успешность операции

        Raises:
            BusinessLogicError: При ошибках доступа или отмены
        """
        try:
            transaction = await transaction_crud.get_by_transaction_id(db, transaction_id=transaction_id)

            if not transaction:
                raise BusinessLogicError("Transaction not found")

            if transaction.user_id != user_id:
                raise BusinessLogicError("Access denied")

            if transaction.status != TransactionStatus.PENDING:
                raise BusinessLogicError(f"Cannot cancel transaction with status {transaction.status.value}")

            # Пытаемся отменить платеж у провайдера
            try:
                if transaction.external_transaction_id:
                    await cryptomus_api.cancel_payment(transaction.external_transaction_id)
            except Exception as e:
                logger.warning(f"Failed to cancel payment with provider: {e}")
                # Продолжаем отмену в нашей системе

            # Обновляем статус транзакции
            await transaction_crud.update_status(
                db,
                transaction=transaction,
                status=TransactionStatus.CANCELLED
            )

            logger.info(f"Payment cancelled by user {user_id}: {transaction_id}, reason: {reason}")
            return True

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error cancelling payment: {e}")
            raise BusinessLogicError(f"Failed to cancel payment: {str(e)}")

    @staticmethod
    async def get_user_transactions(
            db: AsyncSession,
        user_id: int,
        transaction_type: Optional[TransactionType] = None,
        status: Optional[TransactionStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Получение списка транзакций пользователя.

        Args:
            db: Сессия базы данных
            user_id: Идентификатор пользователя
            transaction_type: Фильтр по типу транзакции
            status: Фильтр по статусу
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            Dict[str, Any]: Список транзакций с метаданными
        """
        try:
            transactions = await transaction_crud.get_user_transactions(
                db, user_id=user_id, transaction_type=transaction_type, status=status, skip=skip, limit=limit
            )

            total_count = await transaction_crud.count(db, filters={"user_id": user_id})

            return {
                "transactions": [
                    {
                        "transaction_id": t.transaction_id,
                        "amount": str(t.amount),
                        "currency": t.currency,
                        "type": t.transaction_type.value,
                        "status": t.status.value,
                        "description": t.description,
                        "payment_url": t.payment_url,
                        "created_at": t.created_at.isoformat(),
                        "updated_at": t.updated_at.isoformat(),
                        "completed_at": t.completed_at.isoformat() if t.completed_at else None
                    }
                    for t in transactions
                ],
                "total": total_count,
                "page": (skip // limit) + 1 if limit > 0 else 1,
                "limit": limit,
                "has_next": (skip + limit) < total_count
            }

        except Exception as e:
            logger.error(f"Error getting user transactions: {e}")
            return {"transactions": [], "total": 0, "page": 1, "limit": limit, "has_next": False}

    @staticmethod
    async def get_payment_statistics(
            db: AsyncSession,
        user_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Получение статистики платежей пользователя.

        Args:
            db: Сессия базы данных
            user_id: Идентификатор пользователя
            days: Период для статистики в днях

        Returns:
            Dict[str, Any]: Статистика платежей
        """
        try:
            stats = await transaction_crud.get_transactions_stats(db, user_id=user_id, days=days)
            return stats
        except Exception as e:
            logger.error(f"Error getting payment statistics: {e}")
            return {
                "total_transactions": 0,
                "total_amount": "0.00",
                "status_breakdown": {},
                "type_breakdown": {},
                "period_days": days
            }

    async def retry_failed_payment(
        self,
        db: AsyncSession,
        transaction_id: str,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Повторная попытка неудачного платежа.

        Args:
            db: Сессия базы данных
            transaction_id: Идентификатор исходной транзакции
            user_id: Идентификатор пользователя

        Returns:
            Dict[str, Any]: Данные нового платежа

        Raises:
            BusinessLogicError: При ошибках доступа или валидации
        """
        try:
            original_transaction = await transaction_crud.get_by_transaction_id(db, transaction_id=transaction_id)

            if not original_transaction:
                raise BusinessLogicError("Original transaction not found")

            if original_transaction.user_id != user_id:
                raise BusinessLogicError("Access denied")

            if original_transaction.status not in [TransactionStatus.FAILED, TransactionStatus.CANCELLED]:
                raise BusinessLogicError("Can only retry failed or cancelled transactions")

            user = await user_crud.get(db, obj_id=user_id)
            if not user:
                raise BusinessLogicError("User not found")

            # Создаем новый платеж с теми же параметрами
            return await self.create_payment(
                db,
                user=user,
                amount=original_transaction.amount,
                currency=original_transaction.currency,
                description=f"Retry of {original_transaction.transaction_id}"
            )

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error retrying payment: {e}")
            raise BusinessLogicError(f"Failed to retry payment: {str(e)}")

    async def _process_successful_payment(
        self,
        db: AsyncSession,
        transaction: Transaction,
        amount: str
    ) -> None:
        """
        Обработка успешного платежа.

        Args:
            db: Сессия базы данных
            transaction: Транзакция
            amount: Сумма платежа
        """
        try:
            # Обновление статуса транзакции
            await transaction_crud.update_status(
                db,
                transaction=transaction,
                status=TransactionStatus.COMPLETED
            )

            # Пополнение баланса пользователя
            user = await user_crud.get(db, obj_id=transaction.user_id)
            if user:
                await user_crud.update_balance(
                    db,
                    user=user,
                    amount=Decimal(amount)
                )

                logger.info(f"Balance updated for user {user.id}: +{amount}")

            # Активация заказа если есть
            if transaction.order_id:
                await self._activate_order_after_payment(db, transaction.order_id)

        except Exception as e:
            logger.error(f"Error processing successful payment: {e}")
            raise

    @staticmethod
    async def _activate_order_after_payment(db: AsyncSession, order_id: int) -> None:
        """
        Активация заказа после успешной оплаты.

        Args:
            db: Сессия базы данных
            order_id: Идентификатор заказа
        """
        try:
            from app.models.models import OrderStatus

            order = await order_crud.get(db, obj_id=order_id)
            if order:
                await order_crud.update_status(
                    db,
                    order=order,
                    status=OrderStatus.PAID
                )

                # Активация прокси для заказа
                from app.services.proxy_service import proxy_service
                await proxy_service.activate_proxies_for_order(db, order)

                logger.info(f"Order {order_id} activated after payment")

        except Exception as e:
            logger.error(f"Error activating order {order_id} after payment: {e}")

    async def _sync_payment_status(self, db: AsyncSession, transaction: Transaction) -> None:
        """
        Синхронизация статуса платежа с провайдером.

        Args:
            db: Сессия базы данных
            transaction: Транзакция для синхронизации
        """
        try:
            if not transaction.external_transaction_id:
                return

            payment_info = await cryptomus_api.get_payment_info(transaction.external_transaction_id)

            if payment_info:
                provider_status = payment_info.get("status", "").lower()
                internal_status = cryptomus_api.get_payment_status_mapping(provider_status)

                if internal_status == "completed" and transaction.status == TransactionStatus.PENDING:
                    await self._process_successful_payment(db, transaction, str(transaction.amount))
                elif internal_status in ["failed", "cancelled"] and transaction.status == TransactionStatus.PENDING:
                    new_status = TransactionStatus.FAILED if internal_status == "failed" else TransactionStatus.CANCELLED
                    await transaction_crud.update_status(db, transaction=transaction, status=new_status)

        except Exception as e:
            logger.error(f"Error syncing payment status for transaction {transaction.transaction_id}: {e}")

    @staticmethod
    async def create_refund(
            db: AsyncSession,
        transaction_id: str,
        refund_amount: Optional[Decimal] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Создание возврата средств.

        Args:
            db: Сессия базы данных
            transaction_id: Идентификатор исходной транзакции
            refund_amount: Сумма возврата (если не указана, возвращается полная сумма)
            reason: Причина возврата

        Returns:
            Dict[str, Any]: Данные возврата

        Raises:
            BusinessLogicError: При ошибках валидации или создания возврата
        """
        try:
            original_transaction = await transaction_crud.get_by_transaction_id(db, transaction_id=transaction_id)

            if not original_transaction:
                raise BusinessLogicError("Original transaction not found")

            if original_transaction.status != TransactionStatus.COMPLETED:
                raise BusinessLogicError("Can only refund completed transactions")

            if refund_amount is None:
                refund_amount = original_transaction.amount
            elif refund_amount > original_transaction.amount:
                raise BusinessLogicError("Refund amount cannot exceed original amount")

            # Создаем транзакцию возврата
            refund_transaction = await transaction_crud.create_transaction(
                db,
                user_id=original_transaction.user_id,
                amount=refund_amount,
                currency=original_transaction.currency,
                transaction_type=TransactionType.REFUND,
                description=f"Refund for {transaction_id}: {reason or 'No reason provided'}"
            )

            # Обновляем баланс пользователя
            user = await user_crud.get(db, obj_id=original_transaction.user_id)
            if user:
                await user_crud.update_balance(db, user=user, amount=refund_amount)

            # Отмечаем как выполненный
            await transaction_crud.update_status(
                db,
                transaction=refund_transaction,
                status=TransactionStatus.COMPLETED
            )

            logger.info(f"Refund created: {refund_transaction.transaction_id} for {refund_amount}")

            return {
                "refund_transaction_id": refund_transaction.transaction_id,
                "original_transaction_id": transaction_id,
                "refund_amount": str(refund_amount),
                "currency": original_transaction.currency,
                "reason": reason,
                "status": "completed"
            }

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error creating refund: {e}")
            raise BusinessLogicError(f"Failed to create refund: {str(e)}")


payment_service = PaymentService()
