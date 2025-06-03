"""
Схемы для продуктов прокси.

Содержит все схемы для работы с продуктами прокси-серверов,
включая создание, обновление, фильтрацию и ответы API.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, field_serializer

from app.models.models import ProxyType, ProxyCategory, SessionType, ProviderType


class ProductFilter(BaseModel):
    """
    Схема фильтрации продуктов прокси.

    Позволяет фильтровать продукты по различным критериям:
    технические характеристики, цена, производительность.
    """
    # Текстовый поиск
    search: Optional[str] = Field(None, max_length=100, description="Поиск по названию и описанию")

    # Технические характеристики
    proxy_category: Optional[ProxyCategory] = Field(None, description="Категория прокси")
    proxy_type: Optional[ProxyType] = Field(None, description="Тип прокси протокола")
    provider: Optional[ProviderType] = Field(None, description="Провайдер прокси")

    # Геолокация
    country: Optional[str] = Field(None, min_length=2, max_length=3, description="Код страны")  # ИСПРАВЛЕНО: переименовано из country_code

    # Ценовой диапазон
    min_price: Optional[float] = Field(None, ge=0, description="Минимальная цена за прокси")  # ИСПРАВЛЕНО: тип float
    max_price: Optional[float] = Field(None, ge=0, description="Максимальная цена за прокси")  # ИСПРАВЛЕНО: тип float

    # Сортировка
    sort: Optional[str] = Field("created_at_desc", description="Поле и направление сортировки")


class ProxyProductBase(BaseModel):
    """
    Базовая схема продукта прокси.

    Содержит общие поля для создания и обновления продуктов.
    """
    name: str = Field(..., min_length=1, max_length=200, description="Название продукта")
    description: Optional[str] = Field(None, max_length=1000, description="Описание продукта")

    # Технические характеристики
    proxy_type: ProxyType = Field(..., description="Тип прокси протокола")
    proxy_category: ProxyCategory = Field(..., description="Категория прокси")
    session_type: SessionType = Field(..., description="Тип сессии")
    provider: ProviderType = Field(..., description="Провайдер прокси")

    # Геолокация
    country_code: str = Field(..., min_length=2, max_length=3, description="Код страны (ISO)")
    country_name: str = Field(..., min_length=1, max_length=100, description="Название страны")
    city: Optional[str] = Field(None, max_length=100, description="Город")

    # Ценообразование
    price_per_proxy: Decimal = Field(..., gt=0, description="Цена за один прокси")
    price_per_gb: Optional[Decimal] = Field(None, gt=0, description="Цена за ГБ трафика")

    # Ограничения и характеристики
    duration_days: int = Field(..., gt=0, le=365, description="Длительность в днях")
    min_quantity: int = Field(1, ge=1, le=1000, description="Минимальное количество")
    max_quantity: int = Field(100, ge=1, le=10000, description="Максимальное количество")
    max_threads: int = Field(1, ge=1, le=100, description="Максимум потоков")
    bandwidth_limit_gb: Optional[int] = Field(None, ge=1, description="Лимит трафика в ГБ")

    # Производительность
    uptime_guarantee: Optional[Decimal] = Field(None, ge=0, le=100, description="Гарантия uptime в %")
    speed_mbps: Optional[int] = Field(None, ge=1, description="Скорость в Мбит/с")
    ip_pool_size: Optional[int] = Field(None, ge=1, description="Размер пула IP")

    # Доступность
    stock_available: int = Field(0, ge=0, description="Количество в наличии")
    is_active: bool = Field(True, description="Активен ли продукт")
    is_featured: bool = Field(False, description="Рекомендуемый продукт")


class ProxyProductCreate(ProxyProductBase):
    """
    Схема создания продукта прокси.

    Используется администраторами для добавления новых продуктов в каталог.
    """
    provider_product_id: Optional[str] = Field(None, max_length=255, description="ID в системе провайдера")
    provider_metadata: Optional[str] = Field(None, description="Метаданные провайдера")


class ProxyProductUpdate(BaseModel):
    """
    Схема обновления продукта прокси.

    Все поля опциональны, позволяет частичное обновление.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)

    # Ценообразование
    price_per_proxy: Optional[Decimal] = Field(None, gt=0)
    price_per_gb: Optional[Decimal] = Field(None, gt=0)

    # Характеристики
    duration_days: Optional[int] = Field(None, gt=0, le=365)
    min_quantity: Optional[int] = Field(None, ge=1, le=1000)
    max_quantity: Optional[int] = Field(None, ge=1, le=10000)
    max_threads: Optional[int] = Field(None, ge=1, le=100)
    bandwidth_limit_gb: Optional[int] = Field(None, ge=1)

    # Производительность
    uptime_guarantee: Optional[Decimal] = Field(None, ge=0, le=100)
    speed_mbps: Optional[int] = Field(None, ge=1)
    ip_pool_size: Optional[int] = Field(None, ge=1)

    # Доступность
    stock_available: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None

    # Провайдер
    provider_product_id: Optional[str] = Field(None, max_length=255)
    provider_metadata: Optional[str] = None


class ProxyProductResponse(BaseModel):
    """
    Схема ответа продукта прокси.

    Полная информация о продукте для API ответов.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str]

    # Технические характеристики
    proxy_type: ProxyType
    proxy_category: ProxyCategory
    session_type: SessionType
    provider: ProviderType

    # Геолокация
    country_code: str
    country_name: str
    city: Optional[str]

    # Ценообразование
    price_per_proxy: Decimal
    price_per_gb: Optional[Decimal]

    # Характеристики
    duration_days: int
    min_quantity: int
    max_quantity: int
    max_threads: int
    bandwidth_limit_gb: Optional[int]

    # Производительность
    uptime_guarantee: Optional[Decimal]
    speed_mbps: Optional[int]
    ip_pool_size: Optional[int]

    # Доступность
    stock_available: int
    is_active: bool
    is_featured: bool

    # Провайдер
    provider_product_id: Optional[str]

    # Временные метки
    created_at: datetime
    updated_at: datetime

    @field_serializer('price_per_proxy', 'price_per_gb', 'uptime_guarantee')
    def serialize_decimal(self, value: Optional[Decimal]) -> Optional[str]:
        """Сериализация Decimal значений с высокой точностью."""
        return f"{value:.8f}" if value is not None else None

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, value: datetime) -> str:
        """Сериализация datetime в ISO формат."""
        return value.isoformat()


class ProxyProductPublic(BaseModel):
    """
    Публичная схема продукта прокси.

    Упрощенная версия без чувствительных данных для неавторизованных пользователей.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str]

    # Основные характеристики
    proxy_type: ProxyType
    proxy_category: ProxyCategory

    # Геолокация
    country_code: str
    country_name: str

    # Ценообразование (округленное)
    price_per_proxy: Decimal
    duration_days: int

    @field_serializer('price_per_proxy')
    def serialize_decimal_public(self, value: Decimal) -> str:
        """Сериализация с округлением для публичного API."""
        return f"{value:.2f}"


class ProductListResponse(BaseModel):
    """
    Схема ответа со списком продуктов и пагинацией.
    """
    items: List[ProxyProductResponse] = Field(..., description="Список продуктов")
    total: int = Field(..., ge=0, description="Общее количество продуктов")
    page: int = Field(..., ge=1, description="Текущая страница")
    size: int = Field(..., ge=1, le=100, description="Размер страницы")
    pages: int = Field(..., ge=1, description="Общее количество страниц")


class ProductsByCategoryResponse(BaseModel):  # ДОБАВЛЕНО: недостающая схема
    """
    Схема ответа со списком продуктов по категории.
    """
    category: str = Field(..., description="Название категории")
    products: List[ProxyProductResponse] = Field(..., description="Список продуктов")
    page: int = Field(..., ge=1, description="Номер страницы")
    size: int = Field(..., ge=1, description="Размер страницы")
    total: int = Field(..., ge=0, description="Общее количество продуктов")


class CountryResponse(BaseModel):
    """Схема информации о стране."""
    code: str = Field(..., description="Код страны")
    name: str = Field(..., description="Название страны")
    products_count: int = Field(0, ge=0, description="Количество продуктов в стране")
    flag_emoji: Optional[str] = Field(None, description="Emoji флага страны")


class CategoryStatsResponse(BaseModel):
    """Схема статистики по категории."""
    category: str = Field(..., description="Категория")
    name: str = Field(..., description="Читаемое название категории")
    products_count: int = Field(0, ge=0, description="Количество продуктов")
    price_range: dict = Field(..., description="Ценовой диапазон")
    sample_products: List[dict] = Field(default_factory=list, description="Примеры продуктов")


class ProductAvailabilityResponse(BaseModel):
    """Схема проверки доступности продукта."""
    product_id: int = Field(..., description="ID продукта")
    requested_quantity: int = Field(..., description="Запрошенное количество")
    is_available: bool = Field(..., description="Доступен ли в запрошенном количестве")
    stock_available: int = Field(..., description="Доступно на складе")
    max_quantity: int = Field(..., description="Максимальное количество для заказа")
    price_per_unit: str = Field(..., description="Цена за единицу")
    total_price: str = Field(..., description="Общая стоимость")
    currency: str = Field("USD", description="Валюта")
    message: str = Field(..., description="Сообщение о доступности")


# Создаем алиасы для обратной совместимости
ProductBase = ProxyProductBase
ProductCreate = ProxyProductCreate
ProductUpdate = ProxyProductUpdate
ProductResponse = ProxyProductResponse
