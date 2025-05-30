import hashlib
import hmac
import json
import logging
import uuid
from decimal import Decimal
from typing import Dict, Any
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class CryptomusAPI:
    """Интеграция с API Cryptomus - ЧИСТЫЙ код без моков"""

    def __init__(self):
        self.base_url = settings.cryptomus_base_url
        self.api_key = settings.cryptomus_api_key
        self.merchant_id = settings.cryptomus_merchant_id
        self.webhook_secret = settings.cryptomus_webhook_secret

    def _generate_sign(self, data: Dict[str, Any]) -> str:
        """Генерация подписи для запроса"""
        if not self.api_key:
            logger.warning("API key not configured")
            return ""

        try:
            # Сортируем данные по ключам и создаем строку
            sorted_data = dict(sorted(data.items()))
            data_string = json.dumps(sorted_data, separators=(',', ':'), ensure_ascii=False)

            # Кодируем в base64 и создаем подпись
            import base64
            encoded_data = base64.b64encode(data_string.encode('utf-8')).decode('utf-8')

            signature = hmac.new(
                self.api_key.encode('utf-8'),
                encoded_data.encode('utf-8'),
                hashlib.md5
            ).hexdigest()

            return signature
        except Exception as e:
            logger.error(f"Error generating signature: {e}")
            return ""

    def _verify_webhook_signature(self, data: Dict[str, Any], received_sign: str) -> bool:
        """Проверка подписи webhook"""
        try:
            if not self.webhook_secret:
                logger.warning("Webhook secret not configured")
                return False

            if not received_sign:
                logger.warning("No signature received in webhook")
                return False

            # Исключаем sign из данных для проверки
            data_copy = {k: v for k, v in data.items() if k != 'sign'}
            expected_sign = self._generate_webhook_sign(data_copy)

            if not expected_sign:
                return False

            return hmac.compare_digest(expected_sign, received_sign)
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {e}")
            return False

    def _generate_webhook_sign(self, data: Dict[str, Any]) -> str:
        """Генерация подписи для webhook"""
        if not self.webhook_secret:
            logger.warning("Webhook secret not configured")
            return ""

        try:
            # Сортируем данные и создаем строку
            sorted_data = dict(sorted(data.items()))
            data_string = json.dumps(sorted_data, separators=(',', ':'), ensure_ascii=False)

            # Создаем подпись с webhook secret
            signature = hmac.new(
                self.webhook_secret.encode('utf-8'),
                data_string.encode('utf-8'),
                hashlib.md5
            ).hexdigest()

            return signature
        except Exception as e:
            logger.error(f"Error generating webhook signature: {e}")
            return ""

    async def create_payment(
            self,
            amount: Decimal,
            currency: str = "USD",
            order_id: str = None,
            callback_url: str = None,
            success_url: str = None,
            fail_url: str = None
    ) -> Dict[str, Any]:
        """Создание платежа"""
        try:
            # Генерируем уникальный order_id если не передан
            if not order_id:
                order_id = f"payment_{uuid.uuid4().hex[:16]}"

            # Подготавливаем данные для запроса
            payment_data = {
                "amount": str(amount),
                "currency": currency,
                "order_id": order_id,
                "merchant": self.merchant_id or "test_merchant",
                "network": "tron",
                "url_callback": callback_url or f"{settings.base_url}/api/v1/payments/webhook/cryptomus",
                "url_success": success_url or f"{settings.frontend_url}/payment/success",
                "url_return": fail_url or f"{settings.frontend_url}/payment/failed",
                "is_payment_multiple": False,
                "lifetime": 3600,
                "to_currency": "USDT"
            }

            # Генерируем подпись
            sign = self._generate_sign(payment_data)

            # Заголовки запроса
            headers = {
                "merchant": self.merchant_id or "test_merchant",
                "sign": sign,
                "Content-Type": "application/json"
            }

            # Отправляем запрос к реальному API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/payment",
                    json=payment_data,
                    headers=headers,
                    timeout=30.0
                )

                response.raise_for_status()
                result = response.json()

                logger.info(f"Payment created: {order_id}, amount: {amount}")
                return result

        except httpx.HTTPError as e:
            logger.error(f"HTTP error creating payment: {e}")
            raise Exception(f"Payment creation failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating payment: {e}")
            raise Exception(f"Payment creation failed: {str(e)}")

    async def get_payment_info(self, payment_uuid: str) -> Dict[str, Any]:
        """Получение информации о платеже"""
        try:
            data = {
                "uuid": payment_uuid,
                "merchant": self.merchant_id
            }

            sign = self._generate_sign(data)

            headers = {
                "merchant": self.merchant_id,
                "sign": sign,
                "Content-Type": "application/json"
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/payment/info",
                    json=data,
                    headers=headers,
                    timeout=30.0
                )

                response.raise_for_status()
                result = response.json()

                return result

        except Exception as e:
            logger.error(f"Error getting payment info: {e}")
            raise Exception(f"Failed to get payment info: {str(e)}")

    async def get_payment_history(
            self,
            date_from: str = None,
            date_to: str = None,
            limit: int = 100
    ) -> Dict[str, Any]:
        """Получение истории платежей"""
        try:
            data = {
                "merchant": self.merchant_id,
                "limit": limit
            }

            if date_from:
                data["date_from"] = date_from
            if date_to:
                data["date_to"] = date_to

            sign = self._generate_sign(data)

            headers = {
                "merchant": self.merchant_id,
                "sign": sign,
                "Content-Type": "application/json"
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/payment/list",
                    json=data,
                    headers=headers,
                    timeout=30.0
                )

                response.raise_for_status()
                result = response.json()

                return result

        except Exception as e:
            logger.error(f"Error getting payment history: {e}")
            raise Exception(f"Failed to get payment history: {str(e)}")


cryptomus_api = CryptomusAPI()
