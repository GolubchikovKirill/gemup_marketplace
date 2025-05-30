import logging
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessLogicError
from app.crud.proxy_product import proxy_product_crud
from app.crud.shopping_cart import shopping_cart_crud
from app.models.models import ShoppingCart, User
from app.services.base import BaseService, BusinessRuleValidator

logger = logging.getLogger(__name__)


class CartBusinessRules(BusinessRuleValidator):
    """Валидатор бизнес-правил для корзины"""

    async def validate(self, data: dict, db: AsyncSession) -> bool:
        """Валидация правил корзины"""
        # ИСПРАВЛЕНО: правильное поле
        product_id = data.get('proxy_product_id')  # Было 'product_id'
        quantity = data.get('quantity', 1)

        # Проверяем существование продукта
        product = await proxy_product_crud.get(db, obj_id=product_id)
        if not product:
            raise BusinessLogicError("Product not found")

        # Проверяем активность продукта
        if not product.is_active:
            raise BusinessLogicError("Product is not active")

        # Проверяем наличие на складе
        if product.stock_available < quantity:
            raise BusinessLogicError("Insufficient stock")

        # Проверяем минимальное и максимальное количество
        if quantity < product.min_quantity:
            raise BusinessLogicError(f"Minimum quantity is {product.min_quantity}")

        if quantity > product.max_quantity:
            raise BusinessLogicError(f"Maximum quantity is {product.max_quantity}")

        return True


class CartService(BaseService[ShoppingCart, dict, dict]):
    """Сервис для работы с корзиной"""

    def __init__(self):
        super().__init__(ShoppingCart)
        self.crud = shopping_cart_crud
        self.business_rules = CartBusinessRules()

    async def add_item_to_cart(
            self,
            db: AsyncSession,
            user: User,
            proxy_product_id: int,
            quantity: int = 1,
            generation_params: Optional[str] = None
    ) -> ShoppingCart:
        """Добавление товара в корзину"""
        try:
            # Валидируем бизнес-правила
            await self.business_rules.validate({
                'proxy_product_id': proxy_product_id,
                'quantity': quantity
            }, db)

            # Добавляем товар в корзину
            cart_item = await self.crud.add_item(
                db,
                user_id=user.id if not user.is_guest else None,
                session_id=user.guest_session_id if user.is_guest else None,
                proxy_product_id=proxy_product_id,
                quantity=quantity,
                generation_params=generation_params
            )

            logger.info(f"Item added to cart: product {proxy_product_id}, quantity {quantity}")
            return cart_item

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error adding item to cart: {e}")
            raise BusinessLogicError(f"Failed to add item to cart: {str(e)}")

    # Реализация абстрактных методов BaseService
    async def create(self, db: AsyncSession, obj_in: dict) -> ShoppingCart:
        return await self.crud.create(db, obj_in=obj_in)

    async def get(self, db: AsyncSession, obj_id: int) -> Optional[ShoppingCart]:
        return await self.crud.get(db, obj_id=obj_id)

    async def update(self, db: AsyncSession, db_obj: ShoppingCart, obj_in: dict) -> ShoppingCart:
        return await self.crud.update(db, db_obj=db_obj, obj_in=obj_in)

    async def delete(self, db: AsyncSession, obj_id: int) -> bool:
        await self.crud.remove(db, obj_id=obj_id)
        return True

    async def get_multi(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[ShoppingCart]:
        return await self.crud.get_multi(db, skip=skip, limit=limit)


cart_service = CartService()
