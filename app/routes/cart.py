from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.db import get_db
from app.core.dependencies import get_current_user_or_create_guest, get_current_registered_user
from app.services.cart_service import cart_service
from app.schemas.cart import CartItemResponse, CartItemCreate, CartItemUpdate, CartResponse
from app.schemas.base import MessageResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cart", tags=["Cart"])

@router.get("/", response_model=CartResponse)
async def get_cart(
    current_user = Depends(get_current_user_or_create_guest),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение текущей корзины пользователя
    
    Поддерживает как зарегистрированных пользователей, так и гостей.
    Для гостей корзина привязывается к session_id.
    """
    try:
        user_id = current_user.id if not current_user.is_guest else None
        session_id = current_user.guest_session_id if current_user.is_guest else None
        
        # Получаем элементы корзины
        cart_items = await cart_service.get_user_cart(db, user_id=user_id, session_id=session_id)
        
        # Рассчитываем итоги
        summary = await cart_service.calculate_cart_total(db, user_id=user_id, session_id=session_id)
        
        logger.info(f"Cart retrieved for user {user_id or session_id}: {len(cart_items)} items")
        
        return CartResponse(cart_items=cart_items, summary=summary)
        
    except Exception as e:
        logger.error(f"Error getting cart: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get cart"
        )

@router.post("/items", response_model=CartItemResponse, status_code=status.HTTP_201_CREATED)
async def add_to_cart(
    item: CartItemCreate,
    current_user = Depends(get_current_user_or_create_guest),
    db: AsyncSession = Depends(get_db)
):
    """
    Добавление товара в корзину
    
    - **proxy_product_id**: ID продукта для добавления
    - **quantity**: Количество (должно быть в пределах min/max для продукта)
    - **generation_params**: Дополнительные параметры генерации (JSON)
    """
    try:
        # Устанавливаем идентификатор пользователя
        if current_user.is_guest:
            item.session_id = current_user.guest_session_id
            item.user_id = None
        else:
            item.user_id = current_user.id
            item.session_id = None
        
        # Добавляем в корзину
        cart_item = await cart_service.create(db, obj_in=item)
        
        logger.info(f"Item added to cart: product {item.proxy_product_id}, quantity {item.quantity}")
        
        return cart_item
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding to cart: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add item to cart"
        )

@router.put("/items/{item_id}", response_model=CartItemResponse)
async def update_cart_item(
    item_id: int,
    item_update: CartItemUpdate,
    current_user = Depends(get_current_user_or_create_guest),
    db: AsyncSession = Depends(get_db)
):
    """
    Обновление элемента корзины
    
    - **item_id**: ID элемента корзины
    - **quantity**: Новое количество
    - **generation_params**: Обновленные параметры генерации
    """
    try:
        user_id = current_user.id if not current_user.is_guest else None
        session_id = current_user.guest_session_id if current_user.is_guest else None
        
        # Обновляем количество
        updated_item = await cart_service.update_cart_item(
            db, item_id, item_update.quantity, user_id, session_id
        )
        
        # Обновляем параметры генерации если указаны
        if item_update.generation_params is not None:
            updated_item.generation_params = item_update.generation_params
            await db.commit()
            await db.refresh(updated_item)
        
        logger.info(f"Cart item {item_id} updated: quantity {item_update.quantity}")
        
        return updated_item
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating cart item {item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update cart item"
        )

@router.delete("/items/{item_id}", response_model=MessageResponse)
async def delete_cart_item(
    item_id: int,
    current_user = Depends(get_current_user_or_create_guest),
    db: AsyncSession = Depends(get_db)
):
    """
    Удаление товара из корзины
    
    - **item_id**: ID элемента корзины для удаления
    """
    try:
        user_id = current_user.id if not current_user.is_guest else None
        session_id = current_user.guest_session_id if current_user.is_guest else None
        
        success = await cart_service.remove_cart_item(db, item_id, user_id, session_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart item not found"
            )
        
        logger.info(f"Cart item {item_id} removed")
        
        return MessageResponse(message="Item removed from cart")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing cart item {item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove cart item"
        )

@router.delete("/", response_model=MessageResponse)
async def clear_cart(
    current_user = Depends(get_current_user_or_create_guest),
    db: AsyncSession = Depends(get_db)
):
    """
    Очистка всей корзины
    
    Удаляет все элементы из корзины текущего пользователя.
    """
    try:
        user_id = current_user.id if not current_user.is_guest else None
        session_id = current_user.guest_session_id if current_user.is_guest else None
        
        success = await cart_service.clear_cart(db, user_id, session_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to clear cart"
            )
        
        logger.info(f"Cart cleared for user {user_id or session_id}")
        
        return MessageResponse(message="Cart cleared successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing cart: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear cart"
        )

@router.get("/summary")
async def get_cart_summary(
    current_user = Depends(get_current_user_or_create_guest),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение краткой сводки по корзине
    
    Возвращает только итоговую информацию без деталей товаров.
    """
    try:
        user_id = current_user.id if not current_user.is_guest else None
        session_id = current_user.guest_session_id if current_user.is_guest else None
        
        summary = await cart_service.calculate_cart_total(db, user_id=user_id, session_id=session_id)
        
        return {
            "total_items": summary["total_items"],
            "total_amount": summary["total_amount"],
            "currency": summary["currency"],
            "user_type": "guest" if current_user.is_guest else "registered"
        }
        
    except Exception as e:
        logger.error(f"Error getting cart summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get cart summary"
        )
