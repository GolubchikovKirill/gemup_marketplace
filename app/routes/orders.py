import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.dependencies import get_current_user_from_token, get_current_user_or_create_guest
from app.core.exceptions import InsufficientFundsError, BusinessLogicError
from app.models.models import User
from app.schemas.base import MessageResponse
from app.schemas.order import (
    OrderResponse,
    OrderCreate,
    OrderStatusUpdate,
    OrderPublic
)
from app.services.order_service import order_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
        order_data: Optional[OrderCreate] = None,
        current_user: User = Depends(get_current_user_or_create_guest),
        db: AsyncSession = Depends(get_db)
):
    """
    Создание заказа из корзины

    - Создает заказ из всех товаров в корзине
    - Резервирует товары на складе
    - Списывает средства с баланса (для зарегистрированных пользователей)
    - Очищает корзину после успешного создания
    """
    try:
        # Получаем данные заказа или используем дефолтные
        payment_method = order_data.payment_method if order_data else None
        notes = order_data.notes if order_data else None

        # Создаем заказ
        order = await order_service.create_order_from_cart(
            db,
            user=current_user,
            payment_method=payment_method,
            notes=notes
        )

        logger.info(f"Order {order.order_number} created for user {current_user.id}")
        return order

    except InsufficientFundsError as e:  # Более специфичное исключение первым
        logger.warning(f"Insufficient funds for user {current_user.id}: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=e.message
        )
    except BusinessLogicError as e:  # Более общее исключение вторым
        logger.warning(f"Business logic error creating order: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create order"
        )


@router.get("/", response_model=List[OrderResponse])
async def get_my_orders(
        skip: int = Query(0, ge=0, description="Number of orders to skip"),
        limit: int = Query(20, ge=1, le=100, description="Number of orders to return"),
        current_user: User = Depends(get_current_user_from_token),
        db: AsyncSession = Depends(get_db)
):
    """
    Получение списка заказов текущего пользователя

    - Возвращает заказы в порядке убывания даты создания
    - Поддерживает пагинацию
    - Включает информацию о товарах в заказе
    """
    try:
        orders = await order_service.get_user_orders(
            db,
            user=current_user,
            skip=skip,
            limit=limit
        )

        logger.info(f"Retrieved {len(orders)} orders for user {current_user.id}")
        return orders

    except Exception as e:
        logger.error(f"Error getting orders for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get orders"
        )


@router.get("/summary")
async def get_orders_summary(
        current_user: User = Depends(get_current_user_from_token),
        db: AsyncSession = Depends(get_db)
):
    """
    Получение сводки по заказам пользователя

    Возвращает статистику:
    - Общее количество заказов
    - Количество по статусам
    - Общая сумма потраченных средств
    - Последние заказы
    """
    try:
        summary = await order_service.get_order_summary(db, user=current_user)

        return {
            "user_id": current_user.id,
            "summary": summary
        }

    except Exception as e:
        logger.error(f"Error getting order summary for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get order summary"
        )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
        order_id: int,
        current_user: User = Depends(get_current_user_from_token),
        db: AsyncSession = Depends(get_db)
):
    """
    Получение детальной информации о заказе

    - **order_id**: ID заказа
    - Возвращает полную информацию о заказе включая товары
    - Доступ только к собственным заказам
    """
    try:
        order = await order_service.get_order_by_id(db, order_id, current_user)

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )

        return order

    except HTTPException:  # Пропускаем HTTPException без обработки
        raise
    except BusinessLogicError as e:
        logger.warning(f"Access denied to order {order_id} for user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message
        )
    except Exception as e:
        logger.error(f"Error getting order {order_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get order"
        )


@router.get("/number/{order_number}", response_model=OrderResponse)
async def get_order_by_number(
        order_number: str,
        current_user: User = Depends(get_current_user_from_token),
        db: AsyncSession = Depends(get_db)
):
    """
    Получение заказа по номеру

    - **order_number**: Номер заказа (например: ORD-20250128-A1B2C3D4)
    - Альтернативный способ получения заказа
    """
    try:
        order = await order_service.get_order_by_number(db, order_number, current_user)

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )

        return order

    except HTTPException:
        raise
    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message
        )
    except Exception as e:
        logger.error(f"Error getting order by number {order_number}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get order"
        )


@router.put("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
        order_id: int,
        status_update: OrderStatusUpdate,
        current_user: User = Depends(get_current_user_from_token),
        db: AsyncSession = Depends(get_db)
):
    """
    Обновление статуса заказа

    - **order_id**: ID заказа
    - **status**: Новый статус заказа
    - Проверяет возможность перехода между статусами
    """
    try:
        updated_order = await order_service.update_order_status(
            db,
            order_id,
            status_update.status,
            current_user
        )

        logger.info(f"Order {order_id} status updated to {status_update.status}")
        return updated_order

    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except Exception as e:
        logger.error(f"Error updating order {order_id} status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update order status"
        )


@router.post("/{order_id}/cancel", response_model=MessageResponse)
async def cancel_order(
        order_id: int,
        reason: Optional[str] = None,
        current_user: User = Depends(get_current_user_from_token),
        db: AsyncSession = Depends(get_db)
):
    """
    Отмена заказа

    - **order_id**: ID заказа для отмены
    - **reason**: Причина отмены (опционально)
    - Возвращает товары на склад
    - Возвращает средства на баланс (если заказ был оплачен)
    """
    try:
        await order_service.cancel_order(
            db,
            order_id,
            current_user,
            reason
        )

        logger.info(f"Order {order_id} cancelled by user {current_user.id}")
        return MessageResponse(message="Order cancelled successfully")

    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except Exception as e:
        logger.error(f"Error cancelling order {order_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel order"
        )


@router.get("/public/{order_number}", response_model=OrderPublic)
async def get_public_order_info(
        order_number: str,
        db: AsyncSession = Depends(get_db)
):
    """
    Получение публичной информации о заказе

    - Доступно без авторизации
    - Возвращает только базовую информацию (номер, статус, сумма)
    - Используется для отслеживания заказов
    """
    try:
        order = await order_service.crud.get_by_order_number(db, order_number=order_number)

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )

        # Возвращаем только публичную информацию
        return OrderPublic(
            order_number=order.order_number,
            status=order.status,
            total_amount=order.total_amount,
            currency=order.currency,
            created_at=order.created_at,
            expires_at=order.expires_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting public order info for {order_number}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get order information"
        )
