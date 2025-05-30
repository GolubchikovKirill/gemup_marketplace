from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, field_serializer

from app.models.models import ProxyType, ProxyCategory, SessionType, ProviderType


class ProductFilter(BaseModel):
    """Фильтр для поиска продуктов"""
    search: Optional[str] = None
    proxy_category: Optional[ProxyCategory] = None
    proxy_type: Optional[ProxyType] = None
    provider: Optional[ProviderType] = None
    country: Optional[str] = None  # ИСПРАВЛЕНО: добавлен атрибут country
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_points_per_hour: Optional[int] = None
    auto_claim_only: Optional[bool] = None
    min_farm_efficiency: Optional[float] = None
    multi_account_only: Optional[bool] = None
    min_speed: Optional[int] = None  # ДОБАВЛЕНО: для фильтрации по скорости
    min_uptime: Optional[float] = None  # ДОБАВЛЕНО: для фильтрации по uptime
    sort: Optional[str] = "created_at_desc"


class ProxyProductBase(BaseModel):
    """Базовая схема продукта прокси"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    proxy_type: ProxyType
    proxy_category: ProxyCategory
    session_type: SessionType
    provider: ProviderType
    country_code: str = Field(..., min_length=2, max_length=3)
    country_name: str = Field(..., min_length=1, max_length=100)
    price_per_proxy: Decimal = Field(..., gt=0)
    price_per_gb: Optional[Decimal] = Field(None, gt=0)
    duration_days: int = Field(..., gt=0)
    min_quantity: Optional[int] = Field(1, gt=0)
    max_quantity: Optional[int] = Field(100, gt=0)
    stock_available: int = Field(0, ge=0)
    speed_mbps: Optional[int] = Field(None, gt=0)
    uptime_guarantee: Optional[Decimal] = Field(None, ge=0, le=100)
    ip_pool_size: Optional[int] = Field(None, gt=0)
    points_per_hour: Optional[int] = Field(None, ge=0)
    farm_efficiency: Optional[Decimal] = Field(None, ge=0, le=100)
    auto_claim: Optional[bool] = None
    multi_account_support: Optional[bool] = None
    is_active: bool = Field(default=True)


class ProxyProductCreate(ProxyProductBase):
    """Схема создания продукта прокси"""
    pass


class ProxyProductUpdate(BaseModel):
    """Схема обновления продукта прокси"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    price_per_proxy: Optional[Decimal] = Field(None, gt=0)
    price_per_gb: Optional[Decimal] = Field(None, gt=0)
    duration_days: Optional[int] = Field(None, gt=0)
    min_quantity: Optional[int] = Field(None, gt=0)
    max_quantity: Optional[int] = Field(None, gt=0)
    stock_available: Optional[int] = Field(None, ge=0)
    speed_mbps: Optional[int] = Field(None, gt=0)
    uptime_guarantee: Optional[Decimal] = Field(None, ge=0, le=100)
    ip_pool_size: Optional[int] = Field(None, gt=0)
    points_per_hour: Optional[int] = Field(None, ge=0)
    farm_efficiency: Optional[Decimal] = Field(None, ge=0, le=100)
    auto_claim: Optional[bool] = None
    multi_account_support: Optional[bool] = None
    is_active: Optional[bool] = None


class ProxyProductResponse(BaseModel):
    """Схема ответа продукта прокси"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str]
    proxy_type: ProxyType
    proxy_category: ProxyCategory
    session_type: SessionType
    provider: ProviderType
    country_code: str
    country_name: str
    price_per_proxy: Decimal
    price_per_gb: Optional[Decimal]
    duration_days: int
    min_quantity: Optional[int]
    max_quantity: Optional[int]
    stock_available: int
    speed_mbps: Optional[int]
    uptime_guarantee: Optional[Decimal]
    ip_pool_size: Optional[int]
    points_per_hour: Optional[int]
    farm_efficiency: Optional[Decimal]
    auto_claim: Optional[bool]
    multi_account_support: Optional[bool]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @field_serializer('price_per_proxy', 'price_per_gb', 'uptime_guarantee', 'farm_efficiency')
    def serialize_decimal(self, value: Optional[Decimal]) -> Optional[str]:
        return f"{value:.8f}" if value is not None else None

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()


class ProxyProductPublic(BaseModel):
    """Публичная схема продукта прокси (без чувствительных данных)"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str]
    proxy_type: ProxyType
    proxy_category: ProxyCategory
    country_code: str
    country_name: str
    price_per_proxy: Decimal
    duration_days: int
    points_per_hour: Optional[int]
    farm_efficiency: Optional[Decimal]
    auto_claim: Optional[bool]
    multi_account_support: Optional[bool]

    @field_serializer('price_per_proxy', 'farm_efficiency')
    def serialize_decimal(self, value: Optional[Decimal]) -> Optional[str]:
        return f"{value:.2f}" if value is not None else None


class ProductListResponse(BaseModel):
    """Ответ со списком продуктов"""
    items: List[ProxyProductResponse]
    total: int
    page: int
    size: int
    pages: int


class ProductsByCategoryResponse(BaseModel):
    """Ответ с продуктами по категории"""
    category: str
    products: List[ProxyProductResponse]
    page: int
    size: int
    total: int
