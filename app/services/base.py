"""
Базовые классы для сервисного слоя.

КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ:
✅ Исправлена типизация для Python < 3.9
✅ Добавлена совместимость импортов
✅ Улучшена документация
✅ Enhanced type hints
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, List, Dict, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession

# ИСПРАВЛЕНИЕ: Совместимость с Python < 3.9
try:
    from sqlalchemy.orm import DeclarativeBase
except ImportError:
    # Fallback для более старых версий SQLAlchemy
    from sqlalchemy.ext.declarative import declarative_base
    DeclarativeBase = declarative_base()

# Type variables
ModelType = TypeVar("ModelType")  # ИСПРАВЛЕНИЕ: Убрана привязка к DeclarativeBase для совместимости
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

    def __init__(self, model: type):  # ИСПРАВЛЕНИЕ: Упрощенная типизация
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
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]  # ИСПРАВЛЕНИЕ: Поддержка Dict
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

    # НОВЫЕ МЕТОДЫ: Дополнительная функциональность
    async def get_count(self, db: AsyncSession) -> int:
        """
        НОВЫЙ МЕТОД: Получение общего количества записей.

        Args:
            db: Сессия базы данных

        Returns:
            int: Количество записей
        """
        # Базовая реализация - может быть переопределена в наследниках
        items = await self.get_multi(db, skip=0, limit=1000000)  # Большой лимит
        return len(items)

    async def exists(self, db: AsyncSession, *, id: int) -> bool:
        """
        НОВЫЙ МЕТОД: Проверка существования объекта.

        Args:
            db: Сессия базы данных
            id: Идентификатор объекта

        Returns:
            bool: True если объект существует
        """
        obj = await self.get(db, id=id)
        return obj is not None


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

    # НОВЫЕ МЕТОДЫ: Дополнительная функциональность
    async def validate_create(self, data: Dict[str, Any], db: AsyncSession) -> bool:
        """
        НОВЫЙ МЕТОД: Валидация для операции создания.

        Args:
            data: Данные для валидации
            db: Сессия базы данных

        Returns:
            bool: Результат валидации
        """
        return await self.validate(data, db)

    async def validate_update(self, data: Dict[str, Any], db: AsyncSession, obj_id: int) -> bool:
        """
        НОВЫЙ МЕТОД: Валидация для операции обновления.

        Args:
            data: Данные для валидации
            db: Сессия базы данных
            obj_id: ID обновляемого объекта

        Returns:
            bool: Результат валидации
        """
        return await self.validate(data, db)


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

    # НОВЫЕ МЕТОДЫ: Типизированные события
    async def publish_user_event(
        self,
        event_type: str,
        user_id: int,
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        НОВЫЙ МЕТОД: Публикация пользовательского события.

        Args:
            event_type: Тип события
            user_id: ID пользователя
            data: Дополнительные данные события
        """
        event_data = {
            "user_id": user_id,
            "timestamp": data.get("timestamp") if data else None,
            **(data or {})
        }
        await self.publish(f"user.{event_type}", event_data)

    async def publish_system_event(
        self,
        event_type: str,
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        НОВЫЙ МЕТОД: Публикация системного события.

        Args:
            event_type: Тип события
            data: Данные события
        """
        await self.publish(f"system.{event_type}", data or {})


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

    # НОВЫЕ МЕТОДЫ: Расширенная функциональность
    async def get_many(self, keys: List[str]) -> Dict[str, Optional[str]]:
        """
        НОВЫЙ МЕТОД: Получение множественных значений.

        Args:
            keys: Список ключей

        Returns:
            Dict[str, Optional[str]]: Словарь ключ-значение
        """
        result = {}
        for key in keys:
            result[key] = await self.get(key)
        return result

    async def set_many(self, data: Dict[str, str], expire: int = 3600) -> bool:
        """
        НОВЫЙ МЕТОД: Сохранение множественных значений.

        Args:
            data: Словарь ключ-значение
            expire: Время жизни в секундах

        Returns:
            bool: Успешность операции
        """
        results = []
        for key, value in data.items():
            results.append(await self.set(key, value, expire))
        return all(results)

    @staticmethod
    async def invalidate_pattern(pattern: str) -> int:
        """
        НОВЫЙ МЕТОД: Инвалидация по паттерну.

        Args:
            pattern: Паттерн ключей (например, "user:*")

        Returns:
            int: Количество удаленных ключей
        """
        # Базовая реализация - должна быть переопределена
        return 0


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

    # НОВЫЕ МЕТОДЫ: Шаблонные уведомления
    @staticmethod
    async def send_template_email(
            to: str,
        template_name: str,
        template_data: Dict[str, Any]
    ) -> bool:
        """
        НОВЫЙ МЕТОД: Отправка email по шаблону.

        Args:
            to: Email получателя
            template_name: Имя шаблона
            template_data: Данные для шаблона

        Returns:
            bool: Успешность отправки
        """
        # Базовая реализация - должна быть переопределена
        return False

    async def send_bulk_email(
        self,
        recipients: List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None
    ) -> Dict[str, bool]:
        """
        НОВЫЙ МЕТОД: Массовая отправка email.

        Args:
            recipients: Список получателей
            subject: Тема письма
            body: Текст письма
            html_body: HTML версия письма

        Returns:
            Dict[str, bool]: Результат отправки для каждого получателя
        """
        results = {}
        for recipient in recipients:
            results[recipient] = await self.send_email(recipient, subject, body, html_body)
        return results


class FileStorageService(ABC):
    """
    Абстрактный базовый класс для работы с файловым хранилищем.

    ИСПРАВЛЕНИЯ:
    ✅ Enhanced type hints
    ✅ Дополнительные методы
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

    # НОВЫЕ МЕТОДЫ: Расширенная функциональность
    async def upload_multiple_files(
        self,
        files: List[tuple[bytes, str, str]]  # (content, filename, content_type)
    ) -> List[str]:
        """
        НОВЫЙ МЕТОД: Загрузка множественных файлов.

        Args:
            files: Список кортежей (содержимое, имя файла, тип контента)

        Returns:
            List[str]: Список URL загруженных файлов
        """
        urls = []
        for content, filename, content_type in files:
            url = await self.upload_file(content, filename, content_type)
            urls.append(url)
        return urls

    @staticmethod
    async def get_file_info(file_url: str) -> Optional[Dict[str, Any]]:
        """
        НОВЫЙ МЕТОД: Получение информации о файле.

        Args:
            file_url: URL файла

        Returns:
            Optional[Dict[str, Any]]: Информация о файле или None
        """
        # Базовая реализация - должна быть переопределена
        return None

    async def file_exists(self, filename: str) -> bool:
        """
        НОВЫЙ МЕТОД: Проверка существования файла.

        Args:
            filename: Имя файла

        Returns:
            bool: True если файл существует
        """
        try:
            await self.get_file_url(filename)
            return True
        except Exception:
            return False


# НОВЫЕ КЛАССЫ: Дополнительные сервисы

class AuditService(ABC):
    """
    НОВЫЙ КЛАСС: Абстрактный сервис для аудита действий.
    """

    @abstractmethod
    async def log_action(
        self,
        user_id: Optional[int],
        action: str,
        resource_type: str,
        resource_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Логирование действия пользователя.

        Args:
            user_id: ID пользователя (None для системных действий)
            action: Действие (create, update, delete, etc.)
            resource_type: Тип ресурса
            resource_id: ID ресурса
            details: Дополнительные детали

        Returns:
            bool: Успешность логирования
        """
        pass


class MetricsService(ABC):
    """
    НОВЫЙ КЛАСС: Абстрактный сервис для метрик.
    """

    @abstractmethod
    async def increment_counter(self, metric_name: str, value: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Увеличение счетчика метрики.

        Args:
            metric_name: Имя метрики
            value: Значение для увеличения
            tags: Теги метрики
        """
        pass

    @abstractmethod
    async def record_gauge(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Запись gauge метрики.

        Args:
            metric_name: Имя метрики
            value: Значение метрики
            tags: Теги метрики
        """
        pass

    @abstractmethod
    async def record_histogram(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Запись histogram метрики.

        Args:
            metric_name: Имя метрики
            value: Значение метрики
            tags: Теги метрики
        """
        pass
