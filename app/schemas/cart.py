"""
Схемы для корзины покупок.

Содержит все схемы для работы с корзиной пользователей,
поддерживает как зарегистрированных, так и гостевых пользователей.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict, field_serializer

from app.schemas.proxy_product import ProxyProductPublic


class CartItemBase(BaseModel):
    """
    Базовая схема элемента корзины.

    Содержит основные поля для работы с товарами в корзине.
    """
    proxy_product_id: int = Field(..., gt=0, description="ID продукта прокси")
    quantity: int = Field(..., ge=1, le=1000, description="Количество товара")
    generation_params: Optional[str] = Field(None, max_length=500, description="Параметры генерации прокси")


class CartItemCreate(CartItemBase):
    """
    Схема создания элемента корзины.

    Используется при добавлении товара в корзину.
    """
    user_id: Optional[int] = Field(None, description="ID пользователя (для зарегистрированных)")
    guest_session_id: Optional[str] = Field(None, max_length=255, description="ID сессии (для гостей)")


class CartItemUpdate(BaseModel):
    """
    Схема обновления элемента корзины.

    Позволяет изменить количество товара или параметры генерации.
    """
    quantity: Optional[int] = Field(None, ge=1, le=1000, description="Новое количество")
    generation_params: Optional[str] = Field(None, max_length=500, description="Обновленные параметры")


class CartItemResponse(BaseModel):
    """
    Схема ответа элемента корзины.

    Содержит полную информацию об элементе корзины включая данные продукта.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    proxy_product_id: int
    quantity: int
    generation_params: Optional[str]

    # Временные метки
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime]

    # Информация о продукте
    proxy_product: Optional[ProxyProductPublic] = Field(None, description="Данные продукта")

    # Вычисляемые поля
    unit_price: Optional[Decimal] = Field(None, description="Цена за единицу")
    total_price: Optional[Decimal] = Field(None, description="Общая стоимость позиции")

    @field_serializer('created_at', 'updated_at', 'expires_at')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        """Сериализация datetime в ISO формат."""
        return value.isoformat() if value else None

    @field_serializer('unit_price', 'total_price')
    def serialize_price(self, value: Optional[Decimal]) -> Optional[str]:
        """Сериализация цен."""
        return f"{value:.8f}" if value is not None else None


class CartSummary(BaseModel):
    """
    Сводка корзины.

    Содержит агрегированную информацию о содержимом корзины.
    """
    total_items: int = Field(0, ge=0, description="Общее количество товаров")
    total_amount: str = Field("0.00", description="Общая сумма корзины")
    currency: str = Field("USD", description="Валюта")
    items_count: int = Field(0, ge=0, description="Количество уникальных позиций")
    user_type: str = Field("guest", description="Тип пользователя")

    # Дополнительная информация
    estimated_delivery: Optional[str] = Field(None, description="Примерное время доставки")
    has_farming_products: bool = Field(False, description="Есть ли продукты для фарминга")
    has_proxy_products: bool = Field(False, description="Есть ли обычные прокси")


class CartResponse(BaseModel):
    """
    Полный ответ корзины.

    Содержит список товаров и сводную информацию.
    """
    items: List[CartItemResponse] = Field(default_factory=list, description="Элементы корзины")
    summary: CartSummary = Field(default_factory=CartSummary, description="Сводка корзины")

    # Метаданные
    last_updated: Optional[datetime] = Field(None, description="Последнее обновление корзины")
    expires_at: Optional[datetime] = Field(None, description="Срок истечения корзины")

    @field_serializer('last_updated', 'expires_at')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None


class AddToCartRequest(BaseModel):
    """
    Запрос добавления товара в корзину.

    Используется в API endpoint для добавления товаров.
    """
    proxy_product_id: int = Field(..., gt=0, description="ID продукта")
    quantity: int = Field(1, ge=1, le=1000, description="Количество")
    generation_params: Optional[str] = Field(None, max_length=500, description="Параметры генерации")

    # Опциональные параметры
    replace_if_exists: bool = Field(False, description="Заменить если товар уже в корзине")


class UpdateCartItemRequest(BaseModel):
    """
    Запрос обновления элемента корзины.
    """
    quantity: int = Field(..., ge=1, le=1000, description="Новое количество")
    generation_params: Optional[str] = Field(None, max_length=500, description="Параметры генерации")


class BulkCartOperation(BaseModel):
    """
    Схема для массовых операций с корзиной.
    """
    item_ids: List[int] = Field(..., min_length=1, description="Список ID элементов корзины")
    operation: str = Field(..., pattern="^(delete|update_quantity)$", description="Тип операции")
    quantity: Optional[int] = Field(None, ge=1, le=1000, description="Количество (для update_quantity)")


class CartValidationResponse(BaseModel):
    """
    Результат валидации корзины.

    Используется для проверки корзины перед оформлением заказа.
    """
    is_valid: bool = Field(..., description="Корзина валидна")
    errors: List[str] = Field(default_factory=list, description="Список ошибок")
    warnings: List[str] = Field(default_factory=list, description="Предупреждения")

    # Детальная информация об ошибках
    invalid_items: List[Dict[str, Any]] = Field(default_factory=list, description="Невалидные товары")
    out_of_stock_items: List[Dict[str, Any]] = Field(default_factory=list, description="Товары не в наличии")
    price_changed_items: List[Dict[str, Any]] = Field(default_factory=list, description="Товары с изменившейся ценой")


# Создаем алиасы для обратной совместимости
ShoppingCartBase = CartItemBase
ShoppingCartCreate = CartItemCreate
ShoppingCartUpdate = CartItemUpdate
ShoppingCartItemResponse = CartItemResponse
ShoppingCartResponse = CartResponse
