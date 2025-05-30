import logging
from typing import List, Optional, Dict, Any
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.shopping_cart import shopping_cart_crud
from app.models.models import ShoppingCart
from app.schemas.cart import CartItemCreate, CartItemUpdate
from app.services.base import BaseService, BusinessRuleValidator

logger = logging.getLogger(__name__)


class CartBusinessRules(BusinessRuleValidator):
    """Валидатор бизнес-правил для корзины"""

    async def validate(self, data: dict, db: AsyncSession) -> bool:
        """Валидация правил корзины"""
        return True


class CartService(BaseService[ShoppingCart, CartItemCreate, CartItemUpdate]):
    """Сервис для работы с корзиной"""

    def __init__(self):
        super().__init__(ShoppingCart)
        self.crud = shopping_cart_crud
        self.business_rules = CartBusinessRules()

    async def get_user_cart(
            self,
            db: AsyncSession,
            user_id: Optional[int] = None,
            session_id: Optional[str] = None
    ) -> List[ShoppingCart]:
        """Получение корзины пользователя"""
        try:
            if user_id:
                cart_items = await self.crud.get_user_cart(db, user_id=user_id)
            elif session_id:
                cart_items = await self.crud.get_guest_cart(db, session_id=session_id)
            else:
                return []

            logger.info(f"Retrieved cart for user {user_id or session_id}: {len(cart_items)} items")
            return cart_items
        except Exception as e:
            logger.error(f"Error getting user cart: {e}")
            return []

    async def calculate_cart_total(
            self,
            db: AsyncSession,
            user_id: Optional[int] = None,
            session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Расчет итогов корзины"""
        try:
            cart_items = await self.get_user_cart(db, user_id, session_id)

            total_items = 0
            total_amount = Decimal('0.00')
            items_details = []

            for item in cart_items:
                total_items += item.quantity
                item_total = item.proxy_product.price_per_proxy * item.quantity
                total_amount += item_total

                items_details.append({
                    "product_id": item.proxy_product_id,
                    "product_name": item.proxy_product.name,
                    "quantity": item.quantity,
                    "unit_price": str(item.proxy_product.price_per_proxy),
                    "total_price": str(item_total)
                })

            return {
                "total_items": total_items,
                "total_amount": str(total_amount),
                "currency": "USD",
                "items_count": len(cart_items),
                "items": items_details
            }
        except Exception as e:
            logger.error(f"Error calculating cart total: {e}")
            return {
                "total_items": 0,
                "total_amount": "0.00",
                "currency": "USD",
                "items_count": 0,
                "items": []
            }

    async def update_cart_item(
            self,
            db: AsyncSession,
            item_id: int,
            quantity: int,
            user_id: Optional[int] = None,
            session_id: Optional[str] = None
    ) -> Optional[ShoppingCart]:
        """Обновление элемента корзины"""
        try:
            item = await self.crud.get(db, obj_id=item_id)
            if not item:
                return None

            # Проверяем права доступа
            if user_id and item.user_id != user_id:
                return None
            if session_id and item.session_id != session_id:
                return None

            # Обновляем количество
            item.quantity = quantity
            await db.commit()
            await db.refresh(item)

            logger.info(f"Updated cart item {item_id}: quantity {quantity}")
            return item
        except Exception as e:
            logger.error(f"Error updating cart item {item_id}: {e}")
            return None

    async def remove_cart_item(
            self,
            db: AsyncSession,
            item_id: int,
            user_id: Optional[int] = None,
            session_id: Optional[str] = None
    ) -> bool:
        """Удаление элемента корзины"""
        try:
            item = await self.crud.get(db, obj_id=item_id)
            if not item:
                return False

            # Проверяем права доступа
            if user_id and item.user_id != user_id:
                return False
            if session_id and item.session_id != session_id:
                return False

            # Удаляем элемент
            await self.crud.remove(db, obj_id=item_id)

            logger.info(f"Removed cart item {item_id}")
            return True
        except Exception as e:
            logger.error(f"Error removing cart item {item_id}: {e}")
            return False

    async def clear_cart(
            self,
            db: AsyncSession,
            user_id: Optional[int] = None,
            session_id: Optional[str] = None
    ) -> bool:
        """Очистка корзины"""
        try:
            if user_id:
                success = await self.crud.clear_user_cart(db, user_id=user_id)
            elif session_id:
                success = await self.crud.clear_guest_cart(db, session_id=session_id)
            else:
                return False

            logger.info(f"Cleared cart for user {user_id or session_id}")
            return success
        except Exception as e:
            logger.error(f"Error clearing cart: {e}")
            return False

    # Реализация абстрактных методов BaseService
    async def create(self, db: AsyncSession, obj_in: CartItemCreate) -> ShoppingCart:
        return await self.crud.create(db, obj_in=obj_in)

    async def get(self, db: AsyncSession, obj_id: int) -> Optional[ShoppingCart]:
        return await self.crud.get(db, obj_id=obj_id)

    async def update(self, db: AsyncSession, db_obj: ShoppingCart, obj_in: CartItemUpdate) -> ShoppingCart:
        return await self.crud.update(db, db_obj=db_obj, obj_in=obj_in)

    async def delete(self, db: AsyncSession, obj_id: int) -> bool:
        await self.crud.remove(db, obj_id=obj_id)
        return True

    async def get_multi(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[ShoppingCart]:
        return await self.crud.get_multi(db, skip=skip, limit=limit)


cart_service = CartService()
