"""
Моки для внутренних сервисов
Используются для изоляции unit тестов
"""

from typing import Dict, Any, List
from decimal import Decimal
from datetime import datetime


class MockOrderService:
    """Мок для OrderService"""

    def __init__(self):
        self.orders = {}
        self.order_counter = 1

    async def create_order_from_cart(self, db, user) -> Dict[str, Any]:
        """Мок создания заказа"""
        order_id = self.order_counter
        self.order_counter += 1

        order = {
            "id": order_id,
            "order_number": f"ORD-MOCK-{order_id:06d}",
            "user_id": user.id,
            "total_amount": Decimal("10.00"),
            "currency": "USD",
            "status": "paid",
            "created_at": datetime.now()
        }

        self.orders[order_id] = order
        return order

    async def get_user_orders(self, db, user_id: int) -> List[Dict[str, Any]]:
        """Мок получения заказов пользователя"""
        return [order for order in self.orders.values() if order["user_id"] == user_id]

    async def cancel_order(self, db, order_id: int, user_id: int) -> bool:
        """Мок отмены заказа"""
        if order_id in self.orders and self.orders[order_id]["user_id"] == user_id:
            self.orders[order_id]["status"] = "cancelled"
            return True
        return False


class MockPaymentService:
    """Мок для PaymentService"""

    def __init__(self):
        self.transactions = {}
        self.transaction_counter = 1

    async def create_payment(self, db, user, amount: Decimal, **kwargs) -> Dict[str, Any]:
        """Мок создания платежа"""
        transaction_id = f"TXN-MOCK-{self.transaction_counter:06d}"
        self.transaction_counter += 1

        payment = {
            "transaction_id": transaction_id,
            "payment_url": f"https://mock-payment.com/pay/{transaction_id}",
            "amount": str(amount),
            "currency": "USD",
            "status": "pending"
        }

        self.transactions[transaction_id] = payment
        return payment

    async def get_payment_status(self, db, transaction_id: str) -> Dict[str, Any]:
        """Мок получения статуса платежа"""
        if transaction_id not in self.transactions:
            raise Exception("Transaction not found")

        return self.transactions[transaction_id]

    async def process_webhook(self, db, webhook_data: Dict[str, Any]) -> bool:
        """Мок обработки webhook"""
        order_id = webhook_data.get("order_id")
        if order_id in self.transactions:
            self.transactions[order_id]["status"] = webhook_data.get("status", "completed")
            return True
        return False


class MockCartService:
    """Мок для CartService"""

    def __init__(self):
        self.carts = {}

    async def get_user_cart(self, db, user_id: int = None, session_id: str = None) -> List[Dict[str, Any]]:
        """Мок получения корзины"""
        key = user_id or session_id
        return self.carts.get(key, [])

    async def add_to_cart(self, db, user_id: int, product_id: int, quantity: int) -> Dict[str, Any]:
        """Мок добавления в корзину"""
        if user_id not in self.carts:
            self.carts[user_id] = []

        item = {
            "id": len(self.carts[user_id]) + 1,
            "product_id": product_id,
            "quantity": quantity
        }

        self.carts[user_id].append(item)
        return item

    async def clear_cart(self, db, user_id: int = None, session_id: str = None) -> bool:
        """Мок очистки корзины"""
        key = user_id or session_id
        if key in self.carts:
            self.carts[key] = []
            return True
        return False
