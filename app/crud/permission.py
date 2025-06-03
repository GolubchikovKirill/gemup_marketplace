"""
CRUD операции для разрешений и ролей.

Содержит методы для управления разрешениями пользователей,
создания системы прав доступа и работы с ролями.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from sqlalchemy import select, and_, delete, func, desc, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from app.crud.base import CRUDBase
from app.models.models import Permission, User, user_permissions
from app.schemas.permission import PermissionCreate, PermissionUpdate, PermissionFilter

logger = logging.getLogger(__name__)


class CRUDPermission(CRUDBase[Permission, PermissionCreate, PermissionUpdate]):
    """
    CRUD для управления разрешениями пользователей.

    Обеспечивает создание, обновление и удаление разрешений,
    а также управление связями между пользователями и разрешениями.
    """

    async def get_by_name(self, db: AsyncSession, *, name: str) -> Optional[Permission]:
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
                select(Permission).where(Permission.name == name.lower())
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting permission by name '{name}': {e}")
            return None

    async def get_by_category(
            self,
            db: AsyncSession,
            *,
            category: str,
            active_only: bool = True,
            skip: int = 0,
            limit: int = 100
    ) -> List[Permission]:
        """
        Получение разрешений по категории.

        Args:
            db: Сессия базы данных
            category: Категория разрешений
            active_only: Только активные разрешения
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            List[Permission]: Список разрешений
        """
        try:
            query = select(Permission).where(Permission.category == category.lower())

            if active_only:
                query = query.where(Permission.is_active.is_(True))

            query = query.order_by(Permission.name).offset(skip).limit(limit)
            result = await db.execute(query)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error getting permissions by category '{category}': {e}")
            return []

    async def get_permissions_with_filter(
            self,
            db: AsyncSession,
            *,
            filter_params: PermissionFilter,
            skip: int = 0,
            limit: int = 100
    ) -> List[Permission]:
        """
        Получение разрешений с фильтрацией.

        Args:
            db: Сессия базы данных
            filter_params: Параметры фильтрации
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            List[Permission]: Список отфильтрованных разрешений
        """
        try:
            query = select(Permission)

            # Применяем фильтры
            if filter_params.name:
                query = query.where(Permission.name.ilike(f"%{filter_params.name}%"))

            if filter_params.category:
                query = query.where(Permission.category == filter_params.category.lower())

            if filter_params.is_active is not None:
                query = query.where(Permission.is_active == filter_params.is_active)

            if filter_params.search:
                search_pattern = f"%{filter_params.search}%"
                query = query.where(
                    or_(
                        Permission.name.ilike(search_pattern),
                        Permission.description.ilike(search_pattern)
                    )
                )

            query = query.order_by(Permission.category, Permission.name).offset(skip).limit(limit)
            result = await db.execute(query)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error getting permissions with filter: {e}")
            return []

    async def get_user_permissions(
            self,
            db: AsyncSession,
            *,
            user_id: int,
            active_only: bool = True
    ) -> List[Permission]:
        """
        Получение всех разрешений пользователя.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            active_only: Только активные разрешения

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
                if active_only:
                    return [perm for perm in user.permissions if perm.is_active]
                return list(user.permissions)
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
                raise ValueError("User not found")

            permission = await self.get(db, id=permission_id)
            if not permission:
                logger.warning(f"Permission {permission_id} not found")
                raise ValueError("Permission not found")

            if not permission.is_active:
                logger.warning(f"Permission {permission_id} is not active")
                raise ValueError("Permission is not active")

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
                return True  # Разрешение уже есть

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

        except ValueError:
            await db.rollback()
            raise
        except IntegrityError as e:
            await db.rollback()
            logger.warning(f"Integrity error adding permission {permission_id} to user {user_id}: {e}")
            return False
        except Exception as e:
            await db.rollback()
            logger.error(f"Error adding permission {permission_id} to user {user_id}: {e}")
            return False

    async def remove_permission_from_user(
            self,
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

    async def set_user_permissions(
            self,
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
                raise ValueError("User not found")

            # Проверяем существование всех разрешений
            if permission_ids:
                permissions = await db.execute(
                    select(Permission).where(
                        and_(
                            Permission.id.in_(permission_ids),
                            Permission.is_active.is_(True)
                        )
                    )
                )
                found_permissions = list(permissions.scalars().all())

                if len(found_permissions) != len(permission_ids):
                    found_ids = [p.id for p in found_permissions]
                    missing_ids = set(permission_ids) - set(found_ids)
                    logger.warning(f"Permissions not found or inactive: {missing_ids}")
                    raise ValueError(f"Some permissions not found or inactive: {missing_ids}")

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

        except ValueError:
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error setting permissions for user {user_id}: {e}")
            return False

    async def get_users_with_permission(
            self,
            db: AsyncSession,
            *,
            permission_id: int,
            active_only: bool = True,
            skip: int = 0,
            limit: int = 100
    ) -> List[User]:
        """
        Получение пользователей с определенным разрешением.

        Args:
            db: Сессия базы данных
            permission_id: ID разрешения
            active_only: Только активные пользователи
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

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

            query = query.order_by(User.created_at).offset(skip).limit(limit)
            result = await db.execute(query)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error getting users with permission {permission_id}: {e}")
            return []

    async def check_user_permission(
            self,
            db: AsyncSession,
            *,
            user_id: int,
            permission_name: str
    ) -> bool:
        """
        Проверка наличия разрешения у пользователя.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            permission_name: Имя разрешения

        Returns:
            bool: True если разрешение есть
        """
        try:
            result = await db.execute(
                select(Permission)
                .join(user_permissions)
                .where(
                    and_(
                        user_permissions.c.user_id == user_id,
                        Permission.name == permission_name.lower(),
                        Permission.is_active.is_(True)
                    )
                )
            )
            return result.scalar_one_or_none() is not None

        except Exception as e:
            logger.error(f"Error checking permission {permission_name} for user {user_id}: {e}")
            return False

    async def create_default_permissions(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Создание базовых разрешений системы.

        Args:
            db: Сессия базы данных

        Returns:
            Dict[str, Any]: Результат создания
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

            # Отчеты
            ("read:reports", "Просмотр отчетов", "reports"),
            ("export:data", "Экспорт данных", "reports"),

            # Система
            ("manage:permissions", "Управление разрешениями", "system"),
            ("manage:roles", "Управление ролями", "system"),
        ]

        created_permissions = []
        skipped_count = 0
        errors = []

        try:
            for name, description, category in default_permissions:
                try:
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
                    else:
                        skipped_count += 1
                        logger.debug(f"Permission already exists: {name}")
                except Exception as e:
                    error_msg = f"Failed to create permission {name}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)

            logger.info(f"Created {len(created_permissions)} default permissions, skipped {skipped_count}")

            return {
                "created_count": len(created_permissions),
                "skipped_count": skipped_count,
                "created_permissions": created_permissions,
                "errors": errors
            }

        except Exception as e:
            logger.error(f"Error creating default permissions: {e}")
            return {
                "created_count": 0,
                "skipped_count": 0,
                "created_permissions": [],
                "errors": [str(e)]
            }

    async def get_permission_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Получение статистики по разрешениям.

        Args:
            db: Сессия базы данных

        Returns:
            Dict[str, Any]: Статистика разрешений
        """
        try:
            # Общее количество разрешений
            total_result = await db.execute(select(func.count(Permission.id)))
            total_permissions = total_result.scalar() or 0

            # Активные разрешения
            active_result = await db.execute(
                select(func.count(Permission.id)).where(Permission.is_active.is_(True))
            )
            active_permissions = active_result.scalar() or 0

            # Разрешения по категориям
            categories_result = await db.execute(
                select(Permission.category, func.count(Permission.id))
                .where(Permission.is_active.is_(True))
                .group_by(Permission.category)
            )
            categories = dict(categories_result.all())

            # Наиболее используемые разрешения
            most_used_result = await db.execute(
                select(
                    Permission.id,
                    Permission.name,
                    func.count(user_permissions.c.user_id).label('usage_count')
                )
                .join(user_permissions, Permission.id == user_permissions.c.permission_id, isouter=True)
                .group_by(Permission.id, Permission.name)
                .order_by(desc('usage_count'))
                .limit(10)
            )
            most_used = [
                {"permission_id": row.id, "permission_name": row.name, "usage_count": row.usage_count}
                for row in most_used_result.all()
            ]

            # Наименее используемые разрешения
            least_used_result = await db.execute(
                select(
                    Permission.id,
                    Permission.name,
                    func.count(user_permissions.c.user_id).label('usage_count')
                )
                .join(user_permissions, Permission.id == user_permissions.c.permission_id, isouter=True)
                .group_by(Permission.id, Permission.name)
                .order_by('usage_count')
                .limit(10)
            )
            least_used = [
                {"permission_id": row.id, "permission_name": row.name, "usage_count": row.usage_count}
                for row in least_used_result.all()
            ]

            return {
                "total_permissions": total_permissions,
                "active_permissions": active_permissions,
                "inactive_permissions": total_permissions - active_permissions,
                "categories": categories,
                "most_used_permissions": most_used,
                "least_used_permissions": least_used
            }

        except Exception as e:
            logger.error(f"Error getting permission stats: {e}")
            return {
                "total_permissions": 0,
                "active_permissions": 0,
                "inactive_permissions": 0,
                "categories": {},
                "most_used_permissions": [],
                "least_used_permissions": []
            }

    async def bulk_permission_operation(
            self,
            db: AsyncSession,
            *,
            permission_ids: List[int],
            operation: str
    ) -> Dict[str, Any]:
        """
        Массовые операции с разрешениями.

        Args:
            db: Сессия базы данных
            permission_ids: Список ID разрешений
            operation: Тип операции (activate, deactivate, delete)

        Returns:
            Dict[str, Any]: Результат операции
        """
        try:
            if not permission_ids:
                return {"success": False, "message": "No permission IDs provided", "processed": 0}

            processed = 0

            if operation == "activate":
                result = await db.execute(
                    update(Permission)
                    .where(Permission.id.in_(permission_ids))
                    .values(is_active=True, updated_at=datetime.now(timezone.utc))
                )
                processed = result.rowcount or 0

            elif operation == "deactivate":
                result = await db.execute(
                    update(Permission)
                    .where(Permission.id.in_(permission_ids))
                    .values(is_active=False, updated_at=datetime.now(timezone.utc))
                )
                processed = result.rowcount or 0

            elif operation == "delete":
                # Сначала удаляем связи с пользователями
                await db.execute(
                    delete(user_permissions).where(user_permissions.c.permission_id.in_(permission_ids))
                )

                # Затем удаляем сами разрешения
                result = await db.execute(
                    delete(Permission).where(Permission.id.in_(permission_ids))
                )
                processed = result.rowcount or 0

            await db.commit()

            logger.info(f"Bulk {operation} operation processed {processed} permissions")
            return {
                "success": True,
                "message": f"Successfully {operation}d {processed} permissions",
                "processed": processed
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Error in bulk permission operation: {e}")
            return {
                "success": False,
                "message": f"Operation failed: {str(e)}",
                "processed": 0
            }


permission_crud = CRUDPermission(Permission)
