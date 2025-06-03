"""
Базовый CRUD класс для SQLAlchemy моделей.

Предоставляет общие методы для создания, чтения, обновления и удаления объектов.
Все специфичные CRUD классы наследуются от этого базового класса.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType", bound=DeclarativeBase)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Базовый CRUD класс с методами по умолчанию для Create, Read, Update, Delete.

    Предоставляет стандартные операции CRUD для работы с SQLAlchemy моделями.
    Все методы асинхронные и используют AsyncSession.

    Args:
        model: SQLAlchemy модель для работы с базой данных
    """

    def __init__(self, model: Type[ModelType]):
        """
        Инициализация CRUD объекта с моделью.

        Args:
            model: SQLAlchemy модель
        """
        self.model = model

    async def get(self, db: AsyncSession, *, id: Any) -> Optional[ModelType]:
        """
        Получение объекта по ID.

        Args:
            db: Сессия базы данных
            id: ID объекта для поиска

        Returns:
            Optional[ModelType]: Найденный объект или None

        Raises:
            Exception: При ошибке базы данных
        """
        try:
            result = await db.execute(select(self.model).where(self.model.id == id))
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting {self.model.__name__} by id {id}: {e}")
            raise

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        """
        Получение списка объектов с пагинацией и фильтрацией.

        Args:
            db: Сессия базы данных
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей (не более 1000)
            order_by: Поле для сортировки
            filters: Дополнительные фильтры

        Returns:
            List[ModelType]: Список объектов

        Raises:
            ValueError: При некорректных параметрах пагинации
        """
        # Валидация параметров
        if skip < 0:
            raise ValueError("skip cannot be negative")
        if limit <= 0 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")

        try:
            query = select(self.model)

            # Применяем фильтры
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        if value is not None:
                            query = query.where(getattr(self.model, field) == value)

            # Добавляем сортировку если указана
            if order_by and hasattr(self.model, order_by):
                order_field = getattr(self.model, order_by)
                if order_by.endswith('_desc'):
                    field_name = order_by[:-5]
                    if hasattr(self.model, field_name):
                        query = query.order_by(getattr(self.model, field_name).desc())
                else:
                    query = query.order_by(order_field)
            elif hasattr(self.model, 'created_at'):
                # По умолчанию сортируем по дате создания (новые первые)
                query = query.order_by(self.model.created_at.desc())

            query = query.offset(skip).limit(limit)
            result = await db.execute(query)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error getting multiple {self.model.__name__}: {e}")
            raise

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        """
        Создание нового объекта.

        Args:
            db: Сессия базы данных
            obj_in: Схема для создания объекта

        Returns:
            ModelType: Созданный объект

        Raises:
            Exception: При ошибке создания объекта
        """
        try:
            # Преобразуем схему в словарь
            if hasattr(obj_in, 'model_dump'):
                obj_in_data = obj_in.model_dump(exclude_unset=True)
            else:
                obj_in_data = jsonable_encoder(obj_in)

            # Добавляем временные метки если поля существуют
            current_time = datetime.now(timezone.utc)
            if hasattr(self.model, 'created_at') and 'created_at' not in obj_in_data:
                obj_in_data['created_at'] = current_time
            if hasattr(self.model, 'updated_at') and 'updated_at' not in obj_in_data:
                obj_in_data['updated_at'] = current_time

            db_obj = self.model(**obj_in_data)
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            logger.debug(f"Created {self.model.__name__} with id {db_obj.id}")
            return db_obj

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating {self.model.__name__}: {e}")
            raise

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """
        Обновление существующего объекта.

        Args:
            db: Сессия базы данных
            db_obj: Объект для обновления
            obj_in: Схема или словарь с данными для обновления

        Returns:
            ModelType: Обновленный объект

        Raises:
            Exception: При ошибке обновления объекта
        """
        try:
            if isinstance(obj_in, dict):
                update_data = obj_in
            else:
                update_data = obj_in.model_dump(exclude_unset=True) if hasattr(obj_in, 'model_dump') else obj_in.model_dump(exclude_unset=True)

            # Обновляем только переданные поля
            for field, value in update_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)

            # Обновляем updated_at если поле существует
            if hasattr(db_obj, 'updated_at'):
                db_obj.updated_at = datetime.now(timezone.utc)

            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            logger.debug(f"Updated {self.model.__name__} with id {db_obj.id}")
            return db_obj

        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating {self.model.__name__}: {e}")
            raise

    async def delete(self, db: AsyncSession, *, id: int) -> Optional[ModelType]:
        """
        Удаление объекта по ID.

        Args:
            db: Сессия базы данных
            id: ID объекта для удаления

        Returns:
            Optional[ModelType]: Удаленный объект или None

        Raises:
            Exception: При ошибке удаления объекта
        """
        try:
            obj = await self.get(db, id=id)
            if obj:
                await db.delete(obj)
                await db.commit()
                logger.debug(f"Deleted {self.model.__name__} with id {id}")
            return obj

        except Exception as e:
            await db.rollback()
            logger.error(f"Error deleting {self.model.__name__} with id {id}: {e}")
            raise

    async def count(self, db: AsyncSession, *, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Подсчет общего количества объектов.

        Args:
            db: Сессия базы данных
            filters: Дополнительные фильтры для подсчета

        Returns:
            int: Количество объектов

        Raises:
            Exception: При ошибке подсчета
        """
        try:
            query = select(func.count(self.model.id))

            # Применяем фильтры если есть
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field) and value is not None:
                        query = query.where(getattr(self.model, field) == value)

            result = await db.execute(query)
            return result.scalar() or 0

        except Exception as e:
            logger.error(f"Error counting {self.model.__name__}: {e}")
            raise

    async def exists(self, db: AsyncSession, *, id: Any) -> bool:
        """
        Проверка существования объекта по ID.

        Args:
            db: Сессия базы данных
            id: ID объекта

        Returns:
            bool: True если объект существует
        """
        try:
            result = await db.execute(
                select(func.count(self.model.id)).where(self.model.id == id)
            )
            return (result.scalar() or 0) > 0

        except Exception as e:
            logger.error(f"Error checking existence of {self.model.__name__} with id {id}: {e}")
            return False

    async def get_by_field(
        self,
        db: AsyncSession,
        *,
        field: str,
        value: Any
    ) -> Optional[ModelType]:
        """
        Получение объекта по значению поля.

        Args:
            db: Сессия базы данных
            field: Название поля
            value: Значение для поиска

        Returns:
            Optional[ModelType]: Найденный объект или None

        Raises:
            ValueError: При отсутствии поля в модели
        """
        if not hasattr(self.model, field):
            raise ValueError(f"Field '{field}' does not exist in {self.model.__name__}")

        try:
            result = await db.execute(
                select(self.model).where(getattr(self.model, field) == value)
            )
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error getting {self.model.__name__} by {field}={value}: {e}")
            raise

    async def get_multi_by_field(
        self,
        db: AsyncSession,
        *,
        field: str,
        value: Any,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """
        Получение множественных объектов по значению поля.

        Args:
            db: Сессия базы данных
            field: Название поля
            value: Значение для поиска
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            List[ModelType]: Список найденных объектов

        Raises:
            ValueError: При отсутствии поля в модели
        """
        if not hasattr(self.model, field):
            raise ValueError(f"Field '{field}' does not exist in {self.model.__name__}")

        try:
            query = select(self.model).where(getattr(self.model, field) == value)

            if hasattr(self.model, 'created_at'):
                query = query.order_by(self.model.created_at.desc())

            query = query.offset(skip).limit(limit)
            result = await db.execute(query)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error getting multiple {self.model.__name__} by {field}={value}: {e}")
            raise

    async def soft_delete(self, db: AsyncSession, *, id: int) -> Optional[ModelType]:
        """
        Мягкое удаление объекта (установка is_active=False).

        Args:
            db: Сессия базы данных
            id: ID объекта

        Returns:
            Optional[ModelType]: Объект после мягкого удаления или None

        Raises:
            ValueError: Если модель не поддерживает мягкое удаление
        """
        if not hasattr(self.model, 'is_active'):
            raise ValueError(f"Model {self.model.__name__} does not support soft delete")

        try:
            obj = await self.get(db, id=id)
            if obj:
                obj.is_active = False
                if hasattr(obj, 'updated_at'):
                    obj.updated_at = datetime.now(timezone.utc)

                await db.commit()
                await db.refresh(obj)
                logger.debug(f"Soft deleted {self.model.__name__} with id {id}")
            return obj

        except Exception as e:
            await db.rollback()
            logger.error(f"Error soft deleting {self.model.__name__} with id {id}: {e}")
            raise

    async def restore(self, db: AsyncSession, *, id: int) -> Optional[ModelType]:
        """
        Восстановление мягко удаленного объекта.

        Args:
            db: Сессия базы данных
            id: ID объекта

        Returns:
            Optional[ModelType]: Восстановленный объект или None

        Raises:
            ValueError: Если модель не поддерживает мягкое удаление
        """
        if not hasattr(self.model, 'is_active'):
            raise ValueError(f"Model {self.model.__name__} does not support soft delete/restore")

        try:
            obj = await self.get(db, id=id)
            if obj:
                obj.is_active = True
                if hasattr(obj, 'updated_at'):
                    obj.updated_at = datetime.now(timezone.utc)

                await db.commit()
                await db.refresh(obj)
                logger.debug(f"Restored {self.model.__name__} with id {id}")
            return obj

        except Exception as e:
            await db.rollback()
            logger.error(f"Error restoring {self.model.__name__} with id {id}: {e}")
            raise

    async def search(
        self,
        db: AsyncSession,
        *,
        search_term: str,
        search_fields: List[str],
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """
        Поиск объектов по нескольким полям.

        Args:
            db: Сессия базы данных
            search_term: Поисковый термин
            search_fields: Список полей для поиска
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            List[ModelType]: Список найденных объектов
        """
        if not search_term or len(search_term.strip()) < 2:
            return []

        try:
            search_pattern = f"%{search_term.strip()}%"
            conditions = []

            for field in search_fields:
                if hasattr(self.model, field):
                    field_attr = getattr(self.model, field)
                    conditions.append(field_attr.ilike(search_pattern))

            if not conditions:
                return []

            query = select(self.model).where(or_(*conditions))

            if hasattr(self.model, 'created_at'):
                query = query.order_by(self.model.created_at.desc())

            query = query.offset(skip).limit(limit)
            result = await db.execute(query)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error searching {self.model.__name__}: {e}")
            return []

    async def bulk_create(self, db: AsyncSession, *, objs_in: List[CreateSchemaType]) -> List[ModelType]:
        """
        Массовое создание объектов.

        Args:
            db: Сессия базы данных
            objs_in: Список схем для создания

        Returns:
            List[ModelType]: Список созданных объектов
        """
        if not objs_in:
            return []

        try:
            db_objs = []
            current_time = datetime.now(timezone.utc)

            for obj_in in objs_in:
                if hasattr(obj_in, 'model_dump'):
                    obj_data = obj_in.model_dump(exclude_unset=True)
                else:
                    obj_data = jsonable_encoder(obj_in)

                # Добавляем временные метки
                if hasattr(self.model, 'created_at') and 'created_at' not in obj_data:
                    obj_data['created_at'] = current_time
                if hasattr(self.model, 'updated_at') and 'updated_at' not in obj_data:
                    obj_data['updated_at'] = current_time

                db_obj = self.model(**obj_data)
                db_objs.append(db_obj)

            db.add_all(db_objs)
            await db.commit()

            # Обновляем объекты
            for db_obj in db_objs:
                await db.refresh(db_obj)

            logger.debug(f"Bulk created {len(db_objs)} {self.model.__name__} objects")
            return db_objs

        except Exception as e:
            await db.rollback()
            logger.error(f"Error bulk creating {self.model.__name__}: {e}")
            raise

    async def bulk_update(
        self,
        db: AsyncSession,
        *,
        ids: List[int],
        update_data: Dict[str, Any]
    ) -> int:
        """
        Массовое обновление объектов.

        Args:
            db: Сессия базы данных
            ids: Список ID объектов для обновления
            update_data: Данные для обновления

        Returns:
            int: Количество обновленных объектов
        """
        if not ids or not update_data:
            return 0

        try:
            # Добавляем updated_at если поле существует
            if hasattr(self.model, 'updated_at'):
                update_data['updated_at'] = datetime.now(timezone.utc)

            from sqlalchemy import update
            stmt = update(self.model).where(self.model.id.in_(ids)).values(**update_data)
            result = await db.execute(stmt)
            await db.commit()

            updated_count = result.rowcount or 0
            logger.debug(f"Bulk updated {updated_count} {self.model.__name__} objects")
            return updated_count

        except Exception as e:
            await db.rollback()
            logger.error(f"Error bulk updating {self.model.__name__}: {e}")
            raise

    async def bulk_delete(self, db: AsyncSession, *, ids: List[int]) -> int:
        """
        Массовое удаление объектов.

        Args:
            db: Сессия базы данных
            ids: Список ID объектов для удаления

        Returns:
            int: Количество удаленных объектов
        """
        if not ids:
            return 0

        try:
            from sqlalchemy import delete
            stmt = delete(self.model).where(self.model.id.in_(ids))
            result = await db.execute(stmt)
            await db.commit()

            deleted_count = result.rowcount or 0
            logger.debug(f"Bulk deleted {deleted_count} {self.model.__name__} objects")
            return deleted_count

        except Exception as e:
            await db.rollback()
            logger.error(f"Error bulk deleting {self.model.__name__}: {e}")
            raise


class BusinessRuleValidator:
    """
    Базовый класс для валидации бизнес-правил.

    Используется в сервисах для проверки сложных бизнес-правил
    перед выполнением операций с данными.
    """

    async def validate(self, data: Dict[str, Any], db: AsyncSession) -> bool:
        """
        Валидация бизнес-правил.

        Args:
            data: Данные для валидации
            db: Сессия базы данных

        Returns:
            bool: True если валидация прошла успешно

        Raises:
            ValueError: При нарушении бизнес-правил
        """
        raise NotImplementedError("Subclasses must implement validate method")
