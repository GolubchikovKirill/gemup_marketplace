"""
Схемы для разрешений.

Содержит схемы для управления разрешениями пользователей,
включая создание, обновление и назначение разрешений.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator, field_serializer


class PermissionBase(BaseModel):
    """Базовая схема разрешения."""
    name: str = Field(..., min_length=1, max_length=100, description="Имя разрешения")
    description: Optional[str] = Field(None, max_length=1000, description="Описание")
    category: str = Field("general", max_length=50, description="Категория разрешения")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Валидация имени разрешения."""
        if not v.strip():
            raise ValueError('Permission name cannot be empty')

        # Проверяем формат имени (например, read:users, write:orders)
        if ':' in v:
            parts = v.split(':')
            if len(parts) != 2 or not all(part.strip() for part in parts):
                raise ValueError('Invalid permission format. Use "action:resource" format')

        return v.strip().lower()

    @field_validator('category')
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Валидация категории."""
        allowed_categories = [
            'general', 'users', 'orders', 'products', 'transactions',
            'api', 'admin', 'finance', 'reports', 'system'
        ]
        if v.lower() not in allowed_categories:
            raise ValueError(f'Category must be one of: {", ".join(allowed_categories)}')
        return v.lower()


class PermissionCreate(PermissionBase):
    """Схема создания разрешения."""
    is_active: bool = Field(True, description="Активность разрешения")


class PermissionUpdate(BaseModel):
    """Схема обновления разрешения."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    category: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Валидация имени разрешения."""
        if v is not None:
            if not v.strip():
                raise ValueError('Permission name cannot be empty')
            return v.strip().lower()
        return v

    @field_validator('category')
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        """Валидация категории."""
        if v is not None:
            allowed_categories = [
                'general', 'users', 'orders', 'products', 'transactions',
                'api', 'admin', 'finance', 'reports', 'system'
            ]
            if v.lower() not in allowed_categories:
                raise ValueError(f'Category must be one of: {", ".join(allowed_categories)}')
            return v.lower()
        return v


class PermissionResponse(BaseModel):
    """Схема ответа разрешения."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    category: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, value: datetime) -> str:
        """Сериализация datetime в ISO формат."""
        return value.isoformat()


class PermissionListResponse(BaseModel):
    """Схема списка разрешений."""
    permissions: List[PermissionResponse]
    total: int = Field(ge=0, description="Общее количество разрешений")
    by_category: Dict[str, int] = Field(default_factory=dict, description="Разбивка по категориям")


class UserPermissionsResponse(BaseModel):
    """Схема разрешений пользователя."""
    user_id: int
    permissions: List[PermissionResponse]
    total_permissions: int = Field(ge=0, description="Общее количество разрешений")
    by_category: Dict[str, int] = Field(default_factory=dict, description="Разбивка по категориям")

    def __init__(self, **data):
        super().__init__(**data)
        # Вычисляем статистику
        self.total_permissions = len(self.permissions)
        self.by_category = {}
        for perm in self.permissions:
            self.by_category[perm.category] = self.by_category.get(perm.category, 0) + 1


class SetUserPermissionsRequest(BaseModel):
    """Запрос установки разрешений пользователя."""
    permission_ids: List[int] = Field(..., min_items=0, max_items=100, description="Список ID разрешений")

    @field_validator('permission_ids')
    @classmethod
    def validate_permission_ids(cls, v: List[int]) -> List[int]:
        """Валидация ID разрешений."""
        # Убираем дубликаты
        unique_ids = list(set(v))
        if len(unique_ids) != len(v):
            raise ValueError('Duplicate permission IDs are not allowed')

        # Проверяем что все ID положительные
        if any(id_val <= 0 for id_val in unique_ids):
            raise ValueError('All permission IDs must be positive')

        return unique_ids


class AddPermissionToUserRequest(BaseModel):
    """Запрос добавления разрешения пользователю."""
    permission_id: int = Field(..., gt=0, description="ID разрешения")


class RemovePermissionFromUserRequest(BaseModel):
    """Запрос удаления разрешения у пользователя."""
    permission_id: int = Field(..., gt=0, description="ID разрешения")


class PermissionCheckRequest(BaseModel):
    """Запрос проверки разрешения."""
    user_id: int = Field(..., gt=0, description="ID пользователя")
    permission_name: str = Field(..., min_length=1, description="Имя разрешения")
    resource: Optional[str] = Field(None, description="Ресурс для проверки")


class PermissionCheckResponse(BaseModel):
    """Ответ проверки разрешения."""
    user_id: int
    permission_name: str
    has_permission: bool = Field(..., description="Есть ли разрешение")
    reason: Optional[str] = Field(None, description="Причина отказа")
    granted_by: Optional[str] = Field(None, description="Источник разрешения (direct/role)")


class PermissionStatsResponse(BaseModel):
    """Статистика разрешений."""
    total_permissions: int = Field(ge=0, description="Общее количество разрешений")
    active_permissions: int = Field(ge=0, description="Активные разрешения")
    inactive_permissions: int = Field(ge=0, description="Неактивные разрешения")
    categories: Dict[str, int] = Field(default_factory=dict, description="Разбивка по категориям")
    most_used_permissions: List[Dict[str, Any]] = Field(default_factory=list, description="Наиболее используемые")
    least_used_permissions: List[Dict[str, Any]] = Field(default_factory=list, description="Наименее используемые")


class PermissionFilter(BaseModel):
    """Фильтр для поиска разрешений."""
    name: Optional[str] = Field(None, max_length=100, description="Поиск по имени")
    category: Optional[str] = Field(None, max_length=50, description="Фильтр по категории")
    is_active: Optional[bool] = Field(None, description="Фильтр по активности")
    search: Optional[str] = Field(None, max_length=200, description="Общий поиск")

    @field_validator('search')
    @classmethod
    def validate_search(cls, v: Optional[str]) -> Optional[str]:
        """Валидация поискового запроса."""
        if v is not None:
            v = v.strip()
            if len(v) < 2:
                raise ValueError('Search query must be at least 2 characters long')
            return v
        return v


class BulkPermissionOperation(BaseModel):
    """Массовые операции с разрешениями."""
    permission_ids: List[int] = Field(..., min_items=1, max_items=100, description="ID разрешений")
    operation: str = Field(..., pattern="^(activate|deactivate|delete)$", description="Тип операции")

    @field_validator('permission_ids')
    @classmethod
    def validate_permission_ids(cls, v: List[int]) -> List[int]:
        """Валидация ID разрешений."""
        if len(set(v)) != len(v):
            raise ValueError('Duplicate permission IDs are not allowed')
        return v


class PermissionUsageResponse(BaseModel):
    """Статистика использования разрешения."""
    permission_id: int
    permission_name: str
    users_count: int = Field(ge=0, description="Количество пользователей с разрешением")
    roles_count: int = Field(ge=0, description="Количество ролей с разрешением")
    last_assigned: Optional[datetime] = Field(None, description="Последнее назначение")
    usage_frequency: str = Field("low", description="Частота использования")

    @field_serializer('last_assigned')
    def serialize_last_assigned(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None


class CreateDefaultPermissionsResponse(BaseModel):
    """Ответ создания базовых разрешений."""
    created_count: int = Field(ge=0, description="Количество созданных разрешений")
    skipped_count: int = Field(ge=0, description="Количество пропущенных (уже существуют)")
    created_permissions: List[PermissionResponse] = Field(default_factory=list, description="Созданные разрешения")
    errors: List[str] = Field(default_factory=list, description="Ошибки при создании")
