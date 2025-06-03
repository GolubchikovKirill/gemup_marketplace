"""
CRUD операции для API ключей.

Содержит методы для создания, проверки и управления API ключами.
"""

import hashlib
import secrets
import json
from datetime import datetime, timedelta
from typing import Optional, List

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.models import APIKey
from app.schemas.api_key import APIKeyCreate, APIKeyUpdate


class CRUDAPIKey(CRUDBase[APIKey, APIKeyCreate, APIKeyUpdate]):
    """CRUD для API ключей."""

    @staticmethod
    def generate_api_key() -> str:
        """
        Генерация нового API ключа.

        Returns:
            str: Случайный API ключ
        """
        return f"gmp_{secrets.token_urlsafe(32)}"

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """
        Хеширование API ключа для безопасного хранения.

        Args:
            api_key: Исходный API ключ

        Returns:
            str: Хеш API ключа
        """
        return hashlib.sha256(api_key.encode()).hexdigest()

    async def create_api_key(
            self,
            db: AsyncSession,
            *,
            user_id: int,
            name: str,
            permissions: Optional[List[str]] = None,
            scopes: Optional[List[str]] = None,
            description: Optional[str] = None,
            expires_in_days: Optional[int] = None,
            rate_limit: int = 1000
    ) -> tuple[APIKey, str]:
        """
        Создание нового API ключа.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            name: Название API ключа
            permissions: Список разрешений
            scopes: Список областей действия
            description: Описание
            expires_in_days: Срок действия в днях
            rate_limit: Лимит запросов в час

        Returns:
            tuple[APIKey, str]: Созданный объект API ключа и сам ключ
        """
        # Генерируем ключ
        api_key = self.generate_api_key()
        key_hash = self.hash_api_key(api_key)

        # Устанавливаем срок действия
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now() + timedelta(days=expires_in_days)

        # Создаем объект
        db_obj = APIKey(
            name=name,
            key_hash=key_hash,
            user_id=user_id,
            permissions=json.dumps(permissions or []),
            scopes=json.dumps(scopes or []),
            description=description,
            expires_at=expires_at,
            rate_limit=rate_limit,
            is_active=True
        )

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)

        return db_obj, api_key

    async def get_by_key(self, db: AsyncSession, *, key: str) -> Optional[APIKey]:
        """
        Получение API ключа по значению ключа.

        Args:
            db: Сессия базы данных
            key: API ключ

        Returns:
            Optional[APIKey]: API ключ или None
        """
        key_hash = self.hash_api_key(key)
        result = await db.execute(
            select(APIKey).where(APIKey.key_hash == key_hash)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_api_keys(
            db: AsyncSession,
            *,
            user_id: int,
            active_only: bool = True
    ) -> List[APIKey]:
        """
        Получение всех API ключей пользователя.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            active_only: Только активные ключи

        Returns:
            List[APIKey]: Список API ключей
        """
        query = select(APIKey).where(APIKey.user_id == user_id)

        if active_only:
            query = query.where(
                and_(
                    APIKey.is_active.is_(True),
                    APIKey.expires_at.is_(None) | (APIKey.expires_at > datetime.now())
                )
            )

        result = await db.execute(query)
        return list(result.scalars().all())

    async def update_last_used(self, db: AsyncSession, *, api_key_id: int) -> None:
        """
        Обновление времени последнего использования API ключа.

        Args:
            db: Сессия базы данных
            api_key_id: ID API ключа
        """
        api_key = await self.get(db, obj_id=api_key_id)
        if api_key:
            api_key.last_used = datetime.now()
            await db.commit()

    async def deactivate(self, db: AsyncSession, *, api_key_id: int) -> Optional[APIKey]:
        """
        Деактивация API ключа.

        Args:
            db: Сессия базы данных
            api_key_id: ID API ключа

        Returns:
            Optional[APIKey]: Деактивированный ключ или None
        """
        api_key = await self.get(db, obj_id=api_key_id)
        if api_key:
            api_key.is_active = False
            await db.commit()
            await db.refresh(api_key)
        return api_key

    @staticmethod
    def get_api_key_permissions(api_key: APIKey) -> List[str]:
        """
        Получение разрешений API ключа.

        Args:
            api_key: Объект API ключа

        Returns:
            List[str]: Список разрешений
        """
        if api_key.permissions:
            try:
                return json.loads(api_key.permissions)
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    @staticmethod
    def get_api_key_scopes(api_key: APIKey) -> List[str]:
        """
        Получение областей действия API ключа.

        Args:
            api_key: Объект API ключа

        Returns:
            List[str]: Список областей действия
        """
        if api_key.scopes:
            try:
                return json.loads(api_key.scopes)
            except (json.JSONDecodeError, TypeError):
                return []
        return []


api_key_crud = CRUDAPIKey(APIKey)
