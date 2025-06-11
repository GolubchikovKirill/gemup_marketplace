"""
Моки для PaymentService - ТОЛЬКО для тестов
"""

from typing import Dict, Any
from decimal import Decimal
from datetime import datetime
import uuid


class MockPaymentData:
    """Мок-данные для платежей"""

    @staticmethod
    def generate_mock_transaction() -> Dict[str, Any]:
        """Генерация мок-транзакции"""
        return {
            "transaction_id": f"TXN-MOCK-{uuid.uuid4().hex[:8].upper()}",
            "amount": "50.00",
            "currency": "USD",
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }

    @staticmethod
    def generate_mock_payment_response(amount: Decimal) -> Dict[str, Any]:
        """Генерация мок-ответа платежа"""
        transaction_id = f"TXN-MOCK-{uuid.uuid4().hex[:8].upper()}"
        return {
            "transaction_id": transaction_id,
            "payment_url": f"https://mock-payment.com/pay/{transaction_id}",
            "amount": str(amount),
            "currency": "USD",
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
