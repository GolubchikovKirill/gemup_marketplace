from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict, field_validator, ValidationInfo, field_serializer

from app.models.models import ProxyType, ProxyCategory, SessionType, ProviderType


class ProxyProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    proxy_type: ProxyType
    proxy_category: ProxyCategory
    session_type: SessionType
    provider: ProviderType
    country_code: str = Field(..., min_length=2, max_length=2)
    country_name: str = Field(..., min_length=1, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    price_per_proxy: Decimal = Field(..., gt=0)
    price_per_gb: Optional[Decimal] = Field(None, gt=0)
    min_quantity: int = Field(default=1, ge=1)
    max_quantity: int = Field(default=1000, ge=1)
    duration_days: int = Field(..., gt=0)
    max_threads: int = Field(default=1, ge=1)
    bandwidth_limit_gb: Optional[int] = Field(None, ge=1)
    uptime_guarantee: Optional[Decimal] = Field(None, ge=0, le=100)
    speed_mbps: Optional[int] = Field(None, ge=1)
    ip_pool_size: Optional[int] = Field(None, ge=1)
    # НОВЫЕ ПОЛЯ для Nodepay и Grass
    points_per_hour: Optional[int] = Field(None, ge=0, description="Очки в час для фарминга")
    farm_efficiency: Optional[Decimal] = Field(None, ge=0, le=100, description="Эффективность фарминга в %")
    auto_claim: bool = Field(default=False, description="Автоматический клейм")
    multi_account_support: bool = Field(default=False, description="Поддержка мульти-аккаунтов")

    @field_validator('country_code')
    @classmethod
    def country_code_uppercase(cls, v: str) -> str:
        return v.upper()

    @field_validator('max_quantity')
    @classmethod
    def max_quantity_gte_min_quantity(cls, v: int, info: ValidationInfo) -> int:
        if 'min_quantity' in info.data and v < info.data['min_quantity']:
            raise ValueError('max_quantity must be greater than or equal to min_quantity')
        return v


class ProxyProductCreate(ProxyProductBase):
    stock_available: int = Field(default=0, ge=0)
    is_featured: bool = Field(default=False)
    provider_product_id: Optional[str] = None
    provider_metadata: Optional[str] = None


class ProxyProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    proxy_category: Optional[ProxyCategory] = None
    price_per_proxy: Optional[Decimal] = Field(None, gt=0)
    price_per_gb: Optional[Decimal] = Field(None, gt=0)
    min_quantity: Optional[int] = Field(None, ge=1)
    max_quantity: Optional[int] = Field(None, ge=1)
    duration_days: Optional[int] = Field(None, gt=0)
    max_threads: Optional[int] = Field(None, ge=1)
    bandwidth_limit_gb: Optional[int] = Field(None, ge=1)
    uptime_guarantee: Optional[Decimal] = Field(None, ge=0, le=100)
    speed_mbps: Optional[int] = Field(None, ge=1)
    ip_pool_size: Optional[int] = Field(None, ge=1)
    # НОВЫЕ ПОЛЯ для обновления
    points_per_hour: Optional[int] = Field(None, ge=0)
    farm_efficiency: Optional[Decimal] = Field(None, ge=0, le=100)
    auto_claim: Optional[bool] = None
    multi_account_support: Optional[bool] = None
    stock_available: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    provider_metadata: Optional[str] = None


class ProxyProductResponse(ProxyProductBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    stock_available: int
    is_active: bool
    is_featured: bool
    provider_product_id: Optional[str]
    provider_metadata: Optional[str]
    created_at: datetime
    updated_at: datetime

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, value: datetime) -> str:
        """Сериализация datetime в ISO строку"""
        return value.isoformat()

    @field_serializer('price_per_proxy', 'price_per_gb', 'uptime_guarantee', 'farm_efficiency')
    def serialize_decimal(self, value: Optional[Decimal]) -> Optional[str]:
        """Сериализация Decimal в строку с 8 знаками"""
        return f"{value:.8f}" if value else None


class ProxyProductPublic(BaseModel):
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
    city: Optional[str]
    price_per_proxy: Decimal
    price_per_gb: Optional[Decimal]
    min_quantity: int
    max_quantity: int
    duration_days: int
    max_threads: int
    bandwidth_limit_gb: Optional[int]
    uptime_guarantee: Optional[Decimal]
    speed_mbps: Optional[int]
    ip_pool_size: Optional[int]
    # НОВЫЕ ПОЛЯ для публичного API
    points_per_hour: Optional[int]
    farm_efficiency: Optional[Decimal]
    auto_claim: bool
    multi_account_support: bool
    is_featured: bool
    stock_available: int

    @field_serializer('price_per_proxy', 'price_per_gb', 'uptime_guarantee', 'farm_efficiency')
    def serialize_decimal(self, value: Optional[Decimal]) -> Optional[str]:
        """Сериализация Decimal в строку с 8 знаками"""
        return f"{value:.8f}" if value else None


class ProductFilter(BaseModel):
    """Фильтр для поиска продуктов"""
    proxy_type: Optional[ProxyType] = None
    proxy_category: Optional[ProxyCategory] = None
    session_type: Optional[SessionType] = None
    provider: Optional[ProviderType] = None
    country_code: Optional[str] = None
    city: Optional[str] = None
    featured_only: bool = False
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    min_speed: Optional[int] = None
    min_uptime: Optional[Decimal] = None
    min_duration: Optional[int] = None
    max_duration: Optional[int] = None
    # НОВЫЕ ФИЛЬТРЫ для фарминга
    min_points_per_hour: Optional[int] = Field(None, ge=0, description="Минимум очков в час")
    min_farm_efficiency: Optional[Decimal] = Field(None, ge=0, le=100, description="Минимальная эффективность фарминга")
    auto_claim_only: Optional[bool] = Field(None, description="Только с автоклеймом")
    multi_account_only: Optional[bool] = Field(None, description="Только с поддержкой мульти-аккаунтов")
    search: Optional[str] = None


class ProductListResponse(BaseModel):
    """Ответ со списком продуктов"""
    items: List[ProxyProductPublic]
    total: int
    page: int
    size: int
    pages: int


class CountryResponse(BaseModel):
    """Ответ со странами"""
    code: str
    name: str
    cities: List[str] = []


class CityResponse(BaseModel):
    """Ответ с городами"""
    name: str
    country_code: str
    country_name: str


class CountryInfo(BaseModel):
    code: str
    name: str


class ProxyGenerationParams(BaseModel):
    format_type: str = Field(default="ip:port:user:pass", description="Формат вывода прокси")
    include_auth: bool = Field(default=True, description="Включить авторизацию в список")
    separator: str = Field(default="\n", description="Разделитель между прокси")


class ProxyProductFilters(ProductFilter):
    """Алиас для обратной совместимости"""
    pass
