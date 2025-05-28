import logging
from decimal import Decimal
from typing import List, Optional, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessLogicError, ProductNotAvailableError
from app.crud.proxy_product import proxy_product_crud
from app.crud.shopping_cart import shopping_cart_crud
from app.models.models import ShoppingCart
from app.schemas.cart import CartCreate, CartUpdate
from app.services.base import BaseService, BusinessRuleValidator

logger = logging.getLogger(__name__)


class CartBusinessRules(BusinessRuleValidator):
    """Валидатор бизнес-правил для корзины"""

    async def validate(self, data: dict, db: AsyncSession) -> bool:
        """Валидация правил корзины"""
        product_id = data.get('product_id')
        quantity = data.get('quantity', 1)

        # Проверяем существование продукта
        product = await proxy_product_crud.get(db, obj_id=product_id)  # Исправлено
        if not product:
            raise BusinessLogicError("Product not found")

        if not product.is_active:
            raise ProductNotAvailableError("Product is not available")

        # Проверяем количество
        if quantity < product.min_quantity:
            raise BusinessLogicError(f"Minimum quantity is {product.min_quantity}")

        if quantity > product.max_quantity:
            raise BusinessLogicError(f"Maximum quantity is {product.max_quantity}")

        if quantity > product.stock_available:
            raise ProductNotAvailableError(f"Only {product.stock_available} items available")

        return True


class CartService(BaseService[ShoppingCart, CartCreate, CartUpdate]):
    """Сервис для работы с корзиной"""

    def __init__(self):
        super().__init__(ShoppingCart)
        self.crud = shopping_cart_crud
        self.product_crud = proxy_product_crud
        self.business_rules = CartBusinessRules()

    async def create(self, db: AsyncSession, obj_in: CartCreate) -> ShoppingCart:
        """Создание элемента корзины"""
        # Валидация бизнес-правил
        await self.business_rules.validate({
            'product_id': obj_in.proxy_product_id,  # Исправлено: правильное поле
            'quantity': obj_in.quantity
        }, db)

        # Проверяем, есть ли уже такой товар в корзине
        existing_item = await self.crud.get_cart_item(
            db,
            user_id=obj_in.user_id,
            session_id=obj_in.session_id,
            product_id=obj_in.proxy_product_id
        )

        if existing_item:
            # Обновляем количество
            new_quantity = existing_item.quantity + obj_in.quantity
            await self.business_rules.validate({
                'product_id': obj_in.proxy_product_id,
                'quantity': new_quantity
            }, db)

            return await self.crud.update(
                db,
                db_obj=existing_item,
                obj_in={'quantity': new_quantity}
            )

        # Создаем новый элемент
        return await self.crud.create(db, obj_in=obj_in)

    async def get_user_cart(
            self,
            db: AsyncSession,
            user_id: Optional[int] = None,
            session_id: Optional[str] = None
    ) -> List[ShoppingCart]:
        """Получение корзины пользователя"""
        return await self.crud.get_user_cart(db, user_id=user_id, session_id=session_id)

    async def calculate_cart_total(
            self,
            db: AsyncSession,
            user_id: Optional[int] = None,
            session_id: Optional[str] = None
    ) -> Dict:
        """Расчет итогов корзины"""
        cart_items = await self.get_user_cart(db, user_id, session_id)

        total_amount = Decimal('0.00')
        total_items = 0
        items_details = []

        for item in cart_items:
            product = await self.product_crud.get(db, obj_id=item.proxy_product_id)  # Исправлено
            if product and product.is_active:
                item_total = product.price_per_proxy * item.quantity
                total_amount += item_total
                total_items += item.quantity

                items_details.append({
                    'cart_item_id': item.id,
                    'product_id': product.id,
                    'product_name': product.name,
                    'quantity': item.quantity,
                    'unit_price': product.price_per_proxy,
                    'total_price': item_total
                })

        return {
            'items': items_details,
            'total_items': total_items,
            'total_amount': total_amount,
            'currency': 'USD'
        }

    async def update_cart_item(
            self,
            db: AsyncSession,
            cart_item_id: int,
            quantity: int,
            user_id: Optional[int] = None,
            session_id: Optional[str] = None
    ) -> ShoppingCart:
        """Обновление элемента корзины"""

        # Получаем элемент корзины
        cart_item = await self.crud.get_user_cart_item(
            db, cart_item_id, user_id, session_id
        )

        if not cart_item:
            raise BusinessLogicError("Cart item not found")

        # Валидируем новое количество
        await self.business_rules.validate({
            'product_id': cart_item.proxy_product_id,
            'quantity': quantity
        }, db)

        # Обновляем
        return await self.crud.update(
            db,
            db_obj=cart_item,
            obj_in={'quantity': quantity}
        )

    async def remove_cart_item(
            self,
            db: AsyncSession,
            cart_item_id: int,
            user_id: Optional[int] = None,
            session_id: Optional[str] = None
    ) -> bool:
        """Удаление элемента из корзины"""

        cart_item = await self.crud.get_user_cart_item(
            db, cart_item_id, user_id, session_id
        )

        if not cart_item:
            return False

        await self.crud.remove(db, obj_id=cart_item_id)  # Исправлено
        return True

    async def clear_cart(
            self,
            db: AsyncSession,
            user_id: Optional[int] = None,
            session_id: Optional[str] = None
    ) -> bool:
        """Очистка корзины"""
        return await self.crud.clear_user_cart(db, user_id, session_id)

    async def get(self, db: AsyncSession, obj_id: int) -> Optional[ShoppingCart]:  # Исправлено
        """Получение элемента корзины по ID"""
        return await self.crud.get(db, obj_id=obj_id)

    async def update(self, db: AsyncSession, db_obj: ShoppingCart, obj_in: CartUpdate) -> ShoppingCart:
        """Обновление элемента корзины"""
        return await self.crud.update(db, db_obj=db_obj, obj_in=obj_in)

    async def delete(self, db: AsyncSession, obj_id: int) -> bool:  # Исправлено
        """Удаление элемента корзины"""
        await self.crud.remove(db, obj_id=obj_id)
        return True

    async def get_multi(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[ShoppingCart]:
        """Получение списка элементов корзины"""
        return await self.crud.get_multi(db, skip=skip, limit=limit)


# Создаем экземпляр сервиса
cart_service = CartService()
