"""
Схемы для продуктов прокси - дополнено недостающими схемами для CRUD.

Содержит все схемы для работы с каталогом продуктов прокси,
включая фильтрацию, поиск, статистику и массовые операции.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, ConfigDict, field_validator, field_serializer

from app.models.models import ProxyType, ProxyCategory, ProviderType, SessionType


class ProxyProductBase(BaseModel):
    """Базовая схема продукта прокси."""
    name: str = Field(..., min_length=1, max_length=255, description="Название продукта")
    description: Optional[str] = Field(None, description="Описание продукта")
    proxy_type: ProxyType = Field(..., description="Тип прокси")
    proxy_category: ProxyCategory = Field(..., description="Категория прокси")
    provider: ProviderType = Field(..., description="Провайдер")
    country_code: str = Field(..., min_length=2, max_length=2, description="Код страны")
    country_name: str = Field(..., description="Название страны")
    city: Optional[str] = Field(None, description="Город")
    price_per_proxy: Decimal = Field(..., gt=0, description="Цена за прокси")
    duration_days: int = Field(..., gt=0, description="Длительность в днях")


class ProxyProductCreate(ProxyProductBase):
    """Схема создания продукта прокси."""
    session_type: SessionType = Field(..., description="Тип сессии")
    min_quantity: int = Field(1, ge=1, description="Минимальное количество")
    max_quantity: int = Field(1000, ge=1, description="Максимальное количество")
    stock_available: int = Field(0, ge=0, description="Доступно в наличии")
    max_threads: Optional[int] = Field(None, description="Максимальное количество потоков")
    bandwidth_limit_gb: Optional[Decimal] = Field(None, description="Лимит трафика в ГБ")
    uptime_guarantee: Optional[Decimal] = Field(None, description="Гарантия аптайма")
    speed_mbps: Optional[int] = Field(None, description="Скорость в Мбит/с")


class ProxyProductUpdate(BaseModel):
    """Схема обновления продукта прокси."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    price_per_proxy: Optional[Decimal] = Field(None, gt=0)
    stock_available: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    max_threads: Optional[int] = None
    bandwidth_limit_gb: Optional[Decimal] = None
    uptime_guarantee: Optional[Decimal] = None
    speed_mbps: Optional[int] = None


class ProxyProductResponse(BaseModel):
    """Схема ответа продукта прокси."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    proxy_type: ProxyType
    proxy_category: ProxyCategory
    session_type: SessionType
    provider: ProviderType
    country_code: str
    country_name: str
    city: Optional[str] = None
    price_per_proxy: Decimal
    duration_days: int
    min_quantity: int
    max_quantity: int
    stock_available: int
    max_threads: Optional[int] = None
    bandwidth_limit_gb: Optional[Decimal] = None
    uptime_guarantee: Optional[Decimal] = None
    speed_mbps: Optional[int] = None
    is_active: bool
    is_featured: bool
    created_at: datetime
    updated_at: datetime

    @field_serializer('price_per_proxy', 'bandwidth_limit_gb', 'uptime_guarantee')
    def serialize_decimal(self, value: Optional[Decimal]) -> Optional[str]:
        return f"{value:.2f}" if value is not None else None

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()


class ProxyProductPublic(BaseModel):
    """Публичная схема продукта прокси (без служебной информации)."""
    id: int
    name: str
    description: Optional[str] = None
    proxy_type: ProxyType
    proxy_category: ProxyCategory
    session_type: SessionType
    country_code: str
    country_name: str
    city: Optional[str] = None
    price_per_proxy: str
    duration_days: int
    min_quantity: int
    max_quantity: int
    stock_available: int
    max_threads: Optional[int] = None
    speed_mbps: Optional[int] = None
    uptime_guarantee: Optional[str] = None
    is_featured: bool

    @field_serializer('price_per_proxy', 'uptime_guarantee')
    def serialize_decimal_fields(self, value) -> str:
        if isinstance(value, Decimal):
            return f"{value:.2f}"
        return str(value) if value is not None else "0.00"


class ProductFilter(BaseModel):
    """Схема фильтрации продуктов."""
    search: Optional[str] = Field(None, description="Поиск по названию")
    proxy_category: Optional[ProxyCategory] = Field(None, description="Категория прокси")
    proxy_type: Optional[ProxyType] = Field(None, description="Тип прокси")
    session_type: Optional[SessionType] = Field(None, description="Тип сессии")
    provider: Optional[ProviderType] = Field(None, description="Провайдер")
    country_code: Optional[str] = Field(None, description="Код страны")
    city: Optional[str] = Field(None, description="Город")
    min_price: Optional[float] = Field(None, ge=0, description="Минимальная цена")
    max_price: Optional[float] = Field(None, ge=0, description="Максимальная цена")
    min_duration: Optional[int] = Field(None, ge=1, description="Минимальная длительность")
    max_duration: Optional[int] = Field(None, ge=1, description="Максимальная длительность")
    min_threads: Optional[int] = Field(None, ge=1, description="Минимальное количество потоков")
    max_threads: Optional[int] = Field(None, ge=1, description="Максимальное количество потоков")
    min_speed: Optional[int] = Field(None, ge=1, description="Минимальная скорость")
    min_uptime: Optional[float] = Field(None, ge=0, le=100, description="Минимальный аптайм")
    sort: str = Field("created_at_desc", description="Сортировка")
    in_stock_only: bool = Field(False, description="Только товары в наличии")
    featured_only: bool = Field(False, description="Только рекомендуемые")


class ProductListResponse(BaseModel):
    """Схема списка продуктов с пагинацией."""
    items: List[ProxyProductResponse] = Field(..., description="Список продуктов")
    total: int = Field(..., ge=0, description="Общее количество")
    page: int = Field(..., ge=1, description="Текущая страница")
    per_page: int = Field(..., ge=1, description="Размер страницы")
    pages: int = Field(..., ge=0, description="Общее количество страниц")


class CategoryStatsResponse(BaseModel):
    """Статистика по категории."""
    category: str = Field(..., description="Код категории")
    category_name: str = Field(..., description="Отображаемое название")
    products_count: int = Field(..., description="Количество продуктов")
    avg_price: str = Field(..., description="Средняя цена")
    countries_count: int = Field(..., description="Количество стран")
    min_price: str = Field(..., description="Минимальная цена")
    max_price: str = Field(..., description="Максимальная цена")


class CountryResponse(BaseModel):
    """Информация о стране."""
    country_code: str = Field(..., description="Код страны")
    country_name: str = Field(..., description="Название страны")
    products_count: int = Field(..., description="Количество продуктов")
    flag_url: Optional[str] = Field(None, description="URL флага")
    avg_price: str = Field(..., description="Средняя цена")
    categories: List[str] = Field(default_factory=list, description="Доступные категории")


class ProductsByCategoryResponse(BaseModel):
    """Продукты по категории."""
    category: ProxyCategory = Field(..., description="Категория")
    category_name: str = Field(..., description="Название категории")
    products: List[ProxyProductResponse] = Field(..., description="Список продуктов")
    total: int = Field(..., description="Общее количество")
    page: int = Field(..., description="Текущая страница")
    per_page: int = Field(..., description="Размер страницы")


class ProductAvailabilityRequest(BaseModel):
    """Запрос проверки доступности продукта - ДОБАВЛЕНО для исправления ошибки."""
    product_id: int = Field(..., gt=0, description="ID продукта")
    quantity: int = Field(..., gt=0, le=10000, description="Запрашиваемое количество")

    @field_validator('quantity')
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        if v <= 0:
            raise ValueError('Quantity must be positive')
        if v > 10000:
            raise ValueError('Quantity cannot exceed 10,000')
        return v


class ProductAvailabilityResponse(BaseModel):
    """Ответ проверки доступности продукта."""
    product_id: int = Field(..., description="ID продукта")
    requested_quantity: int = Field(..., description="Запрошенное количество")
    available_quantity: int = Field(..., description="Доступное количество")
    is_available: bool = Field(..., description="Доступен ли товар")
    estimated_price: str = Field(..., description="Расчетная стоимость")
    currency: str = Field("USD", description="Валюта")
    message: Optional[str] = Field(None, description="Дополнительное сообщение")
    stock_available: int = Field(..., description="Остаток на складе")
    max_quantity: int = Field(..., description="Максимальное количество")
    price_per_unit: str = Field(..., description="Цена за единицу")
    total_price: str = Field(..., description="Общая стоимость")


class ProductBulkUpdateRequest(BaseModel):
    """Запрос массового обновления продуктов - ДОБАВЛЕНО для исправления ошибки."""
    product_ids: List[int] = Field(..., min_length=1, max_length=1000, description="Список ID продуктов")
    operation: str = Field(..., description="Тип операции")
    stock_change: Optional[int] = Field(None, description="Изменение остатка (для update_stock)")

    @field_validator('operation')
    @classmethod
    def validate_operation(cls, v: str) -> str:
        allowed_operations = [
            'activate', 'deactivate', 'feature', 'unfeature', 'update_stock'
        ]
        if v not in allowed_operations:
            raise ValueError(f'Operation must be one of: {", ".join(allowed_operations)}')
        return v

    @field_validator('product_ids')
    @classmethod
    def validate_product_ids(cls, v: List[int]) -> List[int]:
        if not v:
            raise ValueError('Product IDs list cannot be empty')
        if len(v) > 1000:
            raise ValueError('Cannot process more than 1000 products at once')
        if any(pid <= 0 for pid in v):
            raise ValueError('All product IDs must be positive')
        return v


class ProductBulkUpdateResponse(BaseModel):
    """Ответ массового обновления продуктов."""
    success: bool = Field(..., description="Успешность операции")
    processed: int = Field(..., description="Количество обработанных продуктов")
    total: int = Field(..., description="Общее количество запрошенных")
    errors: List[str] = Field(default_factory=list, description="Ошибки обработки")
    operation: str = Field(..., description="Выполненная операция")


class ProductStatsResponse(BaseModel):
    """Общая статистика продуктов."""
    total_products: int = Field(..., description="Общее количество продуктов")
    active_products: int = Field(..., description="Активные продукты")
    featured_products: int = Field(..., description="Рекомендуемые продукты")
    categories_count: int = Field(..., description="Количество категорий")
    countries_count: int = Field(..., description="Количество стран")
    providers_count: int = Field(..., description="Количество провайдеров")
    avg_price: str = Field(..., description="Средняя цена")
    price_range: Dict[str, str] = Field(..., description="Диапазон цен")
    total_stock: int = Field(..., description="Общий остаток")
    categories_breakdown: Dict[str, int] = Field(default_factory=dict, description="Разбивка по категориям")
    providers_breakdown: Dict[str, int] = Field(default_factory=dict, description="Разбивка по провайдерам")


class ProductSearchResponse(BaseModel):
    """Ответ поиска продуктов."""
    products: List[ProxyProductResponse] = Field(..., description="Найденные продукты")
    search_term: str = Field(..., description="Поисковый запрос")
    processed_term: str = Field(..., description="Обработанный запрос")
    total_found: int = Field(..., description="Количество найденных")
    suggestions: List[str] = Field(default_factory=list, description="Предложения")


class ProductRecommendationsResponse(BaseModel):
    """Рекомендации продуктов."""
    recommended_products: List[ProxyProductResponse] = Field(..., description="Рекомендуемые продукты")
    recommendation_reason: str = Field(..., description="Причина рекомендации")
    total_recommendations: int = Field(..., description="Общее количество рекомендаций")


class ProductPriceHistoryResponse(BaseModel):
    """История цен продукта."""
    product_id: int = Field(..., description="ID продукта")
    price_history: List[Dict[str, Any]] = Field(..., description="История изменения цен")
    current_price: str = Field(..., description="Текущая цена")
    price_trend: str = Field(..., description="Тренд цены (up/down/stable)")


