"""
Интеграция с Cryptomus API для обработки платежей.

Обеспечивает создание платежей, проверку статуса и обработку webhook'ов
от платежной системы Cryptomus.
"""

import hashlib
import hmac
import json
import logging
import uuid
import base64
from decimal import Decimal
from typing import Dict, Any, Optional

from app.core.config import settings
from .base import BaseIntegration, IntegrationError

logger = logging.getLogger(__name__)


class CryptomusAPI(BaseIntegration):
    """
    API клиент для Cryptomus платежной системы.

    Реализует полную интеграцию с Cryptomus для:
    - Создания платежей
    - Получения информации о платежах
    - Проверки webhook подписей
    - Управления балансом мерчанта
    """

    def __init__(self):
        super().__init__("cryptomus")
        self._validate_configuration()

    @property
    def base_url(self) -> str:
        """Базовый URL Cryptomus API."""
        return getattr(settings, 'cryptomus_base_url', "https://api.cryptomus.com/v1")

    @property
    def api_key(self) -> str:
        """API ключ Cryptomus."""
        return getattr(settings, 'cryptomus_api_key', "")

    @property
    def merchant_id(self) -> str:
        """ID мерчанта Cryptomus."""
        return getattr(settings, 'cryptomus_merchant_id', "")

    @property
    def webhook_secret(self) -> str:
        """Секрет для webhook подписей."""
        return getattr(settings, 'cryptomus_webhook_secret', "")

    def _validate_configuration(self):
        """Валидация конфигурации Cryptomus."""
        missing_configs = []

        if not self.api_key:
            missing_configs.append("cryptomus_api_key")
        if not self.merchant_id:
            missing_configs.append("cryptomus_merchant_id")

        if missing_configs:
            self.logger.warning(f"Missing Cryptomus configuration: {', '.join(missing_configs)}")

    def _generate_sign(self, data: Dict[str, Any]) -> str:
        """
        Генерация подписи для запроса к Cryptomus API.

        Args:
            data: Данные для подписи

        Returns:
            str: Подпись запроса

        Raises:
            IntegrationError: При ошибках генерации подписи
        """
        if not self.api_key:
            raise IntegrationError("API key not configured for signature generation", provider="cryptomus")

        try:
            # Сортируем данные по ключам и создаем JSON строку
            sorted_data = dict(sorted(data.items()))
            data_string = json.dumps(sorted_data, separators=(',', ':'), ensure_ascii=False)

            # Кодируем в base64
            encoded_data = base64.b64encode(data_string.encode('utf-8')).decode('utf-8')

            # Создаем HMAC подпись
            signature = hmac.new(
                self.api_key.encode('utf-8'),
                encoded_data.encode('utf-8'),
                hashlib.md5
            ).hexdigest()

            return signature

        except Exception as e:
            self.logger.error(f"Error generating Cryptomus signature: {e}")
            raise IntegrationError(f"Failed to generate signature: {str(e)}", provider="cryptomus")

    def verify_webhook_signature(self, data: Dict[str, Any], received_sign: str) -> bool:
        """
        Проверка подписи webhook от Cryptomus - КЛЮЧЕВОЕ для MVP.

        Args:
            data: Данные webhook
            received_sign: Полученная подпись

        Returns:
            bool: True если подпись валидна
        """
        try:
            if not self.webhook_secret:
                self.logger.warning("Webhook secret not configured")
                return False

            if not received_sign:
                self.logger.warning("No signature received in webhook")
                return False

            # Исключаем sign из данных для проверки
            data_copy = {k: v for k, v in data.items() if k != 'sign'}
            expected_sign = self._generate_webhook_sign(data_copy)

            if not expected_sign:
                return False

            is_valid = hmac.compare_digest(expected_sign, received_sign)

            if not is_valid:
                self.logger.warning("Invalid webhook signature received")
            else:
                self.logger.debug("Webhook signature verified successfully")

            return is_valid

        except Exception as e:
            self.logger.error(f"Error verifying webhook signature: {e}")
            return False

    def _generate_webhook_sign(self, data: Dict[str, Any]) -> str:
        """
        Генерация подписи для webhook.

        Args:
            data: Данные webhook

        Returns:
            str: Подпись webhook

        Raises:
            IntegrationError: При ошибках генерации подписи
        """
        if not self.webhook_secret:
            raise IntegrationError("Webhook secret not configured", provider="cryptomus")

        try:
            # Сортируем данные и создаем JSON строку
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
            self.logger.error(f"Error generating webhook signature: {e}")
            raise IntegrationError(f"Failed to generate webhook signature: {str(e)}", provider="cryptomus")

    async def create_payment(
        self,
        amount: Decimal,
        currency: str = "USD",
        order_id: Optional[str] = None,
        callback_url: Optional[str] = None,
        success_url: Optional[str] = None,
        fail_url: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Создание платежа в Cryptomus - КЛЮЧЕВОЕ для MVP.

        Args:
            amount: Сумма платежа
            currency: Валюта платежа
            order_id: ID заказа в нашей системе
            callback_url: URL для webhook уведомлений
            success_url: URL перенаправления при успехе
            fail_url: URL перенаправления при ошибке
            **kwargs: Дополнительные параметры

        Returns:
            Dict[str, Any]: Данные созданного платежа

        Raises:
            IntegrationError: При ошибках создания платежа
        """
        try:
            # Валидация входных данных
            if amount <= 0:
                raise IntegrationError("Payment amount must be positive", provider="cryptomus")

            if not self.api_key or not self.merchant_id:
                raise IntegrationError("Cryptomus API credentials not configured", provider="cryptomus")

            # Валидация валюты
            supported_currencies = ["USD", "EUR", "RUB", "BTC", "ETH", "USDT", "LTC", "TRX"]
            if currency not in supported_currencies:
                raise IntegrationError(f"Unsupported currency: {currency}", provider="cryptomus")

            # Генерируем уникальный order_id если не передан
            if not order_id:
                order_id = f"payment_{uuid.uuid4().hex[:16]}"

            # Валидация order_id
            if len(order_id) > 50:
                raise IntegrationError("Order ID too long (max 50 characters)", provider="cryptomus")

            # Получаем базовые URL из настроек
            base_url = getattr(settings, 'base_url', 'http://localhost:8000')
            frontend_url = getattr(settings, 'frontend_url', 'http://localhost:3000')

            # Подготавливаем данные для запроса
            payment_data = {
                "amount": str(amount),
                "currency": currency,
                "order_id": order_id,
                "merchant": self.merchant_id,
                "network": kwargs.get("network", "tron"),
                "url_callback": callback_url or f"{base_url}/api/v1/payments/webhook/cryptomus",
                "url_success": success_url or f"{frontend_url}/payment/success",
                "url_return": fail_url or f"{frontend_url}/payment/failed",
                "is_payment_multiple": kwargs.get("is_payment_multiple", False),
                "lifetime": min(kwargs.get("lifetime", 3600), 7200),  # Максимум 2 часа
                "to_currency": kwargs.get("to_currency", "USDT")
            }

            # Добавляем дополнительные параметры если есть
            optional_params = ["email", "course_source", "except_coins", "description"]
            for param in optional_params:
                if param in kwargs and kwargs[param]:
                    payment_data[param] = str(kwargs[param])[:255]  # Ограничиваем длину

            # Генерируем подпись
            sign = self._generate_sign(payment_data)

            # Заголовки запроса
            headers = {
                "merchant": self.merchant_id,
                "sign": sign
            }

            # Отправляем запрос
            result = await self.make_request("POST", "/payment", data=payment_data, headers=headers)

            # Проверяем успешность ответа
            if result.get("state") != 0:
                error_msg = result.get("message", "Unknown payment creation error")
                error_code = result.get("error_code", "UNKNOWN")
                raise IntegrationError(
                    f"Cryptomus payment creation failed: {error_msg}",
                    provider="cryptomus",
                    error_code=error_code
                )

            payment_info = result.get("result", {})

            # Валидация ответа
            required_fields = ["uuid", "url"]
            missing_fields = [field for field in required_fields if field not in payment_info]
            if missing_fields:
                raise IntegrationError(
                    f"Invalid payment response, missing fields: {missing_fields}",
                    provider="cryptomus"
                )

            self.log_operation("create_payment", {
                "order_id": order_id,
                "amount": str(amount),
                "currency": currency,
                "payment_uuid": payment_info.get("uuid")
            })

            return payment_info

        except IntegrationError:
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error creating Cryptomus payment: {e}")
            raise IntegrationError(f"Payment creation failed: {str(e)}", provider="cryptomus")

    async def get_payment_info(self, payment_uuid: str) -> Dict[str, Any]:
        """
        Получение информации о платеже.

        Args:
            payment_uuid: UUID платежа в Cryptomus

        Returns:
            Dict[str, Any]: Информация о платеже

        Raises:
            IntegrationError: При ошибках получения информации
        """
        try:
            if not payment_uuid or not payment_uuid.strip():
                raise IntegrationError("Payment UUID is required", provider="cryptomus")

            # Валидация UUID формата
            try:
                uuid.UUID(payment_uuid)
            except ValueError:
                raise IntegrationError("Invalid payment UUID format", provider="cryptomus")

            data = {
                "uuid": payment_uuid.strip(),
                "merchant": self.merchant_id
            }

            sign = self._generate_sign(data)

            headers = {
                "merchant": self.merchant_id,
                "sign": sign
            }

            result = await self.make_request("POST", "/payment/info", data=data, headers=headers)

            # Проверяем успешность ответа
            if result.get("state") != 0:
                error_msg = result.get("message", "Payment not found")
                error_code = result.get("error_code", "NOT_FOUND")
                raise IntegrationError(
                    f"Cryptomus payment info error: {error_msg}",
                    provider="cryptomus",
                    error_code=error_code
                )

            payment_info = result.get("result", {})

            self.log_operation("get_payment_info", {
                "payment_uuid": payment_uuid,
                "status": payment_info.get("status", "unknown")
            })

            return payment_info

        except IntegrationError:
            raise
        except Exception as e:
            self.logger.error(f"Error getting Cryptomus payment info: {e}")
            raise IntegrationError(f"Failed to get payment info: {str(e)}", provider="cryptomus")

    async def get_merchant_balance(self) -> Dict[str, Any]:
        """
        Получение баланса мерчанта.

        Returns:
            Dict[str, Any]: Информация о балансе

        Raises:
            IntegrationError: При ошибках получения баланса
        """
        try:
            data = {
                "merchant": self.merchant_id
            }

            sign = self._generate_sign(data)

            headers = {
                "merchant": self.merchant_id,
                "sign": sign
            }

            result = await self.make_request("POST", "/balance", data=data, headers=headers)

            # Проверяем успешность ответа
            if result.get("state") != 0:
                error_msg = result.get("message", "Failed to get balance")
                error_code = result.get("error_code", "UNKNOWN")
                raise IntegrationError(
                    f"Cryptomus balance error: {error_msg}",
                    provider="cryptomus",
                    error_code=error_code
                )

            balance_info = result.get("result", {})

            self.log_operation("get_merchant_balance", {
                "balances_count": len(balance_info.get("merchant", {}).get("balance", []))
            })

            return balance_info

        except IntegrationError:
            raise
        except Exception as e:
            self.logger.error(f"Error getting Cryptomus merchant balance: {e}")
            raise IntegrationError(f"Failed to get merchant balance: {str(e)}", provider="cryptomus")

    async def test_connection(self) -> bool:
        """
        Тестирование подключения к Cryptomus API.

        Returns:
            bool: True если подключение успешно
        """
        try:
            if not self.api_key or not self.merchant_id:
                self.logger.warning("Cryptomus API credentials not configured")
                return False

            # Пытаемся получить баланс как тест подключения
            await self.get_merchant_balance()
            self.logger.info("Cryptomus API connection successful")
            return True

        except IntegrationError as e:
            if e.error_code in ["INVALID_CREDENTIALS", "UNAUTHORIZED"]:
                self.logger.error("Cryptomus API credentials invalid")
            else:
                self.logger.error(f"Cryptomus connection test failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Cryptomus connection test failed: {e}")
            return False

    @staticmethod
    def get_payment_status_mapping(cryptomus_status: str) -> str:
        """
        Маппинг статусов Cryptomus в наши внутренние статусы.

        Args:
            cryptomus_status: Статус от Cryptomus

        Returns:
            str: Внутренний статус
        """
        status_mapping = {
            "pending": "pending",
            "process": "pending",
            "paid": "completed",
            "paid_over": "completed",
            "payment_wait": "pending",
            "confirming": "pending",
            "confirmed": "completed",
            "check": "pending",
            "cancel": "cancelled",
            "fail": "failed",
            "wrong_amount": "failed",
            "timeout": "failed",
            "expired": "failed"
        }

        return status_mapping.get(cryptomus_status.lower(), "pending")

    # Реализация абстрактных методов для совместимости
    async def purchase_proxies(
        self,
        product_id: int,
        quantity: int,
        duration_days: int = 30,
        country: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Cryptomus не поддерживает покупку прокси."""
        raise IntegrationError("Cryptomus does not support proxy purchases", provider="cryptomus")

    async def get_proxy_status(self, order_id: str) -> Dict[str, Any]:
        """Cryptomus не поддерживает статус прокси."""
        raise IntegrationError("Cryptomus does not support proxy status", provider="cryptomus")


cryptomus_api = CryptomusAPI()
