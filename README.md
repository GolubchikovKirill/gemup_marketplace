# Gemup Marketplace

Полнофункциональный маркетплейс для продажи цифровых товаров (прокси-серверы) с поддержкой гостевых пользователей, системой баланса и интеграцией с различными провайдерами прокси.

## 📋 Описание проекта

Gemup Marketplace - это современный backend API для маркетплейса прокси-серверов, построенный на FastAPI с асинхронной архитектурой. Проект поддерживает как зарегистрированных пользователей, так и гостевые сессии, обеспечивая гибкую систему покупок и управления цифровыми товарами.

## 🏗️ Архитектура

### Технологический стек
- **Backend**: FastAPI 0.115+ с асинхронной поддержкой
- **База данных**: PostgreSQL 15 с SQLAlchemy 2.0 (async)
- **Кэширование**: Redis 7 с расширенным функционалом
- **Миграции**: Alembic для управления схемой БД
- **Валидация**: Pydantic v2 для схем данных
- **Контейнеризация**: Docker с multi-stage builds
- **Пакетный менеджер**: uv для быстрой установки зависимостей

### Основные компоненты
app/
├── core/ # Основные компоненты системы
│ ├── config.py # Конфигурация приложения
│ ├── db.py # Подключение к базе данных
│ ├── redis.py # Redis клиент
│ ├── auth.py # Система аутентификации
│ ├── dependencies.py # FastAPI зависимости
│ ├── middleware.py # Middleware компоненты
│ ├── exceptions.py # Обработка исключений
│ └── migrations.py # Управление миграциями
├── models/ # SQLAlchemy модели
├── schemas/ # Pydantic схемы
├── crud/ # CRUD операции
├── routes/ # API роуты
└── services/ # Бизнес-логика (в разработке)

text

## 🗄️ Модель данных

### Основные сущности

#### **User** - Пользователи системы
- Поддержка зарегистрированных и гостевых пользователей
- Система баланса с поддержкой Decimal для точности
- Автоматическое истечение гостевых сессий
- Конвертация гостевых пользователей в зарегистрированных

#### **ProxyProduct** - Товары прокси
- Различные типы прокси (HTTP, SOCKS5)
- Поддержка множественных провайдеров
- Географическая привязка (страна, город)
- Гибкая система ценообразования
- Управление остатками на складе

#### **ShoppingCart** - Корзина покупок
- Поддержка как зарегистрированных, так и гостевых пользователей
- Автоматическое истечение гостевых корзин
- Параметры генерации прокси

#### **Order/OrderItem** - Система заказов
- Уникальные номера заказов
- Детализация по позициям
- Автоматическое истечение неоплаченных заказов
- Интеграция с системой платежей

#### **Transaction** - Финансовые операции
- Поддержка различных типов транзакций
- Интеграция с внешними платежными системами
- Отслеживание статусов платежей
- Метаданные провайдеров

#### **ProxyPurchase** - Купленные прокси
- Хранение списков прокси в JSON формате
- Отслеживание использования трафика
- Управление сроками действия
- Связь с заказами и продуктами

## 🔐 Система аутентификации

### JWT токены для зарегистрированных пользователей
Создание токена
access_token = auth_handler.create_access_token(
data={"sub": str(user.id)},
expires_delta=timedelta(minutes=30)
)


### Гостевые сессии
- Автоматическое создание гостевых пользователей
- Сессии с истечением срока действия
- Возможность конвертации в зарегистрированных пользователей
- Сохранение корзины и истории

### Гибкая система dependencies
Различные уровни доступа
get_current_user() # Может вернуть None
get_current_user_or_create_guest() # Всегда возвращает пользователя
get_current_registered_user() # Только зарегистрированные
get_optional_user() # Опциональный без создания гостя


## 🛣️ API Endpoints

### Аутентификация (`/api/v1/auth/`)
- `POST /register` - Регистрация нового пользователя
- `POST /login` - Авторизация (form-data)
- `POST /login/json` - Авторизация (JSON)
- `POST /logout` - Выход из системы
- `GET /me` - Информация о текущем пользователе

### Пользователи (`/api/v1/users/`)
- `GET /me` - Профиль пользователя (включая гостевых)
- `PUT /me` - Обновление профиля
- `GET /balance` - Получение баланса
- `POST /convert-guest` - Конвертация гостевого пользователя

### Система здоровья
- `GET /` - Основная информация о API
- `GET /health` - Проверка состояния сервисов

## 🔄 CRUD операции

Все CRUD операции построены на базовом классе с асинхронной поддержкой:

class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
async def get(self, db: AsyncSession, id: Any) -> Optional[ModelType]
async def get_multi(self, db: AsyncSession, *, skip: int = 0, limit: int = 100)
async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType)
async def update(self, db: AsyncSession, *, db_obj: ModelType, obj_in: UpdateSchemaType)
async def remove(self, db: AsyncSession, *, id: int)


### Специализированные CRUD
- **UserCRUD**: Управление пользователями, аутентификация, конвертация гостей
- **ProxyProductCRUD**: Каталог продуктов, фильтрация, управление остатками
- **ShoppingCartCRUD**: Корзина покупок, расчет итогов, очистка просроченных
- **OrderCRUD**: Заказы, статусы, создание из корзины
- **TransactionCRUD**: Финансовые операции, обновление статусов

## 🗃️ Кэширование и Redis

Расширенный Redis клиент с специализированными методами:

### Основные возможности
- Пул соединений для производительности
- Автоматическая обработка ошибок
- JSON операции для сложных данных
- Rate limiting для защиты API

### Специализированные методы
Кэширование сессий
await redis.cache_user_session(session_id, user_data, expire_hours=24)

Кэширование корзин
await redis.cache_cart(cart_id, cart_data, expire_hours=2)

Кэширование списков прокси
await redis.cache_proxy_list(purchase_id, proxy_data, expire_days=30)

Rate limiting
await redis.rate_limit_check(identifier, limit=100, window_seconds=3600)


## 🐳 Docker конфигурация

### Multi-stage builds
- **Base stage**: Общие зависимости
- **Development stage**: Полная среда разработки с hot reload
- **Production stage**: Оптимизированный образ для продакшена

### Docker Compose
- **Основной**: `docker-compose.yml` для продакшена
- **Разработка**: `docker-compose.dev.yml` с watch и hot reload
- **Volumes**: Персистентные данные для PostgreSQL и Redis
- **Health checks**: Автоматическая проверка готовности сервисов

### Удобные команды через Makefile
make dev # Запуск для разработки
make dev-watch # Запуск с Docker Compose Watch
make prod # Запуск для продакшена
make logs # Просмотр логов
make shell # Подключение к контейнеру
make migrate # Применение миграций


## ⚙️ Конфигурация

### Переменные окружения
Все настройки через `.env` файл с валидацией через Pydantic:

База данных
POSTGRES_USER=gemup_user
POSTGRES_PASSWORD=secure_password
POSTGRES_DB=gemup_marketplace

Безопасность
SECRET_KEY=your-secret-key-32-chars-minimum
ACCESS_TOKEN_EXPIRE_MINUTES=30

Redis
REDIS_HOST=redis
REDIS_PORT=6379

Приложение
DEBUG=true
ENVIRONMENT=development
LOG_LEVEL=INFO


### Автоматическая валидация
- Проверка длины секретного ключа
- Валидация окружения (development/staging/production)
- Автоматическое формирование URL подключений
- Computed fields для динамических значений

## 🔧 Миграции базы данных

### Alembic интеграция
- Автоматическое выполнение миграций при старте приложения
- Асинхронная поддержка для совместимости с FastAPI
- Автоматическая генерация миграций из изменений моделей

Создание миграции
make create-migration msg="Описание изменений"

Применение миграций
make migrate

Просмотр истории
docker compose exec web alembic history


## 📝 Логирование

### Структурированное логирование
- Настраиваемый уровень логирования через переменные окружения
- Отдельные логи для компонентов (Redis, миграции, аутентификация)
- Поддержка эмодзи для лучшей читаемости
- Интеграция с Uvicorn логами

### Примеры логов
2025-05-26 13:46:33,195 - app.core.main - INFO - 🚀 Запуск приложения...
2025-05-26 13:46:33,199 - app.core.redis - INFO - ✅ Redis connection established successfully


## 🚀 Запуск проекта

### Требования
- Docker и Docker Compose
- Make (опционально, для удобства)

### Быстрый старт
Клонирование репозитория
git clone <repository-url>
cd gemup-marketplace

Настройка переменных окружения
cp .env.example .env

Отредактируйте .env файл
Запуск для разработки
make dev

Или без Make
docker compose -f docker-compose.dev.yml up --build


### Доступ к сервисам
- **API**: http://localhost:8000
- **Swagger документация**: http://localhost:8000/docs
- **ReDoc документация**: http://localhost:8000/redoc
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379


## 🤝 Разработка

### Структура коммитов
Проект следует принципам чистой архитектуры с разделением ответственности:
- **Models**: Определение структуры данных
- **Schemas**: Валидация и сериализация
- **CRUD**: Операции с базой данных
- **Routes**: HTTP эндпоинты
- **Services**: Бизнес-логика (в разработке)

### Качество кода
Линтинг
make lint

Форматирование
make format

Проверка типов
make typecheck

Тесты
make test

