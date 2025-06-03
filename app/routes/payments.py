"""
Роуты для платежей - исправлено для MVP.
"""

import logging
import time
import uuid
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.dependencies import get_current_registered_user
from app.core.exceptions import BusinessLogicError
from app.models.models import User, TransactionType, TransactionStatus
from app.schemas.base import MessageResponse
from app.schemas.payment import (
    PaymentCreateRequest, PaymentResponse, PaymentStatusResponse,
    PaymentCallbackData, PaymentMethodsResponse, PaymentRefundRequest,
    PaymentHistoryResponse, PaymentStatsResponse
)
from app.services.payment_service import payment_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payments", tags=["Payments"])


# Упрощенные утилиты для MVP
async def simple_rate_limit_check(user_id: int, limit: int = 10) -> bool:
    """Простая проверка rate limit без Redis."""
    # В MVP можно использовать in-memory кеш или пропустить проверку
    return True


def generate_error_id() -> str:
    """Генерация уникального ID ошибки."""
    return str(uuid.uuid4())[:8]


def verify_webhook_signature(body: bytes, signature: str, secret: str = None) -> bool:
    """Упрощенная проверка подписи webhook."""
    try:
        if not secret:
            secret = getattr(settings, 'cryptomus_webhook_secret', '')

        if not secret:
            logger.warning("Webhook secret not configured")
            return True  # В development режиме пропускаем проверку

        import hmac
        import hashlib

        expected_signature = hmac.new(
            secret.encode('utf-8'),
            body,
            hashlib.sha256
        ).hexdigest()

        if signature and signature.startswith('sha256='):
            signature = signature[7:]

        return hmac.compare_digest(expected_signature, signature or "")
    except Exception:
        return False


@router.get("/methods", response_model=PaymentMethodsResponse)
async def get_payment_methods():
    """Получение списка доступных методов оплаты."""
    try:
        methods = await payment_service.get_payment_methods()

        response_data = {
            "methods": methods,
            "default_method": "cryptomus"
        }

        return PaymentMethodsResponse(**response_data)

    except Exception as e:
        logger.error(f"Error getting payment methods: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "methods_fetch_failed", "message": "Failed to get payment methods"}
        )


@router.post("/create", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payment_request: PaymentCreateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db)
):
    """Создание платежа с упрощенной защитой для MVP."""
    start_time = time.time()

    try:
        # Упрощенная проверка rate limit
        if not await simple_rate_limit_check(current_user.id):
            logger.warning(f"Payment rate limit exceeded for user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "payment_rate_limit",
                    "message": "Too many payment attempts",
                    "retry_after": 3600
                }
            )

        payment_result = await payment_service.create_payment(
            db=db,
            user=current_user,
            payment_request=payment_request
        )

        duration = time.time() - start_time
        logger.info(
            f"Payment created in {duration:.3f}s",
            extra={
                "user_id": current_user.id,
                "amount": float(payment_request.amount),
                "transaction_id": payment_result.transaction_id,
                "duration": duration
            }
        )

        return payment_result

    except HTTPException:
        raise
    except BusinessLogicError as business_error:
        duration = time.time() - start_time
        logger.warning(f"Payment validation failed: {business_error}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "validation_failed", "message": str(business_error)}
        )
    except Exception as payment_error:
        duration = time.time() - start_time
        error_id = generate_error_id()
        logger.error(f"Payment creation failed: {payment_error}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "payment_failed", "error_id": error_id}
        )


@router.get("/status/{transaction_id}", response_model=PaymentStatusResponse)
async def get_payment_status(
    transaction_id: str,
    current_user: User = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db)
):
    """Получение статуса платежа по ID транзакции."""
    try:
        payment_status = await payment_service.get_payment_status(
            db, transaction_id=transaction_id, user_id=current_user.id
        )

        return PaymentStatusResponse(**payment_status)

    except BusinessLogicError as business_error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "transaction_not_found", "message": str(business_error)}
        )
    except Exception as status_error:
        logger.error(f"Error getting payment status for {transaction_id}: {status_error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "status_fetch_failed", "message": "Failed to retrieve payment status"}
        )


@router.get("/history", response_model=PaymentHistoryResponse)
async def get_payment_history(
    current_user: User = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
    transaction_type: Optional[TransactionType] = None,
    status_filter: Optional[TransactionStatus] = None
):
    """Получение истории платежей пользователя."""
    try:
        payment_history = await payment_service.get_user_transactions(
            db,
            user_id=current_user.id,
            transaction_type=transaction_type,
            status=status_filter,
            skip=skip,
            limit=limit
        )

        return PaymentHistoryResponse(**payment_history)

    except Exception as history_error:
        logger.error(f"Error getting payment history for user {current_user.id}: {history_error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "history_fetch_failed", "message": "Failed to retrieve payment history"}
        )


@router.get("/statistics", response_model=PaymentStatsResponse)
async def get_payment_statistics(
    current_user: User = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db),
    days: int = 30
):
    """Получение статистики платежей пользователя."""
    try:
        stats = await payment_service.get_payment_statistics(
            db, user_id=current_user.id, days=days
        )

        return PaymentStatsResponse(**stats)

    except Exception as stats_error:
        logger.error(f"Error getting payment statistics for user {current_user.id}: {stats_error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "stats_fetch_failed", "message": "Failed to retrieve payment statistics"}
        )


@router.post("/webhook/cryptomus")
async def cryptomus_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Webhook Cryptomus с упрощенной обработкой для MVP."""
    try:
        body = await request.body()
        signature = request.headers.get("X-Cryptomus-Signature")

        if not verify_webhook_signature(body, signature):
            logger.warning(f"Invalid webhook signature from IP {request.client.host}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature"
            )

        webhook_data = await request.json()

        # Простая проверка дублированных webhook
        webhook_id = webhook_data.get("order_id")
        logger.info(f"Processing webhook {webhook_id}")

        # Преобразуем в схему
        callback_data = PaymentCallbackData(**webhook_data)

        # Обрабатываем webhook
        success = await payment_service.process_webhook(
            db, webhook_data=callback_data, provider="cryptomus"
        )

        if success:
            logger.info(f"Webhook {webhook_id} processed successfully")
            return {"status": "success"}
        else:
            logger.warning(f"Webhook {webhook_id} processing failed")
            return {"status": "failed"}

    except HTTPException:
        raise
    except Exception as webhook_error:
        logger.error(f"Webhook processing error: {webhook_error}", exc_info=True)
        # Возвращаем 200 чтобы провайдер не повторял webhook
        return {"status": "error", "message": "Processing failed"}


@router.post("/cancel/{transaction_id}", response_model=MessageResponse)
async def cancel_payment(
    transaction_id: str,
    current_user: User = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db)
):
    """Отмена ожидающего платежа."""
    try:
        success = await payment_service.cancel_payment(
            db,
            transaction_id=transaction_id,
            user_id=current_user.id
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "cannot_cancel", "message": "Payment cannot be cancelled"}
            )

        logger.info(f"Payment {transaction_id} cancelled by user {current_user.id}")
        return MessageResponse(
            message="Payment cancelled successfully",
            success=True,
            details={"transaction_id": transaction_id}
        )

    except BusinessLogicError as business_error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "cancel_failed", "message": str(business_error)}
        )
    except Exception as cancel_error:
        logger.error(f"Error cancelling payment {transaction_id}: {cancel_error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "cancel_failed", "message": "Failed to cancel payment"}
        )


@router.post("/refund", response_model=Dict[str, Any])
async def create_refund(
    refund_request: PaymentRefundRequest,
    current_user: User = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db)
):
    """Создание возврата средств (упрощенная версия для MVP)."""
    try:
        # Проверяем права администратора
        if not getattr(current_user, 'is_admin', False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

        refund_result = await payment_service.create_refund(
            db, refund_request=refund_request
        )

        logger.info(f"Refund created for transaction {refund_request.transaction_id}")
        return refund_result

    except BusinessLogicError as business_error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "refund_failed", "message": str(business_error)}
        )
    except Exception as refund_error:
        logger.error(f"Error creating refund: {refund_error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "refund_failed", "message": "Failed to create refund"}
        )
