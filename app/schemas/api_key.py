"""
Схемы для API ключей.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class APIKeyBase(BaseModel):
    """Базовая схема API ключа."""
    name: str = Field(..., min_length=1, max_length=100, description="Название API ключа")
    description: Optional[str] = Field(None, max_length=500, description="Описание")
    permissions: Optional[List[str]] = Field(default_factory=list, description="Список разрешений")
    scopes: Optional[List[str]] = Field(default_factory=list, description="Области действия")
    rate_limit: int = Field(1000, ge=1, le=10000, description="Лимит запросов в час")


class APIKeyCreate(APIKeyBase):
    """Схема создания API ключа."""
    expires_in_days: Optional[int] = Field(None, ge=1, le=365, description="Срок действия в днях")


class APIKeyUpdate(BaseModel):
    """Схема обновления API ключа."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None
    rate_limit: Optional[int] = Field(None, ge=1, le=10000)


class APIKeyResponse(BaseModel):
    """Схема ответа API ключа."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str]
    user_id: int
    permissions: List[str]
    scopes: List[str]
    is_active: bool
    rate_limit: int
    expires_at: Optional[datetime]
    last_used: Optional[datetime]
    created_at: datetime
    updated_at: datetime



class APIKeyCreated(BaseModel):
    """Схема созданного API ключа с секретным ключом."""
    api_key_info: APIKeyResponse
    api_key: str = Field(..., description="Секретный API ключ (показывается только при создании)")
