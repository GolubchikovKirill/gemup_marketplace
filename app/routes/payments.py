"""
Production-ready роуты для платежей с повышенной безопасностью.
"""

import logging
import time
import uuid
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.dependencies import get_current_registered_user
from app.core.redis import get_redis, RedisClient
from app.models.models import User
from app.schemas.payment import PaymentCreateRequest, PaymentResponse, PaymentStatusResponse
from app.services.payment_service import payment_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payments", tags=["Payments"])


# Утилиты для background задач
async def log_payment_attempt(user_id: int, amount: float, ip_address: str):
    """Логирование попытки платежа."""
    logger.info(f"Payment attempt: user_id={user_id}, amount={amount}, ip={ip_address}")


def generate_error_id() -> str:
    """Генерация уникального ID ошибки."""
    return str(uuid.uuid4())[:8]


async def process_webhook_safely(webhook_data: dict, db: AsyncSession, redis: RedisClient, duplicate_key: str):
    """Безопасная обработка webhook."""
    try:
        await payment_service.process_webhook(db, webhook_data)
        await redis.set(duplicate_key, "1", expire=3600)
        logger.info(f"Webhook {webhook_data.get('order_id')} processed successfully")
    except Exception as webhook_error:
        logger.error(f"Error processing webhook: {webhook_error}")


def verify_webhook_signature(body: bytes, signature: str, secret: str = None) -> bool:
    """Проверка подписи webhook."""
    import hmac
    import hashlib

    if not secret:
        secret = settings.cryptomus_webhook_secret

    if not secret:
        logger.warning("Webhook secret not configured")
        return True  # В development режиме пропускаем проверку

    try:
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            body,
            hashlib.sha256
        ).hexdigest()

        # Убираем префиксы типа "sha256="
        if signature and signature.startswith('sha256='):
            signature = signature[7:]

        return hmac.compare_digest(expected_signature, signature or "")
    except Exception:
        return False


@router.post("/create",
             response_model=PaymentResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Создание платежа",
             responses={
                 201: {"description": "Платеж создан"},
                 400: {"description": "Ошибка валидации"},
                 429: {"description": "Превышен лимит платежей"}
             })
async def create_payment(
        payment_request: PaymentCreateRequest,
        request: Request,
        background_tasks: BackgroundTasks,
        current_user: User = Depends(get_current_registered_user),
        db: AsyncSession = Depends(get_db),
        redis: RedisClient = Depends(get_redis)
):
    """
    Создание платежа с дополнительной защитой.
    """
    start_time = time.time()

    try:
        # Валидация суммы платежа
        if payment_request.amount < Decimal('1.00'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "invalid_amount", "message": "Minimum payment amount is $1.00"}
            )

        if payment_request.amount > Decimal('10000.00'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "amount_too_large", "message": "Maximum payment amount is $10,000.00"}
            )

        # Rate limiting для платежей (10 платежей в час)
        user_key = f"payment:user:{current_user.id}"
        if not await redis.rate_limit_check(user_key, limit=10, window_seconds=3600):
            logger.warning(f"Payment rate limit exceeded for user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "payment_rate_limit",
                    "message": "Too many payment attempts",
                    "retry_after": 3600
                },
                headers={"Retry-After": "3600"}
            )

        # Проверка дублированных платежей
        duplicate_key = f"payment_duplicate:user:{current_user.id}:amount:{payment_request.amount}"
        if await redis.exists(duplicate_key):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "duplicate_payment", "message": "Similar payment already in progress"}
            )

        # Устанавливаем блокировку на 10 минут
        await redis.set(duplicate_key, "1", expire=600)

        try:
            payment_result = await payment_service.create_payment(
                db=db,
                user=current_user,
                amount=payment_request.amount,
                description=payment_request.description or "Balance top-up"
            )

            # Background задачи
            background_tasks.add_task(
                log_payment_attempt,
                user_id=current_user.id,
                amount=float(payment_request.amount),
                ip_address=request.client.host
            )

            duration = time.time() - start_time
            logger.info(
                f"Payment created in {duration:.3f}s",
                extra={
                    "user_id": current_user.id,
                    "amount": float(payment_request.amount),
                    "transaction_id": payment_result["transaction_id"],
                    "duration": duration
                }
            )

            return PaymentResponse(**payment_result, expires_in=3600)

        finally:
            # Убираем блокировку дублирования
            await redis.delete(duplicate_key)

    except HTTPException:
        raise
    except Exception as payment_error:
        duration = time.time() - start_time
        error_id = generate_error_id()
        logger.error(
            f"Payment creation failed in {duration:.3f}s: {payment_error}",
            exc_info=True,
            extra={
                "user_id": current_user.id,
                "amount": float(payment_request.amount),
                "error_id": error_id
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "payment_failed", "error_id": error_id}
        )


@router.get("/status/{transaction_id}",
           response_model=PaymentStatusResponse,
           summary="Получение статуса платежа")
async def get_payment_status(
        transaction_id: str,
        db: AsyncSession = Depends(get_db),
        redis: RedisClient = Depends(get_redis)
):
    """Получение статуса платежа по ID транзакции."""
    try:
        # Проверяем кеш
        cache_key = f"payment_status:{transaction_id}"
        cached_status = await redis.get_json(cache_key)

        if cached_status:
            return PaymentStatusResponse(**cached_status)

        # Получаем из БД
        payment_status = await payment_service.get_payment_status(db, transaction_id)

        # Кешируем на 5 минут
        await redis.set_json(cache_key, payment_status, expire=300)

        return PaymentStatusResponse(**payment_status)

    except ValueError as validation_error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "transaction_not_found", "message": str(validation_error)}
        )
    except Exception as status_error:
        logger.error(f"Error getting payment status for {transaction_id}: {status_error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "status_fetch_failed", "message": "Failed to retrieve payment status"}
        )


@router.get("/history",
           response_model=List[PaymentStatusResponse],
           summary="История платежей")
async def get_payment_history(
        current_user: User = Depends(get_current_registered_user),
        db: AsyncSession = Depends(get_db),
        redis: RedisClient = Depends(get_redis),
        skip: int = 0,
        limit: int = 50
):
    """Получение истории платежей пользователя."""
    try:
        # Проверяем кеш
        cache_key = f"payment_history:user:{current_user.id}:skip:{skip}:limit:{limit}"
        cached_history = await redis.get_json(cache_key)

        if cached_history:
            return [PaymentStatusResponse(**payment) for payment in cached_history]

        # Получаем из БД
        payment_history = await payment_service.get_user_payment_history(
            db, user_id=current_user.id, skip=skip, limit=limit
        )

        # Сериализуем для кеша
        serialized_history = []
        for payment in payment_history:
            if hasattr(payment, 'model_dump'):
                serialized_history.append(payment.model_dump())
            else:
                serialized_history.append({
                    k: str(v) if hasattr(v, '__str__') else v
                    for k, v in payment.__dict__.items()
                    if not k.startswith('_')
                })

        # Кешируем на 10 минут
        await redis.set_json(cache_key, serialized_history, expire=600)

        return [PaymentStatusResponse(**payment) for payment in serialized_history]

    except Exception as history_error:
        logger.error(f"Error getting payment history for user {current_user.id}: {history_error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "history_fetch_failed", "message": "Failed to retrieve payment history"}
        )


@router.post("/webhook/cryptomus",
             summary="Webhook Cryptomus",
             responses={200: {"description": "Webhook processed"}})
async def cryptomus_webhook(
        request: Request,
        background_tasks: BackgroundTasks,
        db: AsyncSession = Depends(get_db),
        redis: RedisClient = Depends(get_redis)
):
    """
    Webhook с улучшенной безопасностью и обработкой.
    """
    try:
        # Rate limiting для webhooks (1000 в час)
        client_ip = request.client.host
        webhook_key = f"webhook:ip:{client_ip}"
        if not await redis.rate_limit_check(webhook_key, limit=1000, window_seconds=3600):
            logger.warning(f"Webhook rate limit exceeded for IP {client_ip}")
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS)

        # Валидация подписи webhook
        body = await request.body()
        signature = request.headers.get("X-Cryptomus-Signature")

        if not verify_webhook_signature(body, signature):
            logger.warning(f"Invalid webhook signature from IP {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature"
            )

        webhook_data = await request.json()

        # Проверка дублированных webhook
        webhook_id = webhook_data.get("order_id")
        duplicate_key = f"webhook_processed:{webhook_id}"
        if await redis.exists(duplicate_key):
            logger.info(f"Webhook {webhook_id} already processed")
            return {"status": "already_processed"}

        # Обрабатываем webhook в background
        background_tasks.add_task(
            process_webhook_safely,
            webhook_data=webhook_data,
            db=db,
            redis=redis,
            duplicate_key=duplicate_key
        )

        return {"status": "accepted"}

    except HTTPException:
        raise
    except Exception as webhook_error:
        logger.error(f"Webhook processing error: {webhook_error}", exc_info=True)
        # Возвращаем 200 чтобы провайдер не повторял webhook
        return {"status": "error", "message": "Processing failed"}


@router.post("/test-webhook",
             summary="Тестовый webhook для разработки")
async def test_webhook(
        webhook_data: dict,
        background_tasks: BackgroundTasks,
        db: AsyncSession = Depends(get_db),
        redis: RedisClient = Depends(get_redis)
):
    """Тестовый endpoint для отладки webhook."""
    if not settings.is_development():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not available in production"
        )

    try:
        logger.info(f"Test webhook received: {webhook_data}")

        # Обрабатываем как обычный webhook
        background_tasks.add_task(
            process_webhook_safely,
            webhook_data=webhook_data,
            db=db,
            redis=redis,
            duplicate_key=f"test_webhook:{webhook_data.get('order_id', 'unknown')}"
        )

        return {"status": "test_webhook_accepted", "data": webhook_data}

    except Exception as test_error:
        logger.error(f"Test webhook error: {test_error}")
        return {"status": "test_error", "message": str(test_error)}


@router.post("/cancel/{transaction_id}",
             summary="Отмена платежа")
async def cancel_payment(
        transaction_id: str,
        current_user: User = Depends(get_current_registered_user),
        db: AsyncSession = Depends(get_db)
):
    """Отмена ожидающего платежа."""
    try:
        result = await payment_service.cancel_pending_payment(db, transaction_id)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "cannot_cancel", "message": "Payment cannot be cancelled"}
            )

        logger.info(f"Payment {transaction_id} cancelled by user {current_user.id}")
        return {"status": "cancelled", "transaction_id": transaction_id}

    except HTTPException:
        raise
    except Exception as cancel_error:
        logger.error(f"Error cancelling payment {transaction_id}: {cancel_error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "cancel_failed", "message": "Failed to cancel payment"}
        )
