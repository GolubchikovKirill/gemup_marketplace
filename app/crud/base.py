"""
Базовый CRUD класс для SQLAlchemy моделей.

Предоставляет общие методы для создания, чтения, обновления и удаления объектов.
Все специфичные CRUD классы наследуются от этого базового класса.
"""

import logging
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import Base

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType", bound=Base)
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

    async def get(self, db: AsyncSession, obj_id: Any) -> Optional[ModelType]:
        """
        Получение объекта по ID.

        Args:
            db: Сессия базы данных
            obj_id: ID объекта для поиска

        Returns:
            Optional[ModelType]: Найденный объект или None

        Raises:
            Exception: При ошибке базы данных
        """
        try:
            result = await db.execute(select(self.model).where(self.model.id == obj_id))
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting {self.model.__name__} by id {obj_id}: {e}")
            raise

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None
    ) -> List[ModelType]:
        """
        Получение списка объектов с пагинацией.

        Args:
            db: Сессия базы данных
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей (не более 1000)
            order_by: Поле для сортировки

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

            # Добавляем сортировку если указана
            if order_by and hasattr(self.model, order_by):
                order_field = getattr(self.model, order_by)
                query = query.order_by(order_field)
            elif hasattr(self.model, 'created_at'):
                # По умолчанию сортируем по дате создания
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
            obj_in_data = jsonable_encoder(obj_in)
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
            obj_data = jsonable_encoder(db_obj)

            if isinstance(obj_in, dict):
                update_data = obj_in
            else:
                update_data = obj_in.model_dump(exclude_unset=True) if hasattr(obj_in, 'model_dump') else obj_in.model_dump(exclude_unset=True)

            for field in obj_data:
                if field in update_data:
                    setattr(db_obj, field, update_data[field])

            # Обновляем updated_at если поле существует
            if hasattr(db_obj, 'updated_at'):
                from datetime import datetime
                db_obj.updated_at = datetime.now()

            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            logger.debug(f"Updated {self.model.__name__} with id {db_obj.id}")
            return db_obj

        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating {self.model.__name__}: {e}")
            raise

    async def delete(self, db: AsyncSession, *, obj_id: int) -> Optional[ModelType]:
        """
        Удаление объекта по ID.

        Args:
            db: Сессия базы данных
            obj_id: ID объекта для удаления

        Returns:
            Optional[ModelType]: Удаленный объект или None

        Raises:
            Exception: При ошибке удаления объекта
        """
        try:
            obj = await self.get(db, obj_id=obj_id)
            if obj:
                await db.delete(obj)
                await db.commit()
                logger.debug(f"Deleted {self.model.__name__} with id {obj_id}")
            return obj

        except Exception as e:
            await db.rollback()
            logger.error(f"Error deleting {self.model.__name__} with id {obj_id}: {e}")
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
                    if hasattr(self.model, field):
                        query = query.where(getattr(self.model, field) == value)

            result = await db.execute(query)
            return result.scalar() or 0

        except Exception as e:
            logger.error(f"Error counting {self.model.__name__}: {e}")
            raise

    async def exists(self, db: AsyncSession, obj_id: Any) -> bool:
        """
        Проверка существования объекта по ID.

        Args:
            db: Сессия базы данных
            obj_id: ID объекта

        Returns:
            bool: True если объект существует
        """
        try:
            result = await db.execute(
                select(func.count(self.model.id)).where(self.model.id == obj_id)
            )
            return (result.scalar() or 0) > 0

        except Exception as e:
            logger.error(f"Error checking existence of {self.model.__name__} with id {obj_id}: {e}")
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

    async def soft_delete(self, db: AsyncSession, *, obj_id: int) -> Optional[ModelType]:
        """
        Мягкое удаление объекта (установка is_active=False).

        Args:
            db: Сессия базы данных
            obj_id: ID объекта

        Returns:
            Optional[ModelType]: Объект после мягкого удаления или None

        Raises:
            ValueError: Если модель не поддерживает мягкое удаление
        """
        if not hasattr(self.model, 'is_active'):
            raise ValueError(f"Model {self.model.__name__} does not support soft delete")

        try:
            obj = await self.get(db, obj_id=obj_id)
            if obj:
                obj.is_active = False
                if hasattr(obj, 'updated_at'):
                    from datetime import datetime
                    obj.updated_at = datetime.now()

                await db.commit()
                await db.refresh(obj)
                logger.debug(f"Soft deleted {self.model.__name__} with id {obj_id}")
            return obj

        except Exception as e:
            await db.rollback()
            logger.error(f"Error soft deleting {self.model.__name__} with id {obj_id}: {e}")
            raise
