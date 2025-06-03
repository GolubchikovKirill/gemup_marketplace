"""
Сервис для управления заказами.

Обеспечивает создание, обработку и управление заказами пользователей,
включая интеграцию с провайдерами прокси и обработку платежей.
Полная production-ready реализация без мок-данных.
"""

import logging
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime, timedelta
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessLogicError
from app.crud.order import order_crud
from app.crud.proxy_purchase import proxy_purchase_crud
from app.integrations import get_proxy_provider
from app.models.models import Order, User, OrderStatus, ProviderType
from app.schemas.order import OrderCreate, OrderUpdate
from app.services.base import BaseService, BusinessRuleValidator
from app.services.cart_service import cart_service

logger = logging.getLogger(__name__)


class OrderBusinessRules(BusinessRuleValidator):
    """Валидатор бизнес-правил для заказов."""

    async def validate(self, data: dict, db: AsyncSession) -> bool:
        """
        Валидация бизнес-правил для заказа.

        Args:
            data: Данные для валидации (user_id, cart_items, total_amount)
            db: Сессия базы данных

        Returns:
            bool: Результат валидации

        Raises:
            BusinessLogicError: При нарушении бизнес-правил
        """
        try:
            user_id = data.get("user_id")
            total_amount = data.get("total_amount", Decimal('0'))
            cart_items = data.get("cart_items", [])

            if not user_id:
                raise BusinessLogicError("User ID is required")

            if not cart_items:
                raise BusinessLogicError("Cart is empty")

            if total_amount <= 0:
                raise BusinessLogicError("Order total must be positive")

            if total_amount > Decimal('50000.00'):  # Максимальная сумма заказа
                raise BusinessLogicError("Order amount exceeds maximum limit")

            # Проверка лимитов на количество товаров
            total_items = sum(item.quantity for item in cart_items)
            if total_items > 10000:  # Максимальное количество прокси в одном заказе
                raise BusinessLogicError("Order exceeds maximum item limit")

            logger.debug(f"Order business rules validation passed for user {user_id}")
            return True

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error during order business rules validation: {e}")
            raise BusinessLogicError(f"Validation failed: {str(e)}")


class OrderService(BaseService[Order, OrderCreate, OrderUpdate]):
    """
    Сервис для управления заказами.

    Предоставляет функциональность для создания заказов из корзины,
    обработки платежей, активации прокси и управления жизненным циклом заказов.
    """

    def __init__(self):
        super().__init__(Order)
        self.crud = order_crud
        self.business_rules = OrderBusinessRules()

    async def create_order_from_cart(self, db: AsyncSession, user: User) -> Order:
        """
        Создание заказа на основе содержимого корзины пользователя.

        Args:
            db: Сессия базы данных
            user: Пользователь, создающий заказ

        Returns:
            Order: Созданный заказ

        Raises:
            BusinessLogicError: При ошибках валидации или недостатке средств
        """
        try:
            # Валидация корзины перед созданием заказа
            cart_validation = await cart_service.validate_cart_before_checkout(
                db,
                user_id=user.id if not user.is_guest else None,
                session_id=user.guest_session_id if user.is_guest else None
            )

            if not cart_validation["is_valid"]:
                error_msg = "; ".join(cart_validation["errors"])
                raise BusinessLogicError(f"Cart validation failed: {error_msg}")

            # Получение содержимого корзины
            cart_items = await cart_service.get_user_cart(
                db,
                user_id=user.id if not user.is_guest else None,
                session_id=user.guest_session_id if user.is_guest else None
            )

            if not cart_items:
                raise BusinessLogicError("Cart is empty")

            # Расчет стоимости
            cart_total = await cart_service.calculate_cart_total(
                db,
                user_id=user.id if not user.is_guest else None,
                session_id=user.guest_session_id if user.is_guest else None
            )

            total_amount = Decimal(cart_total["total_amount"])

            # Валидация бизнес-правил
            validation_data = {
                "user_id": user.id,
                "cart_items": cart_items,
                "total_amount": total_amount
            }
            await self.business_rules.validate(validation_data, db)

            # Проверка баланса для зарегистрированных пользователей
            if not user.is_guest and user.balance < total_amount:
                raise BusinessLogicError(
                    f"Insufficient balance. Required: {total_amount}, Available: {user.balance}"
                )

            # Создание заказа
            order_number = self._generate_order_number()
            order_data = OrderCreate(
                order_number=order_number,
                user_id=user.id,
                total_amount=total_amount,
                currency="USD",
                status=OrderStatus.PENDING,
                notes=f"Order created from cart with {len(cart_items)} items"
            )

            order = await self.crud.create(db, obj_in=order_data)

            # Обработка оплаты для зарегистрированных пользователей
            if not user.is_guest:
                await self._process_balance_payment(db, user, order, total_amount)

            # Создание покупок прокси
            for cart_item in cart_items:
                try:
                    await self._create_proxy_purchase(db, order, cart_item)
                except Exception as e:
                    logger.error(f"Failed to create proxy purchase for cart item {cart_item.id}: {e}")
                    # Продолжаем обработку других элементов

            # Очистка корзины
            await cart_service.clear_cart(
                db,
                user_id=user.id if not user.is_guest else None,
                session_id=user.guest_session_id if user.is_guest else None
            )

            logger.info(f"Order created successfully: {order.order_number}")
            return order

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            raise BusinessLogicError(f"Failed to create order: {str(e)}")

    async def get_user_orders(
        self,
        db: AsyncSession,
        user_id: int,
        status: Optional[OrderStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Order]:
        """
        Получение списка заказов пользователя.

        Args:
            db: Сессия базы данных
            user_id: Идентификатор пользователя
            status: Фильтр по статусу заказа
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            List[Order]: Список заказов пользователя
        """
        try:
            return await self.crud.get_user_orders(
                db, user_id=user_id, status=status, skip=skip, limit=limit
            )
        except Exception as e:
            logger.error(f"Error getting user orders: {e}")
            return []

    async def get_order_by_id(
        self,
        db: AsyncSession,
        order_id: int,
        user_id: int
    ) -> Optional[Order]:
        """
        Получение заказа по идентификатору с проверкой прав доступа.

        Args:
            db: Сессия базы данных
            order_id: Идентификатор заказа
            user_id: Идентификатор пользователя (для проверки прав доступа)

        Returns:
            Optional[Order]: Заказ или None, если не найден или нет доступа
        """
        try:
            order = await self.crud.get_with_items(db, order_id=order_id)
            if order and order.user_id == user_id:
                return order
            return None
        except Exception as e:
            logger.error(f"Error getting order by ID: {e}")
            return None

    async def get_order_summary(
        self,
        db: AsyncSession,
        user_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Получение сводной статистики по заказам пользователя.

        Args:
            db: Сессия базы данных
            user_id: Идентификатор пользователя
            days: Период для статистики в днях

        Returns:
            Dict[str, Any]: Статистика заказов
        """
        try:
            return await self.crud.get_order_stats(db, user_id=user_id, days=days)
        except Exception as e:
            logger.error(f"Error getting order summary: {e}")
            return {
                "total_orders": 0,
                "total_amount": "0.00",
                "status_breakdown": {},
                "period_days": days
            }

    async def cancel_order(
        self,
        db: AsyncSession,
        order_id: int,
        user_id: int,
        reason: Optional[str] = None
    ) -> bool:
        """
        Отмена заказа пользователем.

        Args:
            db: Сессия базы данных
            order_id: Идентификатор заказа
            user_id: Идентификатор пользователя
            reason: Причина отмены

        Returns:
            bool: Успешность операции

        Raises:
            BusinessLogicError: При невозможности отмены заказа
        """
        try:
            order = await self.crud.get(db, obj_id=order_id)
            if not order or order.user_id != user_id:
                raise BusinessLogicError("Order not found or access denied")

            if order.status not in [OrderStatus.PENDING, OrderStatus.PAID]:
                raise BusinessLogicError(f"Cannot cancel order with status {order.status.value}")

            # Возврат средств при отмене оплаченного заказа
            if order.status == OrderStatus.PAID:
                await self._process_refund(db, order)

            # Обновление статуса заказа
            await self.crud.update_status(
                db,
                order=order,
                status=OrderStatus.CANCELLED
            )

            # Обновляем примечания
            order.notes = f"{order.notes or ''}\nCancelled: {reason or 'User requested'}"
            await db.commit()

            # Деактивация связанных покупок прокси
            await self._deactivate_order_proxies(db, order.id)

            logger.info(f"Order {order.order_number} cancelled by user {user_id}")
            return True

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            raise BusinessLogicError(f"Failed to cancel order: {str(e)}")

    async def update_order_status(
        self,
        db: AsyncSession,
        order_id: int,
        status: OrderStatus,
        payment_id: Optional[str] = None
    ) -> Optional[Order]:
        """
        Обновление статуса заказа (административная функция).

        Args:
            db: Сессия базы данных
            order_id: Идентификатор заказа
            status: Новый статус заказа
            payment_id: ID платежа (опционально)

        Returns:
            Optional[Order]: Обновленный заказ или None
        """
        try:
            order = await self.crud.get(db, obj_id=order_id)
            if not order:
                return None

            return await self.crud.update_status(
                db, order=order, status=status, payment_id=payment_id
            )

        except Exception as e:
            logger.error(f"Error updating order status: {e}")
            return None

    async def get_order_by_number(
        self,
        db: AsyncSession,
        order_number: str,
        user_id: Optional[int] = None
    ) -> Optional[Order]:
        """
        Получение заказа по номеру.

        Args:
            db: Сессия базы данных
            order_number: Номер заказа
            user_id: Идентификатор пользователя (для проверки прав доступа)

        Returns:
            Optional[Order]: Заказ или None
        """
        try:
            order = await self.crud.get_by_order_number(db, order_number=order_number)
            if order and (user_id is None or order.user_id == user_id):
                return order
            return None
        except Exception as e:
            logger.error(f"Error getting order by number: {e}")
            return None

    async def search_orders(
        self,
        db: AsyncSession,
        search_term: str,
        user_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Order]:
        """
        Поиск заказов по номеру или описанию.

        Args:
            db: Сессия базы данных
            search_term: Поисковый термин
            user_id: Идентификатор пользователя
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            List[Order]: Список найденных заказов
        """
        try:
            return await self.crud.search_orders(
                db, search_term=search_term, user_id=user_id, skip=skip, limit=limit
            )
        except Exception as e:
            logger.error(f"Error searching orders: {e}")
            return []

    async def get_orders_by_status(
        self,
        db: AsyncSession,
        status: OrderStatus,
        skip: int = 0,
        limit: int = 100
    ) -> List[Order]:
        """
        Получение заказов по статусу.

        Args:
            db: Сессия базы данных
            status: Статус заказа
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            List[Order]: Список заказов с указанным статусом
        """
        try:
            return await self.crud.get_orders_by_status(
                db, status=status, skip=skip, limit=limit
            )
        except Exception as e:
            logger.error(f"Error getting orders by status {status}: {e}")
            return []

    async def get_expired_orders(
        self,
        db: AsyncSession,
        hours_old: int = 24
    ) -> List[Order]:
        """
        Получение просроченных заказов для автоматической отмены.

        Args:
            db: Сессия базы данных
            hours_old: Количество часов для определения просрочки

        Returns:
            List[Order]: Список просроченных заказов
        """
        try:
            return await self.crud.get_expired_orders(db, hours_old=hours_old)
        except Exception as e:
            logger.error(f"Error getting expired orders: {e}")
            return []

    async def auto_cancel_expired_orders(self, db: AsyncSession) -> int:
        """
        Автоматическая отмена просроченных заказов.

        Args:
            db: Сессия базы данных

        Returns:
            int: Количество отмененных заказов
        """
        try:
            expired_orders = await self.get_expired_orders(db, hours_old=24)
            cancelled_count = 0

            for order in expired_orders:
                try:
                    await self.crud.update_status(
                        db,
                        order=order,
                        status=OrderStatus.CANCELLED
                    )
                    order.notes = f"{order.notes or ''}\nAuto-cancelled: Payment timeout"
                    await db.commit()

                    # Деактивация прокси
                    await self._deactivate_order_proxies(db, order.id)
                    cancelled_count += 1

                except Exception as e:
                    logger.error(f"Error auto-cancelling order {order.id}: {e}")
                    continue

            if cancelled_count > 0:
                logger.info(f"Auto-cancelled {cancelled_count} expired orders")

            return cancelled_count

        except Exception as e:
            logger.error(f"Error in auto-cancel expired orders: {e}")
            return 0

    async def _create_proxy_purchase(self, db: AsyncSession, order: Order, cart_item) -> None:
        """
        Создание покупки прокси через интеграцию с провайдерами.

        Args:
            db: Сессия базы данных
            order: Заказ
            cart_item: Элемент корзины
        """
        try:
            proxy_data = await self._purchase_proxies_from_provider(cart_item)

            # Рассчитываем дату истечения
            duration_days = getattr(cart_item.proxy_product, 'duration_days', 30)
            expires_at = datetime.now() + timedelta(days=duration_days)

            await proxy_purchase_crud.create_purchase(
                db,
                user_id=order.user_id,
                proxy_product_id=cart_item.proxy_product_id,
                order_id=order.id,
                proxy_list=proxy_data["proxy_list"],
                username=proxy_data.get("username"),
                password=proxy_data.get("password"),
                expires_at=expires_at,
                provider_order_id=proxy_data.get("provider_order_id"),
                provider_metadata=proxy_data.get("provider_metadata")
            )

        except Exception as e:
            logger.error(f"Error creating proxy purchase: {e}")
            raise

    @staticmethod
    async def _purchase_proxies_from_provider(cart_item) -> Dict[str, Any]:
        """
        Покупка прокси у соответствующего провайдера.

        Args:
            cart_item: Элемент корзины с информацией о продукте

        Returns:
            Dict[str, Any]: Данные купленных прокси

        Raises:
            BusinessLogicError: При ошибках интеграции с провайдером
        """
        try:
            provider = cart_item.proxy_product.provider

            if provider == ProviderType.PROVIDER_711:
                proxy_api = get_proxy_provider("711proxy")
                return await proxy_api.purchase_proxies(
                    product_id=cart_item.proxy_product_id,
                    quantity=cart_item.quantity,
                    duration_days=getattr(cart_item.proxy_product, 'duration_days', 30)
                )
            else:
                raise BusinessLogicError(f"Provider {provider} not supported")

        except Exception as e:
            logger.error(f"Error purchasing proxies from provider: {e}")
            raise BusinessLogicError(f"Failed to purchase proxies: {str(e)}")

    @staticmethod
    async def _process_balance_payment(
        db: AsyncSession,
        user: User,
        order: Order,
        amount: Decimal
    ) -> None:
        """
        Обработка оплаты с баланса пользователя.

        Args:
            db: Сессия базы данных
            user: Пользователь
            order: Заказ
            amount: Сумма платежа
        """
        try:
            from app.crud.user import user_crud

            # Списание с баланса
            await user_crud.update_balance(db, user=user, amount=-amount)

            # Обновление статуса заказа
            await order_crud.update_status(
                db,
                order=order,
                status=OrderStatus.PAID
            )

            logger.info(f"Balance payment processed for order {order.order_number}: {amount}")

        except Exception as e:
            logger.error(f"Error processing balance payment: {e}")
            raise

    @staticmethod
    async def _process_refund(db: AsyncSession, order: Order) -> None:
        """
        Обработка возврата средств за отмененный заказ.

        Args:
            db: Сессия базы данных
            order: Заказ для возврата
        """
        try:
            from app.crud.user import user_crud

            user = await user_crud.get(db, obj_id=order.user_id)
            if user:
                await user_crud.update_balance(db, user=user, amount=order.total_amount)
                logger.info(f"Refund processed for order {order.order_number}: {order.total_amount}")

        except Exception as e:
            logger.error(f"Error processing refund: {e}")
            raise

    @staticmethod
    async def _activate_proxies_for_order(db: AsyncSession, order: Order) -> bool:
        """
        Активация прокси для заказа.

        Args:
            db: Сессия базы данных
            order: Заказ

        Returns:
            bool: Успешность активации
        """
        try:
            # Получаем все покупки прокси для заказа
            from sqlalchemy import select
            result = await db.execute(
                select(proxy_purchase_crud.model).where(
                    proxy_purchase_crud.model.order_id == order.id
                )
            )
            purchases = list(result.scalars().all())

            for purchase in purchases:
                purchase.is_active = True

            await db.commit()
            logger.info(f"Activated {len(purchases)} proxy purchases for order {order.id}")
            return True

        except Exception as e:
            logger.error(f"Error activating proxies for order {order.id}: {e}")
            return False

    @staticmethod
    async def _deactivate_order_proxies(db: AsyncSession, order_id: int) -> bool:
        """
        Деактивация прокси для отмененного заказа.

        Args:
            db: Сессия базы данных
            order_id: Идентификатор заказа

        Returns:
            bool: Успешность деактивации
        """
        try:
            # Получаем все покупки прокси для заказа
            from sqlalchemy import select
            result = await db.execute(
                select(proxy_purchase_crud.model).where(
                    proxy_purchase_crud.model.order_id == order_id
                )
            )
            purchases = list(result.scalars().all())

            for purchase in purchases:
                purchase.is_active = False

            await db.commit()
            logger.info(f"Deactivated {len(purchases)} proxy purchases for order {order_id}")
            return True

        except Exception as e:
            logger.error(f"Error deactivating proxies for order {order_id}: {e}")
            return False

    @staticmethod
    def _generate_order_number() -> str:
        """
        Генерация уникального номера заказа.

        Returns:
            str: Уникальный номер заказа в формате ORD-YYYYMMDD-XXXXXXXX
        """
        timestamp = datetime.now().strftime("%Y%m%d")
        unique_id = str(uuid.uuid4())[:8].upper()
        return f"ORD-{timestamp}-{unique_id}"

    # Реализация абстрактных методов BaseService
    async def create(self, db: AsyncSession, obj_in: OrderCreate) -> Order:
        return await self.crud.create(db, obj_in=obj_in)

    async def get(self, db: AsyncSession, obj_id: int) -> Optional[Order]:
        return await self.crud.get(db, obj_id=obj_id)

    async def update(self, db: AsyncSession, db_obj: Order, obj_in: OrderUpdate) -> Order:
        return await self.crud.update(db, db_obj=db_obj, obj_in=obj_in)

    async def delete(self, db: AsyncSession, obj_id: int) -> bool:
        result = await self.crud.delete(db, obj_id=obj_id)
        return result is not None

    async def get_multi(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Order]:
        return await self.crud.get_multi(db, skip=skip, limit=limit)


order_service = OrderService()
