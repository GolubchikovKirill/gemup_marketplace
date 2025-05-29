from pydantic import BaseModel, Field, ConfigDict, field_serializer
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
from app.models.models import ProxyType, ProxyCategory, SessionType, ProviderType


class ProductBase(BaseModel):
    """Базовая схема продукта"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    proxy_type: ProxyType
    proxy_category: ProxyCategory  # ДОБАВЛЕНО
    session_type: SessionType
    provider: ProviderType
    country_code: str = Field(..., min_length=2, max_length=2)
    country_name: str = Field(..., min_length=1, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    price_per_proxy: Decimal = Field(..., gt=0)
    price_per_gb: Optional[Decimal] = Field(None, gt=0)  # ДОБАВЛЕНО
    duration_days: int = Field(..., gt=0, le=365)


class ProductCreate(ProductBase):
    """Схема для создания продукта"""
    min_quantity: int = Field(1, ge=1, le=1000)
    max_quantity: int = Field(1000, ge=1, le=10000)
    max_threads: int = Field(1, ge=1, le=100)
    bandwidth_limit_gb: Optional[int] = Field(None, ge=1)
    uptime_guarantee: Optional[Decimal] = Field(None, ge=0, le=100)  # ДОБАВЛЕНО
    speed_mbps: Optional[int] = Field(None, ge=1)  # ДОБАВЛЕНО
    ip_pool_size: Optional[int] = Field(None, ge=1)  # ДОБАВЛЕНО
    stock_available: int = Field(0, ge=0)
    provider_product_id: Optional[str] = Field(None, max_length=255)


class ProductUpdate(BaseModel):
    """Схема для обновления продукта"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    proxy_category: Optional[ProxyCategory] = None  # ДОБАВЛЕНО
    price_per_proxy: Optional[Decimal] = Field(None, gt=0)
    price_per_gb: Optional[Decimal] = Field(None, gt=0)  # ДОБАВЛЕНО
    duration_days: Optional[int] = Field(None, gt=0, le=365)
    min_quantity: Optional[int] = Field(None, ge=1, le=1000)
    max_quantity: Optional[int] = Field(None, ge=1, le=10000)
    max_threads: Optional[int] = Field(None, ge=1, le=100)
    bandwidth_limit_gb: Optional[int] = Field(None, ge=1)
    uptime_guarantee: Optional[Decimal] = Field(None, ge=0, le=100)  # ДОБАВЛЕНО
    speed_mbps: Optional[int] = Field(None, ge=1)  # ДОБАВЛЕНО
    ip_pool_size: Optional[int] = Field(None, ge=1)  # ДОБАВЛЕНО
    stock_available: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None


class ProductResponse(ProductBase):
    """Схема ответа продукта"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    min_quantity: int
    max_quantity: int
    max_threads: int
    bandwidth_limit_gb: Optional[int]
    uptime_guarantee: Optional[Decimal]  # ДОБАВЛЕНО
    speed_mbps: Optional[int]  # ДОБАВЛЕНО
    ip_pool_size: Optional[int]  # ДОБАВЛЕНО
    stock_available: int
    is_active: bool
    is_featured: bool
    provider_product_id: Optional[str]

    # Datetime поля с правильными сериализаторами
    created_at: datetime
    updated_at: datetime

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, value: datetime) -> str:
        """Сериализация datetime в ISO строку"""
        return value.isoformat()

    @field_serializer('price_per_proxy', 'price_per_gb')
    def serialize_price(self, value: Optional[Decimal]) -> Optional[str]:
        """Сериализация Decimal в строку с 8 знаками"""
        return f"{value:.8f}" if value else None  # ИСПРАВЛЕНО: 8 знаков как в базе


class ProductListResponse(BaseModel):
    """Схема для списка продуктов с пагинацией"""
    items: List[ProductResponse]
    total: int
    page: int
    size: int
    pages: int


class ProductFilter(BaseModel):
    """Схема для фильтрации продуктов"""
    proxy_type: Optional[ProxyType] = None
    proxy_category: Optional[ProxyCategory] = None  # ДОБАВЛЕНО
    session_type: Optional[SessionType] = None
    provider: Optional[ProviderType] = None
    country_code: Optional[str] = Field(None, min_length=2, max_length=2)
    city: Optional[str] = None
    min_price: Optional[Decimal] = Field(None, ge=0)
    max_price: Optional[Decimal] = Field(None, ge=0)
    min_speed: Optional[int] = Field(None, ge=1)  # ДОБАВЛЕНО
    min_uptime: Optional[Decimal] = Field(None, ge=0, le=100)  # ДОБАВЛЕНО
    min_duration: Optional[int] = Field(None, ge=1)
    max_duration: Optional[int] = Field(None, ge=1)
    featured_only: bool = False  # ДОБАВЛЕНО для совместимости
    is_active: Optional[bool] = True
    is_featured: Optional[bool] = None
    search: Optional[str] = Field(None, max_length=100)


class CountryResponse(BaseModel):
    """Схема для списка стран"""
    code: str
    name: str
    cities: List[str] = []  # ИСПРАВЛЕНО: значение по умолчанию


class CityResponse(BaseModel):
    """Схема для списка городов"""
    name: str
    country_code: str
    country_name: str
