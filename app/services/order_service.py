import logging
from decimal import Decimal
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessLogicError, InsufficientFundsError
from app.crud.order import order_crud
from app.crud.proxy_product import proxy_product_crud
from app.crud.shopping_cart import shopping_cart_crud
from app.crud.user import user_crud
from app.models.models import Order, OrderStatus, User
from app.schemas.order import OrderCreate, OrderUpdate
from app.services.base import BaseService, BusinessRuleValidator

logger = logging.getLogger(__name__)


class OrderBusinessRules(BusinessRuleValidator):
    """Валидатор бизнес-правил для заказов"""

    async def validate(self, data: dict, db: AsyncSession) -> bool:
        """Валидация правил заказа"""
        user_id = data.get('user_id')
        cart_items = data.get('cart_items', [])

        if not cart_items:
            raise BusinessLogicError("Cart is empty")

        # Проверяем доступность всех товаров
        total_amount = Decimal('0.00')
        for item in cart_items:
            product = await proxy_product_crud.get(db, obj_id=item.proxy_product_id)
            if not product:
                raise BusinessLogicError(f"Product {item.proxy_product_id} not found")

            if not product.is_active:
                raise BusinessLogicError(f"Product {product.name} is not available")

            if item.quantity > product.stock_available:
                raise BusinessLogicError(
                    f"Only {product.stock_available} items available for {product.name}"
                )

            if item.quantity < product.min_quantity:
                raise BusinessLogicError(
                    f"Minimum quantity for {product.name} is {product.min_quantity}"
                )

            if item.quantity > product.max_quantity:
                raise BusinessLogicError(
                    f"Maximum quantity for {product.name} is {product.max_quantity}"
                )

            total_amount += product.price_per_proxy * item.quantity

        # Проверяем баланс пользователя
        user = await user_crud.get(db, obj_id=user_id)
        if user and not user.is_guest:
            if user.balance < total_amount:
                raise InsufficientFundsError(
                    f"Insufficient balance. Required: {total_amount}, Available: {user.balance}"
                )

        return True


class OrderService(BaseService[Order, OrderCreate, OrderUpdate]):
    """Сервис для работы с заказами"""

    def __init__(self):
        super().__init__(Order)
        self.crud = order_crud  # ИСПРАВЛЕНО: добавляем crud
        self.business_rules = OrderBusinessRules()

    async def create_order_from_cart(
            self,
            db: AsyncSession,
            user: User,
            payment_method: Optional[str] = None,
            notes: Optional[str] = None
    ) -> Order:
        """Создание заказа из корзины пользователя"""

        # Получаем корзину пользователя
        user_id = user.id if not user.is_guest else None
        session_id = user.guest_session_id if user.is_guest else None

        cart_items = await shopping_cart_crud.get_user_cart(
            db, user_id=user_id, session_id=session_id
        )

        if not cart_items:
            raise BusinessLogicError("Cart is empty")

        # Валидируем бизнес-правила
        await self.business_rules.validate({
            'user_id': user.id,
            'cart_items': cart_items
        }, db)

        # Создаем заказ через CRUD
        order = await order_crud.create_order_from_cart(
            db,
            user_id=user.id,
            cart_items=cart_items,
            payment_method=payment_method
        )

        if notes:
            order.notes = notes
            await db.commit()
            await db.refresh(order)

        # Резервируем товары
        await self._reserve_products(db, cart_items)

        # Списываем средства с баланса
        if not user.is_guest and user.balance >= order.total_amount:
            await self._process_payment_from_balance(db, user, order)

        # Очищаем корзину
        await shopping_cart_crud.clear_user_cart(db, user_id, session_id)

        logger.info(f"Order {order.order_number} created for user {user.id}")
        return order

    @staticmethod
    async def _reserve_products(db: AsyncSession, cart_items):
        """Резервирование товаров"""
        for item in cart_items:
            await proxy_product_crud.update_stock(
                db,
                product_id=item.proxy_product_id,
                quantity=item.quantity
            )

    @staticmethod
    async def _process_payment_from_balance(db: AsyncSession, user: User, order: Order):
        """Списание средств с баланса"""
        await user_crud.update_balance(
            db,
            user=user,
            amount=-float(order.total_amount)
        )

        order.status = OrderStatus.PAID
        await db.commit()
        await db.refresh(order)

        logger.info(f"Payment processed from balance for order {order.order_number}")

    @staticmethod
    async def get_user_orders(
            db: AsyncSession,
            user: User,
            skip: int = 0,
            limit: int = 100
    ) -> List[Order]:
        """Получение заказов пользователя"""
        return await order_crud.get_user_orders(
            db,
            user_id=user.id,
            skip=skip,
            limit=limit
        )

    @staticmethod
    async def get_order_by_id(
            db: AsyncSession,
            order_id: int,
            user: User
    ) -> Optional[Order]:
        """Получение заказа по ID"""
        order = await order_crud.get(db, obj_id=order_id)

        if not order:
            return None

        if order.user_id != user.id:
            raise BusinessLogicError("Access denied to this order")

        return order

    @staticmethod
    async def get_order_by_number(
            db: AsyncSession,
            order_number: str,
            user: User
    ) -> Optional[Order]:
        """Получение заказа по номеру"""
        order = await order_crud.get_by_order_number(db, order_number=order_number)

        if not order:
            return None

        if order.user_id != user.id:
            raise BusinessLogicError("Access denied to this order")

        return order

    async def update_order_status(
            self,
            db: AsyncSession,
            order_id: int,
            status: OrderStatus,
            user: User
    ) -> Order:
        """Обновление статуса заказа"""
        order = await self.get_order_by_id(db, order_id, user)

        if not order:
            raise BusinessLogicError("Order not found")

        if not self._can_update_status(order.status, status):
            raise BusinessLogicError(
                f"Cannot change status from {order.status} to {status}"
            )

        return await order_crud.update_status(
            db,
            order_id=order_id,
            status=status
        )

    @staticmethod
    def _can_update_status(current_status: OrderStatus, new_status: OrderStatus) -> bool:
        """Проверка возможности изменения статуса"""
        allowed_transitions = {
            OrderStatus.PENDING: [OrderStatus.PAID, OrderStatus.CANCELLED],
            OrderStatus.PAID: [OrderStatus.PROCESSING, OrderStatus.CANCELLED],
            OrderStatus.PROCESSING: [OrderStatus.COMPLETED, OrderStatus.FAILED],
            OrderStatus.COMPLETED: [],
            OrderStatus.CANCELLED: [],
            OrderStatus.FAILED: [OrderStatus.PENDING]
        }

        return new_status in allowed_transitions.get(current_status, [])

    async def cancel_order(
            self,
            db: AsyncSession,
            order_id: int,
            user: User,
            reason: Optional[str] = None
    ) -> Order:
        """Отмена заказа"""
        order = await self.get_order_by_id(db, order_id, user)

        if not order:
            raise BusinessLogicError("Order not found")

        if order.status not in [OrderStatus.PENDING, OrderStatus.PAID]:
            raise BusinessLogicError("Cannot cancel order in current status")

        # Возвращаем товары на склад
        await self._restore_products_stock(db, order)

        # Возвращаем средства на баланс
        if order.status == OrderStatus.PAID:
            await self._refund_to_balance(db, user, order)

        # Обновляем статус
        updated_order = await order_crud.update_status(
            db,
            order_id=order_id,
            status=OrderStatus.CANCELLED
        )

        if reason:
            updated_order.notes = f"{updated_order.notes or ''}\nCancellation reason: {reason}"
            await db.commit()
            await db.refresh(updated_order)

        logger.info(f"Order {order.order_number} cancelled")
        return updated_order

    @staticmethod
    async def _restore_products_stock(db: AsyncSession, order: Order):
        """Возврат товаров на склад"""
        for item in order.order_items:  # Работает благодаря lazy="selectin"
            product = await proxy_product_crud.get(db, obj_id=item.proxy_product_id)
            if product:
                product.stock_available += item.quantity
                await db.commit()

    @staticmethod
    async def _refund_to_balance(db: AsyncSession, user: User, order: Order):
        """Возврат средств на баланс"""
        await user_crud.update_balance(
            db,
            user=user,
            amount=float(order.total_amount)
        )

        logger.info(f"Refund {order.total_amount} to user {user.id} balance")

    async def get_order_summary(
            self,
            db: AsyncSession,
            user: User
    ) -> Dict[str, Any]:
        """Получение сводки по заказам"""
        orders = await self.get_user_orders(db, user)

        summary = {
            'total_orders': len(orders),
            'pending_orders': len([o for o in orders if o.status == OrderStatus.PENDING]),
            'completed_orders': len([o for o in orders if o.status == OrderStatus.COMPLETED]),
            'cancelled_orders': len([o for o in orders if o.status == OrderStatus.CANCELLED]),
            'total_spent': sum(o.total_amount for o in orders if o.status == OrderStatus.COMPLETED),
            'recent_orders': orders[:5]
        }

        return summary

    # Реализация абстрактных методов BaseService
    async def create(self, db: AsyncSession, obj_in: OrderCreate) -> Order:
        return await order_crud.create(db, obj_in=obj_in)

    async def get(self, db: AsyncSession, obj_id: int) -> Optional[Order]:
        return await order_crud.get(db, obj_id=obj_id)

    async def update(self, db: AsyncSession, db_obj: Order, obj_in: OrderUpdate) -> Order:
        return await order_crud.update(db, db_obj=db_obj, obj_in=obj_in)

    async def delete(self, db: AsyncSession, obj_id: int) -> bool:
        await order_crud.remove(db, obj_id=obj_id)
        return True

    async def get_multi(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Order]:
        return await order_crud.get_multi(db, skip=skip, limit=limit)


# Создаем экземпляр сервиса
order_service = OrderService()
