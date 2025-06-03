"""
Схемы для платежных операций.

Определяет структуры данных для запросов и ответов
связанных с платежами и транзакциями.
"""

from typing import Optional
from pydantic import BaseModel, Field


class PaymentCreateRequest(BaseModel):
    """
    Схема запроса создания платежа.

    Используется для создания нового платежа для пополнения баланса.
    Валюта фиксирована как USD в системе.
    """
    amount: float = Field(
        ...,
        gt=0,
        le=10000,
        description="Сумма платежа в USD",
        example=50.00
    )
    description: Optional[str] = Field(
        None,
        max_length=255,
        description="Описание платежа",
        example="Пополнение баланса"
    )


class PaymentResponse(BaseModel):
    """
    Схема ответа с данными созданного платежа.

    Содержит всю необходимую информацию для перенаправления
    пользователя на страницу оплаты.
    """
    transaction_id: str = Field(
        ...,
        description="Уникальный идентификатор транзакции",
        example="TXN-20240315-ABC123"
    )
    payment_url: str = Field(
        ...,
        description="URL для перехода к оплате",
        example="https://pay.cryptomus.com/pay/abc123"
    )
    amount: str = Field(
        ...,
        description="Сумма платежа",
        example="50.00"
    )
    currency: str = Field(
        default="USD",
        description="Валюта платежа",
        example="USD"
    )
    status: str = Field(
        ...,
        description="Статус платежа",
        example="pending"
    )
    expires_in: Optional[int] = Field(
        None,
        description="Время жизни платежа в секундах",
        example=3600
    )


class PaymentStatusResponse(BaseModel):
    """
    Схема ответа со статусом платежа.

    Используется для получения актуальной информации
    о состоянии платежа.
    """
    transaction_id: str = Field(
        ...,
        description="Идентификатор транзакции",
        example="TXN-20240315-ABC123"
    )
    amount: str = Field(
        ...,
        description="Сумма платежа",
        example="50.00"
    )
    currency: str = Field(
        ...,
        description="Валюта платежа",
        example="USD"
    )
    status: str = Field(
        ...,
        description="Текущий статус платежа",
        example="completed"
    )
    created_at: str = Field(
        ...,
        description="Дата и время создания платежа",
        example="2024-03-15T10:30:00Z"
    )
    updated_at: str = Field(
        ...,
        description="Дата и время последнего обновления",
        example="2024-03-15T10:45:00Z"
    )


class PaymentMethodResponse(BaseModel):
    """Схема информации о методе оплаты"""
    id: str = Field(..., description="Идентификатор метода")
    name: str = Field(..., description="Название метода")
    description: str = Field(..., description="Описание метода")
    currencies: list[str] = Field(..., description="Поддерживаемые валюты")
    min_amount: float = Field(..., description="Минимальная сумма")
    max_amount: float = Field(..., description="Максимальная сумма")


class PaymentCallbackData(BaseModel):
    """Схема данных callback от платежной системы"""
    order_id: str = Field(..., description="ID заказа")
    transaction_id: str = Field(..., description="ID транзакции")
    status: str = Field(..., description="Статус платежа")
    amount: str = Field(..., description="Сумма")
    currency: str = Field(..., description="Валюта")
    signature: Optional[str] = Field(None, description="Подпись безопасности")
