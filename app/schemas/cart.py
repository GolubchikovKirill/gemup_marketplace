"""
Схемы для корзины покупок.

Содержит все схемы для работы с корзиной пользователей,
поддерживает как зарегистрированных, так и гостевых пользователей.
"""

from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict, field_serializer, field_validator

from app.schemas.proxy_product import ProxyProductPublic


class CartItemBase(BaseModel):
    """
    Базовая схема элемента корзины.

    Содержит основные поля для работы с товарами в корзине.
    """
    proxy_product_id: int = Field(..., gt=0, description="ID продукта прокси")
    quantity: int = Field(..., ge=1, le=1000, description="Количество товара")
    generation_params: Optional[str] = Field(None, max_length=1000, description="Параметры генерации прокси")

    @field_validator('quantity')
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        """Валидация количества."""
        if v <= 0:
            raise ValueError('Quantity must be positive')
        if v > 1000:
            raise ValueError('Quantity cannot exceed 1000')
        return v


class CartItemCreate(CartItemBase):
    """
    Схема создания элемента корзины.

    Используется при добавлении товара в корзину.
    """
    # Эти поля будут определяться автоматически на основе текущего пользователя/сессии
    pass


class CartItemUpdate(BaseModel):
    """
    Схема обновления элемента корзины.

    Позволяет изменить количество товара или параметры генерации.
    """
    quantity: Optional[int] = Field(None, ge=1, le=1000, description="Новое количество")
    generation_params: Optional[str] = Field(None, max_length=1000, description="Обновленные параметры")

    @field_validator('quantity')
    @classmethod
    def validate_quantity(cls, v: Optional[int]) -> Optional[int]:
        """Валидация количества."""
        if v is not None:
            if v <= 0:
                raise ValueError('Quantity must be positive')
            if v > 1000:
                raise ValueError('Quantity cannot exceed 1000')
        return v


class CartItemResponse(BaseModel):
    """
    Схема ответа элемента корзины.

    Содержит полную информацию об элементе корзины включая данные продукта.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[int] = None
    guest_session_id: Optional[str] = None
    proxy_product_id: int
    quantity: int
    generation_params: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    # Информация о продукте (если загружена)
    proxy_product: Optional[ProxyProductPublic] = Field(None, description="Данные продукта")

    # Вычисляемые поля
    unit_price: Optional[Decimal] = Field(None, description="Цена за единицу")
    total_price: Optional[Decimal] = Field(None, description="Общая стоимость позиции")
    is_available: bool = Field(True, description="Доступен ли товар")
    stock_status: str = Field("in_stock", description="Статус наличия")

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
    total_amount: str = Field("0.00000000", description="Общая сумма корзины")
    currency: str = Field("USD", description="Валюта")
    items_count: int = Field(0, ge=0, description="Количество уникальных позиций")
    user_type: str = Field("guest", description="Тип пользователя")

    # Дополнительная информация
    estimated_delivery: str = Field("Immediate", description="Примерное время доставки")
    has_nodepay_products: bool = Field(False, description="Есть ли продукты NodePay")
    has_proxy_products: bool = Field(False, description="Есть ли обычные прокси")
    has_unavailable_items: bool = Field(False, description="Есть ли недоступные товары")

    # Статистика по категориям
    categories_breakdown: Dict[str, int] = Field(default_factory=dict, description="Разбивка по категориям")
    countries_breakdown: Dict[str, int] = Field(default_factory=dict, description="Разбивка по странам")


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
    is_guest: bool = Field(True, description="Гостевая корзина")

    @field_serializer('last_updated', 'expires_at')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None


class CartSummaryResponse(BaseModel):
    """
    Краткая сводка корзины.

    Используется для быстрого получения основной информации о корзине.
    """
    items_count: int = Field(0, ge=0, description="Количество различных товаров")
    total_quantity: int = Field(0, ge=0, description="Общее количество товаров")
    total_amount: str = Field("0.00000000", description="Итоговая сумма")
    currency: str = Field("USD", description="Валюта")
    last_updated: Optional[str] = Field(None, description="Время последнего обновления")
    user_type: str = Field("guest", description="Тип пользователя")
    has_unavailable_items: bool = Field(False, description="Есть ли недоступные товары")


class AddToCartRequest(BaseModel):
    """
    Запрос добавления товара в корзину.

    Используется в API endpoint для добавления товаров.
    """
    proxy_product_id: int = Field(..., gt=0, description="ID продукта")
    quantity: int = Field(1, ge=1, le=1000, description="Количество")
    generation_params: Optional[str] = Field(None, max_length=1000, description="Параметры генерации")
    replace_if_exists: bool = Field(False, description="Заменить если товар уже в корзине")

    @field_validator('quantity')
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        """Валидация количества."""
        if v <= 0:
            raise ValueError('Quantity must be positive')
        return v


class UpdateCartItemRequest(BaseModel):
    """
    Запрос обновления элемента корзины.
    """
    quantity: int = Field(..., ge=1, le=1000, description="Новое количество")
    generation_params: Optional[str] = Field(None, max_length=1000, description="Параметры генерации")

    @field_validator('quantity')
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        """Валидация количества."""
        if v <= 0:
            raise ValueError('Quantity must be positive')
        return v


class BulkCartOperation(BaseModel):
    """
    Схема для массовых операций с корзиной.
    """
    item_ids: List[int] = Field(..., min_length=1, max_length=100, description="Список ID элементов корзины")
    operation: Literal["delete", "update_quantity", "clear"] = Field(..., description="Тип операции")
    quantity: Optional[int] = Field(None, ge=1, le=1000, description="Количество (для update_quantity)")

    @field_validator('item_ids')
    @classmethod
    def validate_item_ids(cls, v: List[int]) -> List[int]:
        """Валидация ID элементов."""
        if len(set(v)) != len(v):
            raise ValueError('Duplicate item IDs are not allowed')
        return v

    @field_validator('quantity')
    @classmethod
    def validate_quantity(cls, v: Optional[int], info) -> Optional[int]:
        """Валидация количества для операции обновления."""
        operation = info.data.get('operation')
        if operation == 'update_quantity' and v is None:
            raise ValueError('Quantity is required for update_quantity operation')
        return v


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
    inactive_items: List[Dict[str, Any]] = Field(default_factory=list, description="Неактивные товары")

    # Сводная информация
    total_valid_items: int = Field(0, description="Количество валидных товаров")
    total_invalid_items: int = Field(0, description="Количество невалидных товаров")
    estimated_total: str = Field("0.00000000", description="Примерная общая стоимость")


class CartMergeRequest(BaseModel):
    """
    Запрос объединения корзин.
    """
    guest_session_id: str = Field(..., min_length=1, description="ID гостевой сессии")
    merge_strategy: Literal["add", "replace", "skip_duplicates"] = Field(
        "add", description="Стратегия объединения"
    )


class CartMergeResponse(BaseModel):
    """
    Результат объединения корзин.
    """
    success: bool = Field(..., description="Успешность операции")
    merged_items: int = Field(0, description="Количество объединенных элементов")
    conflicts: List[Dict[str, Any]] = Field(default_factory=list, description="Конфликты при объединении")
    message: str = Field("", description="Сообщение о результате")


class CartExportRequest(BaseModel):
    """
    Запрос экспорта корзины.
    """
    format: Literal["json", "csv"] = Field("json", description="Формат экспорта")
    include_product_details: bool = Field(True, description="Включать детали продуктов")
    include_pricing: bool = Field(True, description="Включать информацию о ценах")


class CartExportResponse(BaseModel):
    """
    Результат экспорта корзины.
    """
    format: str = Field(..., description="Формат экспорта")
    data: str = Field(..., description="Экспортированные данные")
    filename: str = Field(..., description="Предлагаемое имя файла")
    size_bytes: int = Field(..., description="Размер данных в байтах")


class CartStatsResponse(BaseModel):
    """
    Статистика корзин.
    """
    total_active_carts: int = Field(0, description="Общее количество активных корзин")
    total_items: int = Field(0, description="Общее количество товаров")
    user_carts: int = Field(0, description="Корзины зарегистрированных пользователей")
    guest_carts: int = Field(0, description="Гостевые корзины")
    average_items_per_cart: float = Field(0.0, description="Среднее количество товаров в корзине")
    average_cart_value: str = Field("0.00000000", description="Средняя стоимость корзины")
    period_days: int = Field(30, description="Период статистики в днях")

    # Топ продуктов
    top_products: List[Dict[str, Any]] = Field(default_factory=list, description="Популярные продукты")
    conversion_rate: float = Field(0.0, description="Коэффициент конверсии корзина->заказ")


class CartItemWithProduct(CartItemResponse):
    """
    Элемент корзины с обязательной информацией о продукте.
    """
    proxy_product: ProxyProductPublic = Field(..., description="Данные продукта")


class CartChangesResponse(BaseModel):
    """
    Информация об изменениях в корзине.
    """
    price_changes: List[Dict[str, Any]] = Field(default_factory=list, description="Изменения цен")
    availability_changes: List[Dict[str, Any]] = Field(default_factory=list, description="Изменения доступности")
    stock_changes: List[Dict[str, Any]] = Field(default_factory=list, description="Изменения остатков")
    total_changes: int = Field(0, description="Общее количество изменений")


class DiscountCodeRequest(BaseModel):
    """
    Запрос применения промокода.
    """
    discount_code: str = Field(..., min_length=1, max_length=50, description="Промокод")


class DiscountCodeResponse(BaseModel):
    """
    Результат применения промокода.
    """
    is_valid: bool = Field(..., description="Валиден ли промокод")
    message: str = Field(..., description="Сообщение о результате")
    discount_amount: str = Field("0.00000000", description="Сумма скидки")
    discount_percentage: int = Field(0, description="Процент скидки")


class ShippingEstimateRequest(BaseModel):
    """
    Запрос расчета доставки.
    """
    country_code: Optional[str] = Field(None, description="Код страны")
    postal_code: Optional[str] = Field(None, description="Почтовый индекс")
    shipping_method: Optional[str] = Field(None, description="Способ доставки")


class ShippingEstimateResponse(BaseModel):
    """
    Результат расчета доставки.
    """
    shipping_required: bool = Field(False, description="Требуется ли доставка")
    shipping_cost: str = Field("0.00000000", description="Стоимость доставки")
    delivery_time: str = Field("Instant", description="Время доставки")
    message: str = Field("", description="Дополнительная информация")


# Создаем алиасы для обратной совместимости
ShoppingCartBase = CartItemBase
ShoppingCartCreate = CartItemCreate
ShoppingCartUpdate = CartItemUpdate
ShoppingCartItemResponse = CartItemResponse
ShoppingCartResponse = CartResponse
