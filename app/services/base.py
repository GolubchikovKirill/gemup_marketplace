from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType], ABC):
    """Базовый сервисный класс (SOLID)"""

    def __init__(self, model: type[ModelType]):
        self.model = model

    @abstractmethod
    async def create(
            self,
            db: AsyncSession,
            obj_in: CreateSchemaType
    ) -> ModelType:
        """Создание объекта"""
        pass

    @abstractmethod
    async def get(
            self,
            db: AsyncSession,
            obj_id: int  # Переименовано id -> obj_id
    ) -> Optional[ModelType]:
        """Получение объекта по ID"""
        pass

    @abstractmethod
    async def update(
            self,
            db: AsyncSession,
            db_obj: ModelType,
            obj_in: UpdateSchemaType
    ) -> ModelType:
        """Обновление объекта"""
        pass

    @abstractmethod
    async def delete(
            self,
            db: AsyncSession,
            obj_id: int  # Переименовано id -> obj_id
    ) -> bool:
        """Удаление объекта"""
        pass

    @abstractmethod
    async def get_multi(
            self,
            db: AsyncSession,
            skip: int = 0,
            limit: int = 100
    ) -> List[ModelType]:
        """Получение списка объектов"""
        pass


class BusinessRuleValidator(ABC):
    """Абстрактный класс для валидации бизнес-правил"""

    @abstractmethod
    async def validate(self, data: dict, db: AsyncSession) -> bool:
        """Валидация бизнес-правил"""
        pass


class EventPublisher(ABC):
    """Абстрактный класс для публикации событий"""

    @abstractmethod
    async def publish(self, event_type: str, data: dict) -> None:
        """Публикация события"""
        pass
