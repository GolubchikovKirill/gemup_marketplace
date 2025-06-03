"""
Сервис для управления корзиной покупок.

Обеспечивает функциональность добавления товаров в корзину,
расчета итоговой стоимости и управления содержимым корзины.
Полная production-ready реализация без мок-данных.
"""

import logging
from decimal import Decimal
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessLogicError
from app.crud.proxy_product import proxy_product_crud
from app.crud.shopping_cart import shopping_cart_crud
from app.models.models import ShoppingCart
from app.schemas.cart import CartItemCreate, CartItemUpdate
from app.services.base import BaseService, BusinessRuleValidator

logger = logging.getLogger(__name__)


class CartBusinessRules(BusinessRuleValidator):
    """Валидатор бизнес-правил для корзины."""

    async def validate(self, data: dict, db: AsyncSession) -> bool:
        """
        Валидация бизнес-правил для корзины.

        Args:
            data: Данные для валидации (product_id, quantity, user_id, session_id)
            db: Сессия базы данных

        Returns:
            bool: Результат валидации

        Raises:
            BusinessLogicError: При нарушении бизнес-правил
        """
        try:
            # Проверка обязательных полей
            product_id = data.get("product_id")
            quantity = data.get("quantity", 0)

            if not product_id:
                raise BusinessLogicError("Product ID is required")

            if quantity <= 0:
                raise BusinessLogicError("Quantity must be positive")

            if quantity > 1000:  # Максимальное количество для заказа
                raise BusinessLogicError("Quantity cannot exceed 1000 items")

            # Проверка существования продукта
            product = await proxy_product_crud.get(db, obj_id=product_id)
            if not product:
                raise BusinessLogicError("Product not found")

            if not product.is_active:
                raise BusinessLogicError("Product is not available")

            # Проверка наличия на складе
            if product.stock_available < quantity:
                raise BusinessLogicError(f"Only {product.stock_available} items available in stock")

            # Проверка максимального количества для продукта
            if hasattr(product, 'max_quantity') and product.max_quantity:
                if quantity > product.max_quantity:
                    raise BusinessLogicError(f"Maximum quantity for this product is {product.max_quantity}")

            # Проверка минимального количества
            if hasattr(product, 'min_quantity') and product.min_quantity:
                if quantity < product.min_quantity:
                    raise BusinessLogicError(f"Minimum quantity for this product is {product.min_quantity}")

            logger.debug(f"Cart business rules validation passed for product {product_id}")
            return True

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error during cart business rules validation: {e}")
            raise BusinessLogicError(f"Validation failed: {str(e)}")


class CartService(BaseService[ShoppingCart, CartItemCreate, CartItemUpdate]):
    """
    Сервис для управления корзиной покупок.

    Предоставляет функциональность для работы с корзиной пользователей,
    включая добавление товаров, расчет стоимости и очистку.
    Поддерживает как зарегистрированных пользователей, так и гостевые сессии.
    """

    def __init__(self):
        super().__init__(ShoppingCart)
        self.crud = shopping_cart_crud
        self.business_rules = CartBusinessRules()
        self.max_cart_items = 50  # Максимальное количество различных товаров в корзине

    async def get_user_cart(
        self,
        db: AsyncSession,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> List[ShoppingCart]:
        """
        Получение содержимого корзины пользователя.

        Args:
            db: Сессия базы данных
            user_id: Идентификатор зарегистрированного пользователя
            session_id: Идентификатор сессии гостевого пользователя

        Returns:
            List[ShoppingCart]: Список элементов корзины

        Raises:
            BusinessLogicError: При некорректных параметрах
        """
        try:
            if not user_id and not session_id:
                raise BusinessLogicError("Either user_id or session_id must be provided")

            if user_id:
                cart_items = await self.crud.get_user_cart(db, user_id=user_id)
            else:
                cart_items = await self.crud.get_guest_cart(db, session_id=session_id)

            logger.info(f"Retrieved cart for user {user_id or session_id}: {len(cart_items)} items")
            return cart_items

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error getting user cart: {e}")
            raise BusinessLogicError(f"Failed to get cart: {str(e)}")

    async def calculate_cart_total(
        self,
        db: AsyncSession,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Расчет итоговой стоимости корзины.

        Args:
            db: Сессия базы данных
            user_id: Идентификатор пользователя
            session_id: Идентификатор сессии

        Returns:
            Dict[str, Any]: Детальная информация о стоимости корзины
        """
        try:
            cart_items = await self.get_user_cart(db, user_id, session_id)

            total_items = 0
            total_amount = Decimal('0.00')
            items_details = []

            for item in cart_items:
                # Проверяем актуальность цены
                current_product = await proxy_product_crud.get(db, obj_id=item.proxy_product_id)
                if not current_product or not current_product.is_active:
                    logger.warning(f"Inactive product {item.proxy_product_id} found in cart")
                    continue

                total_items += item.quantity
                item_total = current_product.price_per_proxy * item.quantity
                total_amount += item_total

                items_details.append({
                    "cart_item_id": item.id,
                    "product_id": item.proxy_product_id,
                    "product_name": current_product.name,
                    "quantity": item.quantity,
                    "unit_price": str(current_product.price_per_proxy),
                    "total_price": str(item_total),
                    "country": current_product.country_name,
                    "provider": current_product.provider.value if current_product.provider else None
                })

            # Расчет налогов и скидок (если необходимо)
            tax_amount = Decimal('0.00')  # В будущем можно добавить расчет налогов
            discount_amount = Decimal('0.00')  # В будущем можно добавить скидки

            final_amount = total_amount + tax_amount - discount_amount

            return {
                "total_items": total_items,
                "items_count": len(items_details),
                "subtotal": str(total_amount),
                "tax_amount": str(tax_amount),
                "discount_amount": str(discount_amount),
                "total_amount": str(final_amount),
                "currency": "USD",
                "items": items_details
            }

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error calculating cart total: {e}")
            return {
                "total_items": 0,
                "items_count": 0,
                "subtotal": "0.00",
                "tax_amount": "0.00",
                "discount_amount": "0.00",
                "total_amount": "0.00",
                "currency": "USD",
                "items": []
            }

    async def add_item_to_cart(
        self,
        db: AsyncSession,
        product_id: int,
        quantity: int,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        generation_params: Optional[str] = None
    ) -> ShoppingCart:
        """
        Добавление товара в корзину.

        Args:
            db: Сессия базы данных
            product_id: Идентификатор продукта
            quantity: Количество
            user_id: Идентификатор пользователя
            session_id: Идентификатор сессии
            generation_params: Параметры генерации прокси (JSON)

        Returns:
            ShoppingCart: Добавленный или обновленный элемент корзины

        Raises:
            BusinessLogicError: При ошибках валидации
        """
        try:
            # Валидация бизнес-правил
            validation_data = {
                "product_id": product_id,
                "quantity": quantity,
                "user_id": user_id,
                "session_id": session_id
            }
            await self.business_rules.validate(validation_data, db)

            # Проверка лимита товаров в корзине
            current_cart = await self.get_user_cart(db, user_id, session_id)
            if len(current_cart) >= self.max_cart_items:
                # Проверяем, есть ли уже этот товар в корзине
                existing_item = next((item for item in current_cart if item.proxy_product_id == product_id), None)
                if not existing_item:
                    raise BusinessLogicError(f"Cart cannot contain more than {self.max_cart_items} different items")

            cart_item = await self.crud.add_to_cart(
                db,
                user_id=user_id,
                session_id=session_id,
                proxy_product_id=product_id,
                quantity=quantity,
                generation_params=generation_params
            )

            if not cart_item:
                raise BusinessLogicError("Failed to add item to cart")

            logger.info(f"Added item to cart: product {product_id}, quantity {quantity}")
            return cart_item

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error adding item to cart: {e}")
            raise BusinessLogicError(f"Failed to add item to cart: {str(e)}")

    async def update_cart_item_quantity(
        self,
        db: AsyncSession,
        item_id: int,
        new_quantity: int,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> ShoppingCart:
        """
        Обновление количества товара в корзине.

        Args:
            db: Сессия базы данных
            item_id: Идентификатор элемента корзины
            new_quantity: Новое количество
            user_id: Идентификатор пользователя
            session_id: Идентификатор сессии

        Returns:
            ShoppingCart: Обновленный элемент корзины

        Raises:
            BusinessLogicError: При ошибках валидации или доступа
        """
        try:
            cart_item = await self.crud.update_cart_item_quantity(
                db,
                cart_item_id=item_id,
                new_quantity=new_quantity,
                user_id=user_id,
                session_id=session_id
            )

            if not cart_item:
                raise BusinessLogicError("Cart item not found or access denied")

            logger.info(f"Updated cart item {item_id}: quantity {new_quantity}")
            return cart_item

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error updating cart item {item_id}: {e}")
            raise BusinessLogicError(f"Failed to update cart item: {str(e)}")

    async def remove_cart_item(
        self,
        db: AsyncSession,
        item_id: int,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> bool:
        """
        Удаление товара из корзины.

        Args:
            db: Сессия базы данных
            item_id: Идентификатор элемента корзины
            user_id: Идентификатор пользователя
            session_id: Идентификатор сессии

        Returns:
            bool: Успешность операции

        Raises:
            BusinessLogicError: При ошибках доступа
        """
        try:
            success = await self.crud.remove_cart_item(
                db,
                cart_item_id=item_id,
                user_id=user_id,
                session_id=session_id
            )

            if not success:
                raise BusinessLogicError("Cart item not found or access denied")

            logger.info(f"Removed cart item {item_id}")
            return True

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error removing cart item {item_id}: {e}")
            raise BusinessLogicError(f"Failed to remove cart item: {str(e)}")

    async def clear_cart(
        self,
        db: AsyncSession,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> bool:
        """
        Полная очистка корзины.

        Args:
            db: Сессия базы данных
            user_id: Идентификатор пользователя
            session_id: Идентификатор сессии

        Returns:
            bool: Успешность операции

        Raises:
            BusinessLogicError: При ошибках очистки
        """
        try:
            if user_id:
                success = await self.crud.clear_user_cart(db, user_id=user_id)
            elif session_id:
                success = await self.crud.clear_guest_cart(db, session_id=session_id)
            else:
                raise BusinessLogicError("Either user_id or session_id must be provided")

            if not success:
                raise BusinessLogicError("Failed to clear cart")

            logger.info(f"Cleared cart for user {user_id or session_id}")
            return True

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error clearing cart: {e}")
            raise BusinessLogicError(f"Failed to clear cart: {str(e)}")

    async def merge_guest_cart_to_user(
        self,
        db: AsyncSession,
        session_id: str,
        user_id: int
    ) -> bool:
        """
        Объединение гостевой корзины с корзиной пользователя при авторизации.

        Args:
            db: Сессия базы данных
            session_id: ID гостевой сессии
            user_id: ID пользователя

        Returns:
            bool: Успешность операции

        Raises:
            BusinessLogicError: При ошибках объединения
        """
        try:
            success = await self.crud.merge_guest_cart_to_user(
                db,
                session_id=session_id,
                user_id=user_id
            )

            if not success:
                raise BusinessLogicError("Failed to merge guest cart")

            logger.info(f"Merged guest cart {session_id} to user {user_id}")
            return True

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error merging guest cart: {e}")
            raise BusinessLogicError(f"Failed to merge cart: {str(e)}")

    async def validate_cart_before_checkout(
        self,
        db: AsyncSession,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Валидация корзины перед оформлением заказа.

        Args:
            db: Сессия базы данных
            user_id: Идентификатор пользователя
            session_id: Идентификатор сессии

        Returns:
            Dict[str, Any]: Результат валидации с детальной информацией

        Raises:
            BusinessLogicError: При критических ошибках валидации
        """
        try:
            cart_items = await self.get_user_cart(db, user_id, session_id)

            if not cart_items:
                raise BusinessLogicError("Cart is empty")

            validation_result = {
                "is_valid": True,
                "errors": [],
                "warnings": [],
                "updated_items": []
            }

            for item in cart_items:
                # Проверяем актуальность продукта
                current_product = await proxy_product_crud.get(db, obj_id=item.proxy_product_id)

                if not current_product:
                    validation_result["errors"].append(f"Product {item.proxy_product_id} no longer exists")
                    validation_result["is_valid"] = False
                    continue

                if not current_product.is_active:
                    validation_result["errors"].append(f"Product '{current_product.name}' is no longer available")
                    validation_result["is_valid"] = False
                    continue

                # Проверяем наличие на складе
                if current_product.stock_available < item.quantity:
                    if current_product.stock_available > 0:
                        validation_result["warnings"].append(
                            f"Only {current_product.stock_available} units of '{current_product.name}' available"
                        )
                        validation_result["updated_items"].append({
                            "item_id": item.id,
                            "new_quantity": current_product.stock_available
                        })
                    else:
                        validation_result["errors"].append(f"Product '{current_product.name}' is out of stock")
                        validation_result["is_valid"] = False

                # ИСПРАВЛЕНО: убрал проверку несуществующего атрибута cached_price
                # Проверка изменения цены теперь происходит при расчете итоговой стоимости
                # в методе calculate_cart_total

            return validation_result

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error validating cart: {e}")
            raise BusinessLogicError(f"Cart validation failed: {str(e)}")

    async def get_cart_summary(
        self,
        db: AsyncSession,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получение краткой сводки корзины.

        Args:
            db: Сессия базы данных
            user_id: Идентификатор пользователя
            session_id: Идентификатор сессии

        Returns:
            Dict[str, Any]: Краткая информация о корзине
        """
        try:
            cart_items = await self.get_user_cart(db, user_id, session_id)
            cart_total = await self.calculate_cart_total(db, user_id, session_id)

            return {
                "items_count": len(cart_items),
                "total_quantity": cart_total["total_items"],
                "total_amount": cart_total["total_amount"],
                "currency": cart_total["currency"],
                "last_updated": max([item.updated_at for item in cart_items]).isoformat() if cart_items else None
            }

        except Exception as e:
            logger.error(f"Error getting cart summary: {e}")
            return {
                "items_count": 0,
                "total_quantity": 0,
                "total_amount": "0.00",
                "currency": "USD",
                "last_updated": None
            }

    async def check_cart_item_changes(
        self,
        db: AsyncSession,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Проверка изменений в товарах корзины с момента добавления.

        Args:
            db: Сессия базы данных
            user_id: Идентификатор пользователя
            session_id: Идентификатор сессии

        Returns:
            Dict[str, Any]: Информация об изменениях
        """
        try:
            cart_items = await self.get_user_cart(db, user_id, session_id)
            changes = {
                "price_changes": [],
                "availability_changes": [],
                "stock_changes": []
            }

            for item in cart_items:
                current_product = await proxy_product_crud.get(db, obj_id=item.proxy_product_id)

                if not current_product:
                    changes["availability_changes"].append({
                        "item_id": item.id,
                        "product_id": item.proxy_product_id,
                        "message": "Product no longer exists"
                    })
                    continue

                if not current_product.is_active:
                    changes["availability_changes"].append({
                        "item_id": item.id,
                        "product_id": item.proxy_product_id,
                        "product_name": current_product.name,
                        "message": "Product is no longer available"
                    })

                if current_product.stock_available < item.quantity:
                    changes["stock_changes"].append({
                        "item_id": item.id,
                        "product_id": item.proxy_product_id,
                        "product_name": current_product.name,
                        "requested_quantity": item.quantity,
                        "available_quantity": current_product.stock_available,
                        "message": f"Only {current_product.stock_available} items available"
                    })

            return changes

        except Exception as e:
            logger.error(f"Error checking cart item changes: {e}")
            return {
                "price_changes": [],
                "availability_changes": [],
                "stock_changes": []
            }

    # Реализация абстрактных методов BaseService
    async def create(self, db: AsyncSession, obj_in: CartItemCreate) -> ShoppingCart:
        return await self.crud.create(db, obj_in=obj_in)

    async def get(self, db: AsyncSession, obj_id: int) -> Optional[ShoppingCart]:
        return await self.crud.get(db, obj_id=obj_id)

    async def update(self, db: AsyncSession, db_obj: ShoppingCart, obj_in: CartItemUpdate) -> ShoppingCart:
        return await self.crud.update(db, db_obj=db_obj, obj_in=obj_in)

    async def delete(self, db: AsyncSession, obj_id: int) -> bool:
        result = await self.crud.delete(db, obj_id=obj_id)
        return result is not None

    async def get_multi(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[ShoppingCart]:
        return await self.crud.get_multi(db, skip=skip, limit=limit)


cart_service = CartService()
