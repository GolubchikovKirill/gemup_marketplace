"""
Роуты для управления заказами.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.dependencies import get_current_registered_user
from app.core.exceptions import BusinessLogicError
from app.core.redis import get_redis, RedisClient
from app.models.models import User, OrderStatus
from app.schemas.base import MessageResponse
from app.schemas.order import OrderResponse, OrderListResponse, OrderStatsResponse
from app.services.order_service import order_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis)
):
    """Создание заказа из корзины."""
    try:
        # Rate limiting
        user_key = f"create_order:user:{current_user.id}"
        if not await redis.rate_limit_check(user_key, limit=5, window_seconds=600):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"error": "rate_limit_exceeded", "message": "Too many order creation attempts"}
            )

        # Создание заказа
        order = await order_service.create_order_from_cart(db, user=current_user)

        # Background task для уведомлений
        background_tasks.add_task(_send_order_notification, current_user.email, order.order_number)

        logger.info(f"Order created: {order.id} for user {current_user.id}")
        return order

    except BusinessLogicError as e:
        if "Insufficient balance" in str(e):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={"error": "insufficient_balance", "message": str(e)}
            )
        elif "Cart is empty" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "empty_cart", "message": str(e)}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "validation_error", "message": str(e)}
            )

    except Exception as e:
        logger.error(f"Error creating order for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": "Failed to create order"}
        )


@router.get("/", response_model=OrderListResponse)
async def get_orders(
    current_user: User = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db),
    status_filter: Optional[OrderStatus] = Query(None, description="Фильтр по статусу"),
    skip: int = Query(0, ge=0, description="Пропустить записей"),
    limit: int = Query(50, ge=1, le=100, description="Максимум записей")
):
    """Получение списка заказов пользователя."""
    try:
        orders = await order_service.get_user_orders(
            db, user_id=current_user.id, status=status_filter, skip=skip, limit=limit
        )

        # Подсчитываем общее количество
        total_orders = await order_service.get_user_orders(
            db, user_id=current_user.id, status=status_filter, skip=0, limit=1000
        )
        total = len(total_orders)

        pages = (total + limit - 1) // limit if total > 0 else 0

        return OrderListResponse(
            orders=orders,
            total=total,
            page=(skip // limit) + 1,
            per_page=limit,
            pages=pages
        )

    except Exception as e:
        logger.error(f"Error getting orders for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "fetch_failed", "message": "Failed to retrieve orders"}
        )


@router.get("/stats", response_model=OrderStatsResponse)
async def get_orders_summary(
    current_user: User = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365, description="Период в днях")
):
    """Получение сводки по заказам пользователя."""
    try:
        summary = await order_service.get_order_summary(db, user_id=current_user.id, days=days)
        return OrderStatsResponse(**summary)

    except Exception as e:
        logger.error(f"Error getting order summary for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "summary_failed", "message": "Failed to retrieve order summary"}
        )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db)
):
    """Получение детальной информации о заказе."""
    try:
        order = await order_service.get_order_by_id(db, order_id=order_id, user_id=current_user.id)

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "order_not_found", "message": "Order not found"}
            )

        return order

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting order {order_id} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "fetch_failed", "message": "Failed to retrieve order"}
        )


@router.post("/{order_id}/cancel", response_model=MessageResponse)
async def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db),
    reason: Optional[str] = Query(None, max_length=500, description="Причина отмены")
):
    """Отмена заказа пользователем."""
    try:
        success = await order_service.cancel_order(
            db, order_id=order_id, user_id=current_user.id, reason=reason
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "cancel_failed", "message": "Failed to cancel order"}
            )

        return MessageResponse(
            message="Order cancelled successfully",
            success=True,
            details={"order_id": order_id, "reason": reason}
        )

    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "cancel_failed", "message": str(e)}
        )
    except Exception as e:
        logger.error(f"Error cancelling order {order_id} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "cancel_failed", "message": "Failed to cancel order"}
        )


@router.get("/number/{order_number}", response_model=OrderResponse)
async def get_order_by_number(
    order_number: str,
    current_user: User = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db)
):
    """Получение заказа по номеру."""
    try:
        order = await order_service.get_order_by_number(
            db, order_number=order_number, user_id=current_user.id
        )

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "order_not_found", "message": "Order not found"}
            )

        return order

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting order by number {order_number}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "fetch_failed", "message": "Failed to retrieve order"}
        )


# Внутренние функции
async def _send_order_notification(email: str, order_number: str):
    """Отправка уведомления о заказе."""
    try:
        logger.info(f"Sending order notification to {email} for order {order_number}")
        # Здесь была бы реальная отправка email
    except Exception as e:
        logger.error(f"Failed to send order notification: {e}")
