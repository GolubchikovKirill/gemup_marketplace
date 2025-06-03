"""
Схемы для разрешений.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class PermissionBase(BaseModel):
    """Базовая схема разрешения."""
    name: str = Field(..., min_length=1, max_length=100, description="Имя разрешения")
    description: Optional[str] = Field(None, max_length=255, description="Описание")
    category: str = Field("general", max_length=50, description="Категория разрешения")


class PermissionCreate(PermissionBase):
    """Схема создания разрешения."""
    is_active: bool = Field(True, description="Активность разрешения")


class PermissionUpdate(BaseModel):
    """Схема обновления разрешения."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None


class PermissionResponse(BaseModel):
    """Схема ответа разрешения."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str]
    category: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserPermissionsResponse(BaseModel):
    """Схема разрешений пользователя."""
    user_id: int
    permissions: List[PermissionResponse]


class SetUserPermissionsRequest(BaseModel):
    """Запрос установки разрешений пользователя."""
    permission_ids: List[int] = Field(..., description="Список ID разрешений")
