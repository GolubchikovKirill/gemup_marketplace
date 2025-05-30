import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.dependencies import get_current_registered_user
from app.core.exceptions import BusinessLogicError
from app.models.models import User, OrderStatus
from app.schemas.base import MessageResponse
from app.schemas.order import OrderResponse
from app.services.order_service import order_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
        current_user: User = Depends(get_current_registered_user),
        db: AsyncSession = Depends(get_db)
):
    """Создание заказа из корзины"""
    try:
        order = await order_service.create_order_from_cart(db, current_user)

        logger.info(f"Order created for user {current_user.id}: {order.order_number}")
        return order

    except BusinessLogicError as e:
        if "Insufficient balance" in str(e):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=str(e)
            )
        elif "Cart is empty" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create order"
        )


@router.get("/", response_model=List[OrderResponse])
async def get_orders(
        current_user: User = Depends(get_current_registered_user),
        db: AsyncSession = Depends(get_db)
):
    """Получение списка заказов пользователя"""
    try:
        orders = await order_service.get_user_orders(db, user_id=current_user.id)

        logger.info(f"Retrieved {len(orders)} orders for user {current_user.id}")
        return orders

    except Exception as e:
        logger.error(f"Error getting orders for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get orders"
        )


@router.get("/summary")
async def get_order_summary(
        current_user: User = Depends(get_current_registered_user),
        db: AsyncSession = Depends(get_db)
):
    """Получение сводки по заказам пользователя"""
    try:
        summary = await order_service.get_order_summary(db, user_id=current_user.id)

        logger.info(f"Retrieved order summary for user {current_user.id}")
        return summary

    except Exception as e:
        logger.error(f"Error getting order summary for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get order summary"
        )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
        order_id: int,
        current_user: User = Depends(get_current_registered_user),
        db: AsyncSession = Depends(get_db)
):
    """Получение заказа по ID"""
    try:
        order = await order_service.get_order_by_id(db, order_id=order_id, user_id=current_user.id)

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )

        return order

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting order {order_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get order"
        )


# ДОБАВЛЕНО: Недостающие роуты
@router.post("/{order_id}/cancel", response_model=MessageResponse)
async def cancel_order(
        order_id: int,
        current_user: User = Depends(get_current_registered_user),
        db: AsyncSession = Depends(get_db)
):
    """Отмена заказа"""
    try:
        success = await order_service.cancel_order(db, order_id=order_id, user_id=current_user.id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found or cannot be cancelled"
            )

        return MessageResponse(message="Order cancelled successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling order {order_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel order"
        )


@router.put("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
        order_id: int,
        status_update: dict,
        current_user: User = Depends(get_current_registered_user),
        db: AsyncSession = Depends(get_db)
):
    """Обновление статуса заказа"""
    try:
        new_status = OrderStatus(status_update.get("status"))
        order = await order_service.update_order_status(
            db, order_id=order_id, status=new_status, user_id=current_user.id
        )

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )

        return order

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating order status {order_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update order status"
        )


@router.get("/number/{order_number}", response_model=OrderResponse)
async def get_order_by_number(
        order_number: str,
        current_user: User = Depends(get_current_registered_user),
        db: AsyncSession = Depends(get_db)
):
    """Получение заказа по номеру"""
    try:
        order = await order_service.get_order_by_number(db, order_number=order_number, user_id=current_user.id)

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )

        return order

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting order by number {order_number}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get order"
        )


@router.get("/public/{order_number}")
async def get_public_order_info(
        order_number: str,
        db: AsyncSession = Depends(get_db)
):
    """Получение публичной информации о заказе"""
    try:
        order = await order_service.get_public_order_info(db, order_number=order_number)

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )

        return {
            "order_number": order.order_number,
            "status": order.status,
            "total_amount": str(order.total_amount),
            "currency": order.currency,
            "created_at": order.created_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting public order info {order_number}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get order info"
        )
