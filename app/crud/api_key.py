"""
CRUD операции для API ключей.

Содержит методы для создания, проверки и управления API ключами пользователей.
"""

import hashlib
import secrets
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import select, and_, func, desc, update, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.models import APIKey, User
from app.schemas.api_key import APIKeyCreate, APIKeyUpdate

logger = logging.getLogger(__name__)


class CRUDAPIKey(CRUDBase[APIKey, APIKeyCreate, APIKeyUpdate]):
    """CRUD для API ключей."""

    @staticmethod
    def generate_api_key() -> str:
        """
        Генерация нового API ключа.

        Returns:
            str: Случайный API ключ с префиксом
        """
        return f"gmp_{secrets.token_urlsafe(32)}"

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """
        Хеширование API ключа для безопасного хранения.

        Args:
            api_key: Исходный API ключ

        Returns:
            str: Хеш API ключа (SHA-256)
        """
        return hashlib.sha256(api_key.encode('utf-8')).hexdigest()

    async def create_api_key(
            self,
            db: AsyncSession,
            *,
            user_id: int,
            api_key_data: APIKeyCreate
    ) -> tuple[APIKey, str]:
        """
        Создание нового API ключа.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            api_key_data: Данные для создания API ключа

        Returns:
            tuple[APIKey, str]: Созданный объект API ключа и сам ключ

        Raises:
            ValueError: Если пользователь не найден
        """
        try:
            # Проверяем существование пользователя
            user = await db.get(User, user_id)
            if not user:
                raise ValueError("User not found")

            # Генерируем ключ
            api_key = self.generate_api_key()
            key_hash = self.hash_api_key(api_key)

            # Устанавливаем срок действия
            expires_at = None
            if api_key_data.expires_in_days:
                expires_at = datetime.now(timezone.utc) + timedelta(days=api_key_data.expires_in_days)

            # Создаем объект
            db_obj = APIKey(
                name=api_key_data.name,
                key_hash=key_hash,
                user_id=user_id,
                description=api_key_data.description,
                permissions=json.dumps(api_key_data.permissions),
                scopes=json.dumps(api_key_data.scopes),
                rate_limit=api_key_data.rate_limit,
                expires_at=expires_at,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )

            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)

            logger.info(f"Created API key {db_obj.id} for user {user_id}")
            return db_obj, api_key

        except ValueError:
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating API key: {e}")
            raise

    async def get_by_key(self, db: AsyncSession, *, key: str) -> Optional[APIKey]:
        """
        Получение API ключа по значению ключа.

        Args:
            db: Сессия базы данных
            key: API ключ

        Returns:
            Optional[APIKey]: API ключ или None
        """
        try:
            key_hash = self.hash_api_key(key)
            result = await db.execute(
                select(APIKey)
                .where(
                    and_(
                        APIKey.key_hash == key_hash,
                        APIKey.is_active.is_(True)
                    )
                )
            )
            api_key = result.scalar_one_or_none()

            # Проверяем срок действия
            if api_key and api_key.expires_at:
                if api_key.expires_at < datetime.now(timezone.utc):
                    logger.warning(f"API key {api_key.id} has expired")
                    return None

            return api_key

        except Exception as e:
            logger.error(f"Error getting API key: {e}")
            return None

    async def get_user_api_keys(
            self,
            db: AsyncSession,
            *,
            user_id: int,
            active_only: bool = True,
            skip: int = 0,
            limit: int = 100
    ) -> List[APIKey]:
        """
        Получение всех API ключей пользователя.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            active_only: Только активные ключи
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            List[APIKey]: Список API ключей
        """
        try:
            query = select(APIKey).where(APIKey.user_id == user_id)

            if active_only:
                current_time = datetime.now(timezone.utc)
                query = query.where(
                    and_(
                        APIKey.is_active.is_(True),
                        or_(
                            APIKey.expires_at.is_(None),
                            APIKey.expires_at > current_time
                        )
                    )
                )

            query = query.order_by(desc(APIKey.created_at)).offset(skip).limit(limit)
            result = await db.execute(query)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error getting user API keys: {e}")
            return []

    async def update_last_used(self, db: AsyncSession, *, api_key_id: int) -> bool:
        """
        Обновление времени последнего использования API ключа.

        Args:
            db: Сессия базы данных
            api_key_id: ID API ключа

        Returns:
            bool: True если обновление прошло успешно
        """
        try:
            result = await db.execute(
                update(APIKey)
                .where(APIKey.id == api_key_id)
                .values(
                    last_used=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
            )
            await db.commit()

            return result.rowcount > 0

        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating last used for API key {api_key_id}: {e}")
            return False

    async def deactivate(self, db: AsyncSession, *, api_key_id: int) -> Optional[APIKey]:
        """
        Деактивация API ключа.

        Args:
            db: Сессия базы данных
            api_key_id: ID API ключа

        Returns:
            Optional[APIKey]: Деактивированный ключ или None
        """
        try:
            api_key = await self.get(db, id=api_key_id)
            if api_key:
                api_key.is_active = False
                api_key.updated_at = datetime.now(timezone.utc)
                await db.commit()
                await db.refresh(api_key)
                logger.info(f"Deactivated API key {api_key_id}")
            return api_key

        except Exception as e:
            await db.rollback()
            logger.error(f"Error deactivating API key {api_key_id}: {e}")
            return None

    async def activate(self, db: AsyncSession, *, api_key_id: int) -> Optional[APIKey]:
        """
        Активация API ключа.

        Args:
            db: Сессия базы данных
            api_key_id: ID API ключа

        Returns:
            Optional[APIKey]: Активированный ключ или None
        """
        try:
            api_key = await self.get(db, id=api_key_id)
            if api_key:
                api_key.is_active = True
                api_key.updated_at = datetime.now(timezone.utc)
                await db.commit()
                await db.refresh(api_key)
                logger.info(f"Activated API key {api_key_id}")
            return api_key

        except Exception as e:
            await db.rollback()
            logger.error(f"Error activating API key {api_key_id}: {e}")
            return None

    async def get_api_key_stats(
            self,
            db: AsyncSession,
            *,
            user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Получение статистики API ключей.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя (опционально)

        Returns:
            Dict[str, Any]: Статистика API ключей
        """
        try:
            base_query = select(APIKey)
            if user_id:
                base_query = base_query.where(APIKey.user_id == user_id)

            # Общее количество
            total_result = await db.execute(
                select(func.count(APIKey.id)).select_from(base_query.subquery())
            )
            total = total_result.scalar() or 0

            # Активные
            active_result = await db.execute(
                select(func.count(APIKey.id)).select_from(
                    base_query.where(APIKey.is_active.is_(True)).subquery()
                )
            )
            active = active_result.scalar() or 0

            # Истекшие
            current_time = datetime.now(timezone.utc)
            expired_result = await db.execute(
                select(func.count(APIKey.id)).select_from(
                    base_query.where(
                        and_(
                            APIKey.expires_at.is_not(None),
                            APIKey.expires_at < current_time
                        )
                    ).subquery()
                )
            )
            expired = expired_result.scalar() or 0

            # Использованные за последние 30 дней
            thirty_days_ago = current_time - timedelta(days=30)
            used_recently_result = await db.execute(
                select(func.count(APIKey.id)).select_from(
                    base_query.where(
                        and_(
                            APIKey.last_used.is_not(None),
                            APIKey.last_used >= thirty_days_ago
                        )
                    ).subquery()
                )
            )
            used_recently = used_recently_result.scalar() or 0

            return {
                "total": total,
                "active": active,
                "expired": expired,
                "used_recently": used_recently,
                "inactive": total - active
            }

        except Exception as e:
            logger.error(f"Error getting API key stats: {e}")
            return {
                "total": 0,
                "active": 0,
                "expired": 0,
                "used_recently": 0,
                "inactive": 0
            }

    async def cleanup_expired_keys(self, db: AsyncSession) -> int:
        """
        Очистка истекших API ключей.

        Args:
            db: Сессия базы данных

        Returns:
            int: Количество деактивированных ключей
        """
        try:
            current_time = datetime.now(timezone.utc)

            result = await db.execute(
                update(APIKey)
                .where(
                    and_(
                        APIKey.expires_at < current_time,
                        APIKey.is_active.is_(True)
                    )
                )
                .values(
                    is_active=False,
                    updated_at=current_time
                )
            )
            await db.commit()

            count = result.rowcount or 0
            if count > 0:
                logger.info(f"Deactivated {count} expired API keys")

            return count

        except Exception as e:
            await db.rollback()
            logger.error(f"Error cleaning up expired API keys: {e}")
            return 0

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
                logger.warning(f"Invalid permissions JSON for API key {api_key.id}")
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
                logger.warning(f"Invalid scopes JSON for API key {api_key.id}")
                return []
        return []

    def check_permission(self, api_key: APIKey, required_permission: str) -> bool:
        """
        Проверка разрешения API ключа.

        Args:
            api_key: Объект API ключа
            required_permission: Требуемое разрешение

        Returns:
            bool: True если разрешение есть
        """
        permissions = self.get_api_key_permissions(api_key)

        # Проверяем точное совпадение
        if required_permission in permissions:
            return True

        # Проверяем wildcard разрешения
        if 'admin' in permissions:
            return True

        # Проверяем иерархические разрешения (например, users:write включает users:read)
        if ':' in required_permission:
            resource, action = required_permission.split(':', 1)
            if action == 'read' and f"{resource}:write" in permissions:
                return True

        return False

    def check_scope(self, api_key: APIKey, required_scope: str) -> bool:
        """
        Проверка области действия API ключа.

        Args:
            api_key: Объект API ключа
            required_scope: Требуемая область действия

        Returns:
            bool: True если область действия разрешена
        """
        scopes = self.get_api_key_scopes(api_key)
        return required_scope in scopes or 'api' in scopes


api_key_crud = CRUDAPIKey(APIKey)
