"""
Схемы для API ключей.

Содержит схемы для создания, обновления и отображения API ключей пользователей.
Упрощено для MVP - базовая функциональность без сложных разрешений.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, field_validator, field_serializer


class APIKeyBase(BaseModel):
    """Базовая схема API ключа."""
    name: str = Field(..., min_length=1, max_length=255, description="Название API ключа")
    description: Optional[str] = Field(None, max_length=1000, description="Описание")
    rate_limit: int = Field(1000, ge=1, le=10000, description="Лимит запросов в час")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Валидация названия API ключа."""
        if not v.strip():
            raise ValueError('API key name cannot be empty')
        return v.strip()


class APIKeyCreate(APIKeyBase):
    """Схема создания API ключа."""
    permissions: List[str] = Field(default_factory=list, description="Список разрешений")
    scopes: List[str] = Field(default_factory=list, description="Области действия")
    expires_in_days: Optional[int] = Field(None, ge=1, le=365, description="Срок действия в днях")

    @field_validator('permissions', 'scopes')
    @classmethod
    def validate_lists(cls, v: List[str]) -> List[str]:
        """Валидация списков разрешений и областей действия."""
        # Убираем дубликаты и пустые строки
        cleaned = list(set(item.strip() for item in v if item.strip()))
        return cleaned

    @field_validator('permissions')
    @classmethod
    def validate_permissions(cls, v: List[str]) -> List[str]:
        """Валидация разрешений - упрощено для MVP."""
        allowed_permissions = [
            'read', 'write', 'delete',
            'orders:read', 'orders:write',
            'transactions:read',
            'products:read',
            'proxies:read', 'proxies:write'
        ]

        for permission in v:
            if permission not in allowed_permissions:
                raise ValueError(f'Invalid permission: {permission}. Allowed: {", ".join(allowed_permissions)}')

        return v

    @field_validator('scopes')
    @classmethod
    def validate_scopes(cls, v: List[str]) -> List[str]:
        """Валидация областей действия - упрощено для MVP."""
        allowed_scopes = [
            'api', 'webhook', 'public',
            'user_data', 'order_data', 'proxy_data'
        ]

        for scope in v:
            if scope not in allowed_scopes:
                raise ValueError(f'Invalid scope: {scope}. Allowed: {", ".join(allowed_scopes)}')

        return v


class APIKeyUpdate(BaseModel):
    """Схема обновления API ключа."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None
    rate_limit: Optional[int] = Field(None, ge=1, le=10000)
    permissions: Optional[List[str]] = None
    scopes: Optional[List[str]] = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Валидация названия API ключа."""
        if v is not None:
            if not v.strip():
                raise ValueError('API key name cannot be empty')
            return v.strip()
        return v


class APIKeyResponse(BaseModel):
    """Схема ответа API ключа."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    user_id: int
    permissions: List[str] = Field(default_factory=list)
    scopes: List[str] = Field(default_factory=list)
    is_active: bool
    rate_limit: int
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    @field_serializer('expires_at', 'last_used', 'created_at', 'updated_at')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        """Сериализация datetime в ISO формат."""
        return value.isoformat() if value else None


class APIKeyCreated(BaseModel):
    """Схема созданного API ключа с секретным ключом."""
    api_key_info: APIKeyResponse
    api_key: str = Field(..., description="Секретный API ключ (показывается только при создании)")
    warning: str = Field(
        default="Сохраните этот ключ в безопасном месте. Он больше не будет показан.",
        description="Предупреждение о сохранении ключа"
    )


class APIKeyListResponse(BaseModel):
    """Схема списка API ключей."""
    api_keys: List[APIKeyResponse]
    total: int = Field(ge=0, description="Общее количество API ключей")
    active: int = Field(ge=0, description="Количество активных ключей")
    expired: int = Field(ge=0, description="Количество истекших ключей")


class APIKeyUsageStats(BaseModel):
    """Статистика использования API ключа."""
    api_key_id: int
    total_requests: int = Field(ge=0, description="Общее количество запросов")
    requests_today: int = Field(ge=0, description="Запросов сегодня")
    requests_this_month: int = Field(ge=0, description="Запросов в этом месяце")
    last_request_at: Optional[datetime] = Field(None, description="Время последнего запроса")
    rate_limit_exceeded: int = Field(ge=0, description="Количество превышений лимита")
    most_used_endpoints: List[dict] = Field(default_factory=list, description="Наиболее используемые endpoints")

    @field_serializer('last_request_at')
    def serialize_last_request(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None


class APIKeyPermissionCheck(BaseModel):
    """Схема проверки разрешений API ключа."""
    api_key_id: int
    permission: str = Field(..., description="Проверяемое разрешение")
    resource: Optional[str] = Field(None, description="Ресурс для проверки")
    action: Optional[str] = Field(None, description="Действие для проверки")


class APIKeyPermissionResult(BaseModel):
    """Результат проверки разрешений."""
    allowed: bool = Field(..., description="Разрешено ли действие")
    reason: Optional[str] = Field(None, description="Причина запрета (если не разрешено)")
    expires_at: Optional[datetime] = Field(None, description="Время истечения разрешения")

    @field_serializer('expires_at')
    def serialize_expires_at(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None
