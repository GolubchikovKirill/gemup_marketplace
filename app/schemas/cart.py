from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, ConfigDict

from app.schemas.proxy_product import ProxyProductResponse


class CartItemBase(BaseModel):
    """Базовая схема элемента корзины"""
    proxy_product_id: int
    quantity: int = Field(..., ge=1, description="Количество товара")
    generation_params: Optional[str] = Field(None, description="Параметры генерации")


class CartItemCreate(CartItemBase):
    """Схема создания элемента корзины"""
    user_id: Optional[int] = None
    session_id: Optional[str] = None


class CartItemUpdate(BaseModel):
    """Схема обновления элемента корзины"""
    quantity: Optional[int] = Field(None, ge=1, description="Новое количество")
    generation_params: Optional[str] = Field(None, description="Обновленные параметры")


class CartItemResponse(BaseModel):
    """Схема ответа элемента корзины"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    proxy_product_id: int
    quantity: int
    generation_params: Optional[str]

    # Информация о продукте
    proxy_product: Optional[ProxyProductResponse] = None


class CartSummary(BaseModel):
    """Сводка корзины"""
    total_items: int = Field(default=0, description="Общее количество товаров")
    total_amount: str = Field(default="0.00", description="Общая сумма")
    currency: str = Field(default="USD", description="Валюта")
    items_count: int = Field(default=0, description="Количество позиций")
    items: List[Dict[str, Any]] = Field(default_factory=list, description="Детали товаров")  # ДОБАВЛЕНО


class CartResponse(BaseModel):
    """Ответ корзины"""
    cart_items: List[CartItemResponse] = Field(default_factory=list)
    summary: CartSummary = Field(default_factory=CartSummary)

# Алиасы для обратной совместимости
CartCreate = CartItemCreate
CartUpdate = CartItemUpdate