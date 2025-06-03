"""
CRUD операции для разрешений и ролей.

Содержит методы для управления разрешениями пользователей,
создания системы прав доступа и работы с ролями.
"""

import logging
from typing import List, Optional

from sqlalchemy import select, and_, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from app.crud.base import CRUDBase
from app.models.models import Permission, User, user_permissions
from app.schemas.permission import PermissionCreate, PermissionUpdate

logger = logging.getLogger(__name__)


class CRUDPermission(CRUDBase[Permission, PermissionCreate, PermissionUpdate]):
    """
    CRUD для управления разрешениями пользователей.

    Обеспечивает создание, обновление и удаление разрешений,
    а также управление связями между пользователями и разрешениями.
    """

    @staticmethod
    async def get_by_name(db: AsyncSession, *, name: str) -> Optional[Permission]:
        """
        Получение разрешения по имени.

        Args:
            db: Сессия базы данных
            name: Имя разрешения

        Returns:
            Optional[Permission]: Разрешение или None
        """
        try:
            result = await db.execute(
                select(Permission).where(Permission.name == name)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting permission by name '{name}': {e}")
            raise

    @staticmethod
    async def get_by_category(
            db: AsyncSession,
        *,
        category: str,
        active_only: bool = True
    ) -> List[Permission]:
        """
        Получение разрешений по категории.

        Args:
            db: Сессия базы данных
            category: Категория разрешений
            active_only: Только активные разрешения

        Returns:
            List[Permission]: Список разрешений
        """
        try:
            query = select(Permission).where(Permission.category == category)

            if active_only:
                query = query.where(Permission.is_active.is_(True))

            query = query.order_by(Permission.name)
            result = await db.execute(query)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error getting permissions by category '{category}': {e}")
            return []

    @staticmethod
    async def get_user_permissions(
            db: AsyncSession,
        *,
        user_id: int
    ) -> List[Permission]:
        """
        Получение всех разрешений пользователя.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя

        Returns:
            List[Permission]: Список разрешений пользователя
        """
        try:
            result = await db.execute(
                select(User)
                .options(selectinload(User.permissions))
                .where(User.id == user_id)
            )
            user = result.scalar_one_or_none()

            if user:
                return [perm for perm in user.permissions if perm.is_active]
            return []

        except Exception as e:
            logger.error(f"Error getting permissions for user {user_id}: {e}")
            return []

    async def add_permission_to_user(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        permission_id: int
    ) -> bool:
        """
        Добавление разрешения пользователю.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            permission_id: ID разрешения

        Returns:
            bool: True если разрешение добавлено успешно
        """
        try:
            # Проверяем существование пользователя и разрешения
            user = await db.get(User, user_id)
            if not user:
                logger.warning(f"User {user_id} not found")
                return False

            permission = await self.get(db, obj_id=permission_id)
            if not permission:
                logger.warning(f"Permission {permission_id} not found")
                return False

            # Проверяем, есть ли уже такое разрешение у пользователя
            result = await db.execute(
                select(user_permissions).where(
                    and_(
                        user_permissions.c.user_id == user_id,
                        user_permissions.c.permission_id == permission_id
                    )
                )
            )

            if result.first():
                logger.debug(f"User {user_id} already has permission {permission_id}")
                return False  # Разрешение уже есть

            # Добавляем разрешение
            await db.execute(
                user_permissions.insert().values(
                    user_id=user_id,
                    permission_id=permission_id
                )
            )
            await db.commit()

            logger.info(f"Added permission {permission_id} to user {user_id}")
            return True

        except IntegrityError as e:
            await db.rollback()
            logger.warning(f"Integrity error adding permission {permission_id} to user {user_id}: {e}")
            return False
        except Exception as e:
            await db.rollback()
            logger.error(f"Error adding permission {permission_id} to user {user_id}: {e}")
            return False

    @staticmethod
    async def remove_permission_from_user(
            db: AsyncSession,
        *,
        user_id: int,
        permission_id: int
    ) -> bool:
        """
        Удаление разрешения у пользователя.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            permission_id: ID разрешения

        Returns:
            bool: True если разрешение удалено успешно
        """
        try:
            result = await db.execute(
                delete(user_permissions).where(
                    and_(
                        user_permissions.c.user_id == user_id,
                        user_permissions.c.permission_id == permission_id
                    )
                )
            )
            await db.commit()

            if result.rowcount > 0:
                logger.info(f"Removed permission {permission_id} from user {user_id}")
                return True
            else:
                logger.debug(f"Permission {permission_id} was not assigned to user {user_id}")
                return False

        except Exception as e:
            await db.rollback()
            logger.error(f"Error removing permission {permission_id} from user {user_id}: {e}")
            return False

    @staticmethod
    async def set_user_permissions(
            db: AsyncSession,
        *,
        user_id: int,
        permission_ids: List[int]
    ) -> bool:
        """
        Установка списка разрешений для пользователя (заменяет существующие).

        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            permission_ids: Список ID разрешений

        Returns:
            bool: True если операция успешна
        """
        try:
            # Проверяем существование пользователя
            user = await db.get(User, user_id)
            if not user:
                logger.warning(f"User {user_id} not found")
                return False

            # Проверяем существование всех разрешений
            if permission_ids:
                permissions = await db.execute(
                    select(Permission).where(Permission.id.in_(permission_ids))
                )
                found_permissions = list(permissions.scalars().all())

                if len(found_permissions) != len(permission_ids):
                    found_ids = [p.id for p in found_permissions]
                    missing_ids = set(permission_ids) - set(found_ids)
                    logger.warning(f"Permissions not found: {missing_ids}")
                    return False

            # Удаляем все существующие разрешения
            await db.execute(
                delete(user_permissions).where(
                    user_permissions.c.user_id == user_id
                )
            )

            # Добавляем новые разрешения
            if permission_ids:
                values = [
                    {"user_id": user_id, "permission_id": perm_id}
                    for perm_id in permission_ids
                ]
                await db.execute(user_permissions.insert().values(values))

            await db.commit()

            logger.info(f"Set {len(permission_ids)} permissions for user {user_id}")
            return True

        except Exception as e:
            await db.rollback()
            logger.error(f"Error setting permissions for user {user_id}: {e}")
            return False

    @staticmethod
    async def get_users_with_permission(
            db: AsyncSession,
        *,
        permission_id: int,
        active_only: bool = True
    ) -> List[User]:
        """
        Получение пользователей с определенным разрешением.

        Args:
            db: Сессия базы данных
            permission_id: ID разрешения
            active_only: Только активные пользователи

        Returns:
            List[User]: Список пользователей
        """
        try:
            query = (
                select(User)
                .join(user_permissions)
                .where(user_permissions.c.permission_id == permission_id)
            )

            if active_only:
                query = query.where(User.is_active.is_(True))

            result = await db.execute(query)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error getting users with permission {permission_id}: {e}")
            return []

    async def create_default_permissions(self, db: AsyncSession) -> List[Permission]:
        """
        Создание базовых разрешений системы.

        Args:
            db: Сессия базы данных

        Returns:
            List[Permission]: Список созданных разрешений
        """
        default_permissions = [
            # Пользователи
            ("read:users", "Просмотр пользователей", "users"),
            ("write:users", "Управление пользователями", "users"),
            ("delete:users", "Удаление пользователей", "users"),

            # Заказы
            ("read:orders", "Просмотр заказов", "orders"),
            ("write:orders", "Управление заказами", "orders"),
            ("cancel:orders", "Отмена заказов", "orders"),

            # Продукты
            ("read:products", "Просмотр продуктов", "products"),
            ("write:products", "Управление продуктами", "products"),
            ("delete:products", "Удаление продуктов", "products"),

            # Транзакции
            ("read:transactions", "Просмотр транзакций", "transactions"),
            ("write:transactions", "Управление транзакциями", "transactions"),

            # API ключи
            ("manage:api_keys", "Управление API ключами", "api"),
            ("read:api_keys", "Просмотр API ключей", "api"),

            # Админка
            ("admin:full", "Полный административный доступ", "admin"),
            ("admin:users", "Администрирование пользователей", "admin"),
            ("admin:finance", "Администрирование финансов", "admin"),
        ]

        created_permissions = []

        try:
            for name, description, category in default_permissions:
                # Проверяем, есть ли уже такое разрешение
                existing = await self.get_by_name(db, name=name)
                if not existing:
                    permission_data = PermissionCreate(
                        name=name,
                        description=description,
                        category=category,
                        is_active=True
                    )
                    permission = await self.create(db, obj_in=permission_data)
                    created_permissions.append(permission)
                    logger.debug(f"Created permission: {name}")

            if created_permissions:
                logger.info(f"Created {len(created_permissions)} default permissions")

            return created_permissions

        except Exception as e:
            logger.error(f"Error creating default permissions: {e}")
            return []

    async def get_permission_stats(self, db: AsyncSession) -> dict:
        """
        Получение статистики по разрешениям.

        Args:
            db: Сессия базы данных

        Returns:
            dict: Статистика разрешений
        """
        try:
            # Общее количество разрешений
            total_permissions = await self.count(db)

            # Активные разрешения
            active_permissions = await self.count(db, filters={"is_active": True})

            # Разрешения по категориям
            categories_result = await db.execute(
                select(Permission.category, func.count(Permission.id))
                .where(Permission.is_active.is_(True))
                .group_by(Permission.category)
            )
            categories = dict(categories_result.all())

            return {
                "total_permissions": total_permissions,
                "active_permissions": active_permissions,
                "categories": categories
            }

        except Exception as e:
            logger.error(f"Error getting permission stats: {e}")
            return {
                "total_permissions": 0,
                "active_permissions": 0,
                "categories": {}
            }


permission_crud = CRUDPermission(Permission)
