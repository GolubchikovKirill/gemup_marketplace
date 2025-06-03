"""
Базовые классы для сервисного слоя.

Предоставляет абстракции и общую функциональность
для всех сервисов приложения в соответствии с принципами SOLID.
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

ModelType = TypeVar("ModelType", bound=DeclarativeBase)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType], ABC):
    """
    Базовый абстрактный класс для всех сервисов.

    Определяет общий интерфейс для CRUD операций и обеспечивает
    единообразие архитектуры сервисного слоя.

    Generic Types:
        ModelType: Тип модели базы данных
        CreateSchemaType: Схема для создания объекта
        UpdateSchemaType: Схема для обновления объекта
    """

    def __init__(self, model: type[ModelType]):
        """
        Инициализация базового сервиса.

        Args:
            model: Класс модели базы данных
        """
        self.model = model

    @abstractmethod
    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: CreateSchemaType
    ) -> ModelType:
        """
        Создание нового объекта.

        Args:
            db: Сессия базы данных
            obj_in: Данные для создания объекта

        Returns:
            ModelType: Созданный объект
        """
        pass

    @abstractmethod
    async def get(
        self,
        db: AsyncSession,
        *,
        id: int
    ) -> Optional[ModelType]:
        """
        Получение объекта по идентификатору.

        Args:
            db: Сессия базы данных
            id: Идентификатор объекта

        Returns:
            Optional[ModelType]: Объект или None, если не найден
        """
        pass

    @abstractmethod
    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType
    ) -> ModelType:
        """
        Обновление существующего объекта.

        Args:
            db: Сессия базы данных
            db_obj: Объект для обновления
            obj_in: Данные для обновления

        Returns:
            ModelType: Обновленный объект
        """
        pass

    @abstractmethod
    async def delete(
        self,
        db: AsyncSession,
        *,
        id: int
    ) -> bool:
        """
        Удаление объекта по идентификатору.

        Args:
            db: Сессия базы данных
            id: Идентификатор объекта

        Returns:
            bool: Успешность операции удаления
        """
        pass

    @abstractmethod
    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """
        Получение списка объектов с пагинацией.

        Args:
            db: Сессия базы данных
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            List[ModelType]: Список объектов
        """
        pass


class BusinessRuleValidator(ABC):
    """
    Абстрактный базовый класс для валидации бизнес-правил.

    Предоставляет интерфейс для реализации специфических
    бизнес-правил в различных доменах приложения.
    """

    @abstractmethod
    async def validate(self, data: Dict[str, Any], db: AsyncSession) -> bool:
        """
        Валидация бизнес-правил для переданных данных.

        Args:
            data: Данные для валидации
            db: Сессия базы данных для выполнения проверок

        Returns:
            bool: Результат валидации (True - валидны, False - нет)

        Raises:
            BusinessLogicError: При нарушении бизнес-правил
        """
        pass


class EventPublisher(ABC):
    """
    Абстрактный базовый класс для публикации событий.

    Предоставляет интерфейс для реализации паттерна "Издатель-Подписчик"
    и интеграции с системами обмена сообщениями.
    """

    @abstractmethod
    async def publish(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Публикация события в систему обмена сообщениями.

        Args:
            event_type: Тип события
            data: Данные события

        Raises:
            PublishError: При ошибках публикации события
        """
        pass


class CacheService(ABC):
    """
    Абстрактный базовый класс для кэширования.

    Предоставляет интерфейс для работы с различными
    системами кэширования (Redis, Memcached и др.).
    """

    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        """
        Получение значения из кэша.

        Args:
            key: Ключ кэша

        Returns:
            Optional[str]: Значение или None
        """
        pass

    @abstractmethod
    async def set(self, key: str, value: str, expire: int = 3600) -> bool:
        """
        Сохранение значения в кэш.

        Args:
            key: Ключ кэша
            value: Значение для сохранения
            expire: Время жизни в секундах

        Returns:
            bool: Успешность операции
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Удаление значения из кэша.

        Args:
            key: Ключ кэша

        Returns:
            bool: Успешность операции
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Проверка существования ключа в кэше.

        Args:
            key: Ключ кэша

        Returns:
            bool: True если ключ существует
        """
        pass

    @abstractmethod
    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Получение JSON значения из кэша.

        Args:
            key: Ключ кэша

        Returns:
            Optional[Dict[str, Any]]: Десериализованное значение или None
        """
        pass

    @abstractmethod
    async def set_json(self, key: str, value: Dict[str, Any], expire: int = 3600) -> bool:
        """
        Сохранение JSON значения в кэш.

        Args:
            key: Ключ кэша
            value: Значение для сериализации и сохранения
            expire: Время жизни в секундах

        Returns:
            bool: Успешность операции
        """
        pass


class NotificationService(ABC):
    """
    Абстрактный базовый класс для уведомлений.

    Предоставляет интерфейс для отправки различных типов уведомлений.
    """

    @abstractmethod
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None
    ) -> bool:
        """
        Отправка email уведомления.

        Args:
            to: Email получателя
            subject: Тема письма
            body: Текст письма
            html_body: HTML версия письма

        Returns:
            bool: Успешность отправки
        """
        pass

    @abstractmethod
    async def send_sms(self, to: str, message: str) -> bool:
        """
        Отправка SMS уведомления.

        Args:
            to: Номер телефона получателя
            message: Текст сообщения

        Returns:
            bool: Успешность отправки
        """
        pass

    @abstractmethod
    async def send_push(
        self,
        user_id: int,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Отправка push уведомления.

        Args:
            user_id: ID пользователя
            title: Заголовок уведомления
            message: Текст уведомления
            data: Дополнительные данные

        Returns:
            bool: Успешность отправки
        """
        pass


class FileStorageService(ABC):
    """
    Абстрактный базовый класс для работы с файловым хранилищем.
    """

    @abstractmethod
    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        content_type: str
    ) -> str:
        """
        Загрузка файла в хранилище.

        Args:
            file_content: Содержимое файла
            filename: Имя файла
            content_type: MIME тип файла

        Returns:
            str: URL загруженного файла
        """
        pass

    @abstractmethod
    async def delete_file(self, file_url: str) -> bool:
        """
        Удаление файла из хранилища.

        Args:
            file_url: URL файла

        Returns:
            bool: Успешность удаления
        """
        pass

    @abstractmethod
    async def get_file_url(self, filename: str) -> str:
        """
        Получение URL файла.

        Args:
            filename: Имя файла

        Returns:
            str: URL файла
        """
        pass
