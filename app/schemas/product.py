from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from decimal import Decimal
from app.models.models import ProxyType, SessionType, ProviderType


class ProductBase(BaseModel):
    """Базовая схема продукта"""
    name: str = Field(..., min_length=1, max_length=200, description="Название продукта")
    description: Optional[str] = Field(None, max_length=1000, description="Описание продукта")
    proxy_type: ProxyType = Field(..., description="Тип прокси")
    session_type: SessionType = Field(..., description="Тип сессии")
    provider: ProviderType = Field(..., description="Провайдер")
    country_code: str = Field(..., min_length=2, max_length=2, description="Код страны (ISO)")
    country_name: str = Field(..., min_length=1, max_length=100, description="Название страны")
    city: Optional[str] = Field(None, max_length=100, description="Город")
    price_per_proxy: Decimal = Field(..., gt=0, description="Цена за прокси")
    duration_days: int = Field(..., gt=0, le=365, description="Срок действия в днях")


class ProductCreate(ProductBase):
    """Схема для создания продукта"""
    min_quantity: int = Field(1, ge=1, le=1000, description="Минимальное количество")
    max_quantity: int = Field(1000, ge=1, le=10000, description="Максимальное количество")
    max_threads: int = Field(1, ge=1, le=100, description="Максимальное количество потоков")
    bandwidth_limit_gb: Optional[int] = Field(None, ge=1, description="Лимит трафика в ГБ")
    stock_available: int = Field(0, ge=0, description="Доступное количество")
    provider_product_id: Optional[str] = Field(None, max_length=255, description="ID в системе провайдера")


class ProductUpdate(BaseModel):
    """Схема для обновления продукта"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    price_per_proxy: Optional[Decimal] = Field(None, gt=0)
    duration_days: Optional[int] = Field(None, gt=0, le=365)
    min_quantity: Optional[int] = Field(None, ge=1, le=1000)
    max_quantity: Optional[int] = Field(None, ge=1, le=10000)
    max_threads: Optional[int] = Field(None, ge=1, le=100)
    bandwidth_limit_gb: Optional[int] = Field(None, ge=1)
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
    stock_available: int
    is_active: bool
    is_featured: bool
    provider_product_id: Optional[str]
    created_at: str
    updated_at: str


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
    session_type: Optional[SessionType] = None
    provider: Optional[ProviderType] = None
    country_code: Optional[str] = Field(None, min_length=2, max_length=2)
    city: Optional[str] = Field(None, max_length=100)
    min_price: Optional[Decimal] = Field(None, ge=0)
    max_price: Optional[Decimal] = Field(None, ge=0)
    min_duration: Optional[int] = Field(None, ge=1)
    max_duration: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = True
    is_featured: Optional[bool] = None
    search: Optional[str] = Field(None, max_length=100, description="Поиск по названию")


class CountryResponse(BaseModel):
    """Схема для списка стран"""
    code: str
    name: str
    cities: List[str]


class CityResponse(BaseModel):
    """Схема для списка городов"""
    name: str
    country_code: str
    country_name: str
