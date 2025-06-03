"""
Схемы для платежных операций.

Содержит все необходимые схемы для работы с платежами,
включая Cryptomus интеграцию и webhook обработку.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, field_validator, field_serializer


class PaymentCreateRequest(BaseModel):
    """Схема запроса создания платежа."""
    amount: Decimal = Field(..., gt=0, le=10000, description="Сумма платежа")
    currency: str = Field("USD", description="Валюта")
    payment_method: str = Field("cryptomus", description="Метод оплаты")
    description: Optional[str] = Field(None, description="Описание платежа")

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        if v < Decimal('1.00'):
            raise ValueError('Minimum payment amount is $1.00')
        if v > Decimal('10000.00'):
            raise ValueError('Maximum payment amount is $10,000.00')
        return v

    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v: str) -> str:
        allowed_currencies = ['USD', 'EUR', 'BTC', 'ETH', 'USDT', 'LTC', 'TRX']
        if v.upper() not in allowed_currencies:
            raise ValueError(f'Currency must be one of: {", ".join(allowed_currencies)}')
        return v.upper()


class PaymentResponse(BaseModel):
    """Схема ответа создания платежа."""
    transaction_id: str = Field(..., description="ID транзакции")
    payment_url: Optional[str] = Field(None, description="URL для оплаты")
    amount: str = Field(..., description="Сумма платежа")
    currency: str = Field(..., description="Валюта")
    status: str = Field(..., description="Статус платежа")
    payment_method: str = Field(..., description="Метод оплаты")
    expires_at: Optional[datetime] = Field(None, description="Время истечения")
    qr_code: Optional[str] = Field(None, description="QR код для оплаты")
    wallet_address: Optional[str] = Field(None, description="Адрес кошелька")
    created_at: datetime = Field(..., description="Время создания")

    @field_serializer('expires_at', 'created_at')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None


class PaymentStatusResponse(BaseModel):
    """Схема ответа статуса платежа."""
    transaction_id: str = Field(..., description="ID транзакции")
    amount: str = Field(..., description="Сумма платежа")
    currency: str = Field(..., description="Валюта")
    status: str = Field(..., description="Текущий статус платежа")
    payment_method: str = Field(..., description="Метод платежа")
    provider_transaction_id: Optional[str] = Field(None, description="ID транзакции у провайдера")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")
    processed_at: Optional[datetime] = Field(None, description="Время обработки")

    @field_serializer('created_at', 'updated_at', 'processed_at')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None


class PaymentCallbackData(BaseModel):
    """Схема данных callback от Cryptomus - ДОБАВЛЕНО для исправления ошибки."""
    order_id: str = Field(..., description="ID заказа в системе Cryptomus")
    uuid: str = Field(..., description="UUID транзакции")
    status: str = Field(..., description="Статус платежа")
    amount: str = Field(..., description="Сумма")
    currency: str = Field(..., description="Валюта")
    payer_currency: Optional[str] = Field(None, description="Валюта плательщика")
    payer_amount: Optional[str] = Field(None, description="Сумма в валюте плательщика")
    txid: Optional[str] = Field(None, description="ID транзакции в блокчейне")
    sign: str = Field(..., description="Подпись безопасности")
    network: Optional[str] = Field(None, description="Сеть блокчейна")
    address: Optional[str] = Field(None, description="Адрес кошелька")
    from_address: Optional[str] = Field(None, description="Адрес отправителя")
    fee: Optional[str] = Field(None, description="Комиссия")
    merchant_amount: Optional[str] = Field(None, description="Сумма мерчанта")
    is_final: Optional[bool] = Field(None, description="Финальный статус")

    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Валидация статуса от Cryptomus."""
        allowed_statuses = [
            'paid', 'paid_over', 'fail', 'cancel', 'system_fail',
            'refund_process', 'refund_fail', 'refund_paid', 'process'
        ]
        if v.lower() not in allowed_statuses:
            raise ValueError(f'Status must be one of: {", ".join(allowed_statuses)}')
        return v.lower()


class PaymentRefundRequest(BaseModel):
    """Схема запроса возврата платежа."""
    transaction_id: str = Field(..., description="ID транзакции для возврата")
    amount: Optional[Decimal] = Field(None, gt=0, description="Сумма возврата (если частичный)")
    reason: str = Field(..., max_length=500, description="Причина возврата")
    refund_type: str = Field("full", description="Тип возврата: full или partial")

    @field_validator('refund_type')
    @classmethod
    def validate_refund_type(cls, v: str) -> str:
        if v not in ['full', 'partial']:
            raise ValueError('Refund type must be "full" or "partial"')
        return v


class PaymentRefundResponse(BaseModel):
    """Схема ответа возврата платежа."""
    refund_id: str = Field(..., description="ID возврата")
    transaction_id: str = Field(..., description="ID исходной транзакции")
    amount: str = Field(..., description="Сумма возврата")
    currency: str = Field(..., description="Валюта")
    status: str = Field(..., description="Статус возврата")
    reason: str = Field(..., description="Причина возврата")
    created_at: str = Field(..., description="Время создания возврата")
    processed_at: Optional[str] = Field(None, description="Время обработки")


class PaymentVerificationRequest(BaseModel):
    """Запрос верификации платежа."""
    transaction_id: str = Field(..., description="ID транзакции")


class PaymentVerificationResponse(BaseModel):
    """Ответ верификации платежа."""
    transaction_id: str = Field(..., description="ID транзакции")
    is_verified: bool = Field(..., description="Верифицирован ли платеж")
    status: str = Field(..., description="Статус платежа")
    amount: str = Field(..., description="Сумма")
    provider_data: Optional[Dict[str, Any]] = Field(None, description="Данные от провайдера")


class PaymentMethodInfo(BaseModel):
    """Информация о методе оплаты."""
    method: str = Field(..., description="Код метода")
    name: str = Field(..., description="Название метода")
    description: str = Field(..., description="Описание")
    currencies: List[str] = Field(..., description="Поддерживаемые валюты")
    min_amount: Decimal = Field(..., description="Минимальная сумма")
    max_amount: Decimal = Field(..., description="Максимальная сумма")
    fee_percentage: Decimal = Field(..., description="Комиссия в %")
    is_active: bool = Field(..., description="Активен ли метод")

    @field_serializer('min_amount', 'max_amount', 'fee_percentage')
    def serialize_amounts(self, value: Decimal) -> str:
        return f"{value:.8f}"


class PaymentMethodsResponse(BaseModel):
    """Список доступных методов оплаты."""
    methods: List[PaymentMethodInfo] = Field(..., description="Доступные методы")
    default_method: str = Field("cryptomus", description="Метод по умолчанию")


class PaymentHistoryItem(BaseModel):
    """Элемент истории платежей."""
    transaction_id: str = Field(..., description="ID транзакции")
    amount: str = Field(..., description="Сумма")
    currency: str = Field(..., description="Валюта")
    transaction_type: str = Field(..., description="Тип транзакции")
    status: str = Field(..., description="Статус")
    payment_method: str = Field(..., description="Метод оплаты")
    description: Optional[str] = Field(None, description="Описание")
    created_at: str = Field(..., description="Дата создания")
    processed_at: Optional[str] = Field(None, description="Дата обработки")


class PaymentHistoryResponse(BaseModel):
    """Ответ истории платежей."""
    transactions: List[PaymentHistoryItem] = Field(..., description="Список транзакций")
    total: int = Field(..., description="Общее количество")
    page: int = Field(..., description="Текущая страница")
    per_page: int = Field(..., description="Размер страницы")
    total_pages: int = Field(..., description="Всего страниц")


class PaymentStatsResponse(BaseModel):
    """Статистика платежей пользователя."""
    total_payments: int = Field(0, description="Общее количество платежей")
    successful_payments: int = Field(0, description="Успешные платежи")
    failed_payments: int = Field(0, description="Неудачные платежи")
    pending_payments: int = Field(0, description="Ожидающие платежи")
    total_amount: str = Field("0.00000000", description="Общая сумма")
    average_amount: str = Field("0.00000000", description="Средняя сумма")
    last_payment_date: Optional[str] = Field(None, description="Дата последнего платежа")
    preferred_method: str = Field("cryptomus", description="Предпочитаемый метод")
    period_days: int = Field(30, description="Период статистики")
    success_rate: float = Field(0.0, description="Процент успешных платежей")


# Алиас для обратной совместимости
CryptomusCallbackData = PaymentCallbackData
