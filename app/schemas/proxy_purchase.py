"""
Схемы для покупок прокси.

Содержит схемы для управления приобретенными прокси-серверами,
включая генерацию списков, продление и статистику использования.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, ConfigDict, field_serializer, field_validator

from app.models.models import ProxyType, ProxyCategory


class ProxyPurchaseBase(BaseModel):
    """
    Базовая схема покупки прокси.

    Содержит основную информацию о приобретенных прокси-серверах.
    """
    user_id: int = Field(..., gt=0, description="ID пользователя")
    proxy_product_id: int = Field(..., gt=0, description="ID продукта прокси")
    order_id: int = Field(..., gt=0, description="ID заказа")
    proxy_list: str = Field(..., min_length=1, description="Список прокси серверов")
    username: Optional[str] = Field(None, max_length=100, description="Имя пользователя для аутентификации")
    password: Optional[str] = Field(None, max_length=255, description="Пароль для аутентификации")
    expires_at: datetime = Field(..., description="Дата истечения срока действия")
    traffic_used_gb: Decimal = Field(Decimal('0.00'), ge=0, description="Использованный трафик в ГБ")
    provider_order_id: Optional[str] = Field(None, max_length=255, description="ID заказа у провайдера")
    provider_metadata: Optional[str] = Field(None, description="Метаданные провайдера")

    @field_validator('proxy_list')
    @classmethod
    def validate_proxy_list(cls, v: str) -> str:
        """Валидация списка прокси."""
        lines = v.strip().split('\n')
        if not lines or not any(line.strip() for line in lines):
            raise ValueError('Proxy list cannot be empty')

        # Базовая проверка формата прокси
        for line in lines:
            line = line.strip()
            if line and ':' not in line:
                raise ValueError('Invalid proxy format: must contain IP:PORT')

        return v.strip()

    @field_validator('expires_at')
    @classmethod
    def validate_expires_at(cls, v: datetime) -> datetime:
        """Валидация срока истечения."""
        if v <= datetime.now():
            raise ValueError('Expiration date must be in the future')
        return v


class ProxyPurchaseCreate(ProxyPurchaseBase):
    """
    Схема создания покупки прокси.

    Используется при создании новой записи о приобретенных прокси.
    """
    is_active: bool = Field(True, description="Активна ли покупка")


class ProxyPurchaseUpdate(BaseModel):
    """
    Схема обновления покупки прокси.

    Позволяет обновлять информацию о прокси после покупки.
    """
    proxy_list: Optional[str] = Field(None, min_length=1, description="Обновленный список прокси")
    username: Optional[str] = Field(None, max_length=100, description="Новое имя пользователя")
    password: Optional[str] = Field(None, max_length=255, description="Новый пароль")
    is_active: Optional[bool] = Field(None, description="Статус активности")
    expires_at: Optional[datetime] = Field(None, description="Новая дата истечения")
    traffic_used_gb: Optional[Decimal] = Field(None, ge=0, description="Обновленный использованный трафик")
    last_used: Optional[datetime] = Field(None, description="Время последнего использования")
    provider_order_id: Optional[str] = Field(None, max_length=255, description="ID заказа провайдера")
    provider_metadata: Optional[str] = Field(None, description="Метаданные провайдера")

    @field_validator('proxy_list')
    @classmethod
    def validate_proxy_list(cls, v: Optional[str]) -> Optional[str]:
        """Валидация обновляемого списка прокси."""
        if v is not None:
            return ProxyPurchaseBase.validate_proxy_list(v)
        return v


class ProxyPurchaseResponse(BaseModel):
    """
    Схема ответа покупки прокси.

    Содержит полную информацию о приобретенных прокси для API ответов.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    proxy_product_id: int
    order_id: int
    proxy_list: str
    username: Optional[str]
    password: Optional[str]
    is_active: bool
    expires_at: datetime
    traffic_used_gb: Decimal
    last_used: Optional[datetime]
    provider_order_id: Optional[str]
    provider_metadata: Optional[str]
    created_at: datetime
    updated_at: datetime

    # Информация о продукте (может быть загружена отдельно)
    product_name: Optional[str] = Field(None, description="Название продукта")
    proxy_type: Optional[ProxyType] = Field(None, description="Тип прокси")
    proxy_category: Optional[ProxyCategory] = Field(None, description="Категория прокси")
    country_code: Optional[str] = Field(None, description="Код страны")
    country_name: Optional[str] = Field(None, description="Название страны")

    # Вычисляемые поля
    days_until_expiry: Optional[int] = Field(None, description="Дней до истечения")
    proxy_count: Optional[int] = Field(None, description="Количество прокси")

    @field_serializer('traffic_used_gb')
    def serialize_traffic(self, value: Decimal) -> str:
        """Сериализация трафика."""
        return f"{value:.2f}"

    @field_serializer('expires_at', 'last_used', 'created_at', 'updated_at')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        """Сериализация datetime в ISO формат."""
        return value.isoformat() if value else None

    def __init__(self, **data):
        super().__init__(**data)
        # Вычисляем дни до истечения
        if self.expires_at:
            delta = self.expires_at - datetime.now()
            self.days_until_expiry = max(0, delta.days)

        # Считаем количество прокси
        if self.proxy_list:
            lines = [line.strip() for line in self.proxy_list.split('\n') if line.strip()]
            self.proxy_count = len(lines)


class ProxyDetailsResponse(BaseModel):
    """
    Детальная информация о покупке прокси.

    Расширенная схема с полной информацией о прокси и связанных данных.
    """
    id: int = Field(..., description="ID покупки")
    order_id: int = Field(..., description="ID заказа")

    # Информация о продукте
    product: Dict[str, Any] = Field(..., description="Информация о продукте")

    # Список прокси с деталями
    proxy_list: List[Dict[str, Any]] = Field(..., description="Детальный список прокси")

    # Учетные данные
    credentials: Dict[str, Optional[str]] = Field(..., description="Данные для аутентификации")

    # Статус и срок действия
    status: Dict[str, Any] = Field(..., description="Информация о статусе")

    # Статистика использования
    usage: Dict[str, Any] = Field(..., description="Статистика использования")

    # Метаданные
    metadata: Dict[str, Any] = Field(..., description="Дополнительные метаданные")


class ProxyExtensionRequest(BaseModel):  # ИСПРАВЛЕНО: правильное имя схемы
    """
    Запрос на продление прокси.

    Используется для продления срока действия приобретенных прокси.
    """
    days: int = Field(..., ge=1, le=365, description="Количество дней для продления")
    auto_renew: bool = Field(False, description="Включить автоматическое продление")

    @field_validator('days')
    @classmethod
    def validate_days(cls, v: int) -> int:
        """Валидация количества дней."""
        if v < 1:
            raise ValueError('Extension period must be at least 1 day')
        if v > 365:
            raise ValueError('Extension period cannot exceed 365 days')
        return v


class ProxyExtensionResponse(BaseModel):
    """
    Ответ на запрос продления прокси.
    """
    purchase_id: int = Field(..., description="ID покупки")
    extended_days: int = Field(..., description="Количество добавленных дней")
    new_expires_at: str = Field(..., description="Новая дата истечения")
    cost: str = Field(..., description="Стоимость продления")
    currency: str = Field("USD", description="Валюта")
    status: str = Field(..., description="Статус операции")


class ProxyGenerationRequest(BaseModel):
    """
    Запрос на генерацию списка прокси.

    Позволяет указать формат вывода и параметры генерации.
    """
    format_type: str = Field(
        "ip:port:user:pass",
        description="Формат вывода прокси"
    )
    include_auth: bool = Field(True, description="Включить данные аутентификации")
    separator: str = Field("\n", max_length=10, description="Разделитель между прокси")
    line_ending: str = Field("\n", description="Окончание строки")

    @field_validator('format_type')
    @classmethod
    def validate_format_type(cls, v: str) -> str:
        """Валидация типа формата."""
        allowed_formats = [
            'ip:port',
            'ip:port:user:pass',
            'user:pass@ip:port',
            'https://user:pass@ip:port'
        ]
        if v not in allowed_formats:
            raise ValueError(f'Format type must be one of: {", ".join(allowed_formats)}')
        return v


class ProxyGenerationResponse(BaseModel):
    """
    Ответ генерации списка прокси.

    Содержит отформатированный список прокси для скачивания.
    """
    purchase_id: int = Field(..., description="ID покупки")
    proxy_count: int = Field(..., ge=0, description="Количество прокси")
    format: str = Field(..., description="Использованный формат")
    proxies: List[str] = Field(..., description="Список отформатированных прокси")
    expires_at: datetime = Field(..., description="Срок действия прокси")
    generated_at: datetime = Field(default_factory=datetime.now, description="Время генерации")
    total_size_bytes: Optional[int] = Field(None, description="Общий размер в байтах")

    @field_serializer('expires_at', 'generated_at')
    def serialize_datetime(self, value: datetime) -> str:
        """Сериализация datetime."""
        return value.isoformat()

    def __init__(self, **data):
        super().__init__(**data)
        # Вычисляем размер данных
        if self.proxies:
            content = '\n'.join(self.proxies)
            self.total_size_bytes = len(content.encode('utf-8'))


class ProxyStatsResponse(BaseModel):
    """
    Статистика использования прокси пользователем.
    """
    total_purchases: int = Field(..., ge=0, description="Общее количество покупок")
    active_purchases: int = Field(..., ge=0, description="Активных покупок")
    total_traffic_used_gb: str = Field(..., description="Общий использованный трафик")
    product_breakdown: Dict[str, Any] = Field(default_factory=dict, description="Разбивка по продуктам")
    period_days: int = Field(..., description="Период статистики в днях")

    # Дополнительная статистика
    total_proxies: int = Field(0, ge=0, description="Общее количество прокси")
    active_proxies: int = Field(0, ge=0, description="Активных прокси")
    expired_proxies: int = Field(0, ge=0, description="Истекших прокси")
    expiring_soon: int = Field(0, ge=0, description="Истекающих в ближайшие 7 дней")

    # Детальная статистика
    by_category: Dict[str, int] = Field(default_factory=dict, description="По категориям")
    by_country: Dict[str, int] = Field(default_factory=dict, description="По странам")
    by_provider: Dict[str, int] = Field(default_factory=dict, description="По провайдерам")

    # Временная статистика
    purchased_this_month: int = Field(0, ge=0, description="Куплено в этом месяце")
    total_spent: str = Field("0.00", description="Общая потрачена сумма")


class ProxyUsageLog(BaseModel):
    """
    Лог использования прокси.
    """
    purchase_id: int = Field(..., description="ID покупки")
    used_at: datetime = Field(..., description="Время использования")
    traffic_mb: Decimal = Field(..., ge=0, description="Трафик в МБ")
    ip_address: Optional[str] = Field(None, description="IP адрес клиента")
    user_agent: Optional[str] = Field(None, max_length=500, description="User Agent")
    success: bool = Field(..., description="Успешное использование")
    error_message: Optional[str] = Field(None, max_length=500, description="Сообщение об ошибке")

    @field_serializer('used_at')
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()

    @field_serializer('traffic_mb')
    def serialize_traffic(self, value: Decimal) -> str:
        return f"{value:.2f}"


class ProxyHealthCheck(BaseModel):
    """
    Результат проверки работоспособности прокси.
    """
    purchase_id: int = Field(..., description="ID покупки")
    checked_at: datetime = Field(default_factory=datetime.now, description="Время проверки")
    working_proxies: int = Field(..., ge=0, description="Работающих прокси")
    total_proxies: int = Field(..., ge=0, description="Общее количество прокси")
    average_response_time: Optional[float] = Field(None, description="Среднее время отклика в мс")
    success_rate: float = Field(..., ge=0, le=100, description="Процент работающих прокси")
    failed_proxies: List[str] = Field(default_factory=list, description="Список неработающих прокси")

    @field_serializer('checked_at')
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()

    def __init__(self, **data):
        super().__init__(**data)
        # Вычисляем процент успешности
        if self.total_proxies > 0:
            self.success_rate = (self.working_proxies / self.total_proxies) * 100
        else:
            self.success_rate = 0.0


# Алиасы для обратной совместимости с роутами
ProxyExtendRequest = ProxyExtensionRequest
ProxyExtendResponse = ProxyExtensionResponse
