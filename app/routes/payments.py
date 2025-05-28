import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.dependencies import get_current_registered_user
from app.core.exceptions import BusinessLogicError
from app.models.models import User
from app.schemas.base import MessageResponse
from app.schemas.transaction import (
    PaymentCreateRequest, PaymentResponse, TransactionResponse,
    WebhookData
)
from app.services.payment_service import payment_service
from app.crud.transaction import transaction_crud

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/create", response_model=PaymentResponse)
async def create_payment(
        payment_request: PaymentCreateRequest,
        current_user: User = Depends(get_current_registered_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Создание платежа для пополнения баланса

    - **amount**: Сумма пополнения (минимум $1.00)
    - **currency**: Валюта (по умолчанию USD)
    - **description**: Описание платежа
    """
    try:
        payment_result = await payment_service.create_payment(
            db,
            user=current_user,
            amount=payment_request.amount,
            currency=payment_request.currency,
            description=payment_request.description or "Balance top-up"
        )

        logger.info(f"Payment created for user {current_user.id}: {payment_request.amount}")
        return PaymentResponse(**payment_result)

    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except Exception as e:
        logger.error(f"Error creating payment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create payment"
        )


@router.get("/status/{transaction_id}")
async def get_payment_status(
        transaction_id: str,
        current_user: User = Depends(get_current_registered_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Получение статуса платежа

    - **transaction_id**: ID транзакции
    """
    try:
        # Проверяем, что транзакция принадлежит пользователю
        transaction = await transaction_crud.get_by_transaction_id(
            db, transaction_id=transaction_id
        )

        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found"
            )

        if transaction.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this transaction"
            )

        payment_status = await payment_service.get_payment_status(db, transaction_id)
        return payment_status

    except HTTPException:
        raise
    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except Exception as e:
        logger.error(f"Error getting payment status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get payment status"
        )


@router.get("/history", response_model=List[TransactionResponse])
async def get_payment_history(
        current_user: User = Depends(get_current_registered_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Получение истории платежей пользователя
    """
    try:
        transactions = await transaction_crud.get_user_transactions(
            db, user_id=current_user.id
        )

        return transactions

    except Exception as e:
        logger.error(f"Error getting payment history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get payment history"
        )


@router.post("/webhook/cryptomus", response_model=MessageResponse)
async def cryptomus_webhook(
        request: Request,
        db: AsyncSession = Depends(get_db)
):
    """
    Webhook для обработки уведомлений от Cryptomus

    Этот эндпоинт вызывается Cryptomus при изменении статуса платежа
    """
    try:
        # Получаем данные webhook
        webhook_data = await request.json()

        logger.info(f"Received Cryptomus webhook: {webhook_data}")

        # Обрабатываем webhook
        success = await payment_service.process_webhook(db, webhook_data)

        if success:
            return MessageResponse(message="Webhook processed successfully")
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Webhook processing failed"
            )

    except Exception as e:
        logger.error(f"Error processing Cryptomus webhook: {e}")
        # Возвращаем 200 чтобы Cryptomus не повторял запрос
        return MessageResponse(message="Webhook received")


@router.post("/test-webhook", response_model=MessageResponse)
async def test_webhook(
        webhook_data: WebhookData,
        db: AsyncSession = Depends(get_db)
):
    """
    Тестовый эндпоинт для проверки обработки webhook
    (только для разработки)
    """
    try:
        success = await payment_service.process_webhook(
            db, webhook_data.model_dump()
        )

        if success:
            return MessageResponse(message="Test webhook processed successfully")
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Test webhook processing failed"
            )

    except Exception as e:
        logger.error(f"Error processing test webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Test webhook processing failed"
        )
