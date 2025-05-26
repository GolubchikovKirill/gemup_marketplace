from pydantic import BaseModel, Field, ConfigDict, field_serializer
from typing import Optional, List
from decimal import Decimal
from datetime import datetime

class CartItemBase(BaseModel):
    """Базовая схема элемента корзины"""
    proxy_product_id: int = Field(..., description="ID продукта")
    quantity: int = Field(..., ge=1, le=1000, description="Количество")
    generation_params: Optional[str] = Field(None, description="Параметры генерации (JSON)")

class CartItemCreate(CartItemBase):
    """Схема для добавления в корзину"""
    user_id: Optional[int] = Field(None, description="ID пользователя (для зарегистрированных)")
    session_id: Optional[str] = Field(None, description="ID сессии (для гостей)")

class CartItemUpdate(BaseModel):
    """Схема для обновления элемента корзины"""
    quantity: int = Field(..., ge=1, le=1000, description="Новое количество")
    generation_params: Optional[str] = Field(None, description="Параметры генерации")

class CartItemResponse(CartItemBase):
    """Схема ответа элемента корзины"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: Optional[int]
    session_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime]
    
    # Информация о продукте (будет добавлена в сервисе)
    product: Optional[dict] = None
    
    @field_serializer('created_at', 'updated_at', 'expires_at')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        """Сериализация datetime в ISO строку"""
        return value.isoformat() if value else None

class CartSummary(BaseModel):
    """Сводка по корзине"""
    items: List[dict]
    total_items: int
    total_amount: Decimal
    currency: str = "USD"
    
    @field_serializer('total_amount')
    def serialize_amount(self, value: Decimal) -> str:
        return f"{value:.2f}"

class CartResponse(BaseModel):
    """Полный ответ корзины"""
    cart_items: List[CartItemResponse]
    summary: CartSummary

# Алиасы для совместимости
CartCreate = CartItemCreate
CartUpdate = CartItemUpdate
