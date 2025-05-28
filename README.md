# Gemup Marketplace

Полнофункциональный маркетплейс для продажи цифровых товаров (прокси-серверы) с поддержкой гостевых пользователей, системой баланса, интеграцией с платежными системами и провайдерами прокси.

## 📋 Описание проекта

Gemup Marketplace - это современный backend API для маркетплейса прокси-серверов, построенный на FastAPI с асинхронной архитектурой. Проект поддерживает как зарегистрированных пользователей, так и гостевые сессии, обеспечивая полный цикл покупки и управления цифровыми товарами с автоматической активацией прокси.

## 🏗️ Архитектура

### Технологический стек
- **Backend**: FastAPI 0.115+ с асинхронной поддержкой
- **База данных**: PostgreSQL 15 с SQLAlchemy 2.0 (async)
- **Кэширование**: Redis 7 с расширенным функционалом
- **Миграции**: Alembic для управления схемой БД
- **Валидация**: Pydantic v2 для схем данных
- **Контейнеризация**: Docker с multi-stage builds
- **Пакетный менеджер**: uv для быстрой установки зависимостей
- **Тестирование**: pytest с 132 тестами и полным покрытием

### Основные компоненты
````
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
├── services/ # Бизнес-логика
├── integrations/ # Внешние интеграции
│ ├── cryptomus.py # Платежная система Cryptomus
│ └── proxy_711.py # Интеграция с 711 Proxy
└── tests/ # 132 теста (unit + integration)
````

## 🗄️ Модель данных

### Основные сущности

#### **User** - Пользователи системы
- Поддержка зарегистрированных и гостевых пользователей
- Система баланса с поддержкой Decimal для точности
- Автоматическое истечение гостевых сессий
- Конвертация гостевых пользователей в зарегистрированных

#### **ProxyProduct** - Товары прокси
- Различные типы прокси (HTTP, HTTPS, SOCKS4, SOCKS5)
- Поддержка множественных провайдеров (711, ProxySeller, Lightning, GoProxy)
- Географическая привязка (страна, город)
- Гибкая система ценообразования
- Управление остатками на складе

#### **ShoppingCart** - Корзина покупок
- Поддержка как зарегистрированных, так и гостевых пользователей
- Автоматическое истечение гостевых корзин
- Параметры генерации прокси
- Автоматический расчет итоговой суммы

#### **Order/OrderItem** - Система заказов
- Уникальные номера заказов
- Детализация по позициям
- Полный lifecycle управления статусами
- Автоматическое истечение неоплаченных заказов
- Интеграция с системой платежей и активацией прокси

#### **Transaction** - Финансовые операции
- Поддержка различных типов транзакций (пополнение, покупка, возврат)
- Интеграция с Cryptomus платежной системой
- Отслеживание статусов платежей
- Автоматическое обновление баланса при успешной оплате

#### **ProxyPurchase** - Купленные прокси
- Хранение списков прокси с учетными данными
- Отслеживание использования трафика
- Управление сроками действия
- Связь с заказами и продуктами
- Система продления прокси

## 🔐 Система аутентификации

### JWT токены для зарегистрированных пользователей

Создание токена
```
access_token = auth_handler.create_access_token(data={"sub": str(user.i)},
expires_delta=timedelta(min)
```


### Гостевые сессии
- Автоматическое создание гостевых пользователей
- Сессии с истечением срока действия
- Возможность конвертации в зарегистрированных пользователей
- Сохранение корзины и истории

### Гибкая система dependencies

Различные уровни доступа
````
get_current_user() # Может вернуть None
get_current_user_or_create_guest() # Всегда возвращает пользователя
get_current_registered_user() # Только зарегистрированные
get_optional_user() # Опциональный без создания гостя
````


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

### Продукты (`/api/v1/products/`)
- `GET /` - Список продуктов с фильтрацией и пагинацией
- `GET /{product_id}` - Детальная информация о продукте
- `GET /{product_id}/availability` - Проверка доступности товара
- `GET /meta/countries` - Список доступных стран
- `GET /meta/cities/{country_code}` - Города по стране

### Корзина (`/api/v1/cart/`)
- `GET /` - Содержимое корзины
- `POST /items` - Добавление товара в корзину
- `PUT /items/{item_id}` - Обновление количества
- `DELETE /items/{item_id}` - Удаление товара
- `DELETE /` - Очистка корзины

### Заказы (`/api/v1/orders/`)
- `POST /` - Создание заказа из корзины
- `GET /` - Список заказов пользователя
- `GET /{order_id}` - Детали заказа
- `GET /number/{order_number}` - Заказ по номеру
- `PUT /{order_id}/status` - Обновление статуса
- `POST /{order_id}/cancel` - Отмена заказа
- `GET /summary` - Сводка по заказам
- `GET /public/{order_number}` - Публичная информация о заказе

### Платежи (`/api/v1/payments/`)
- `POST /create` - Создание платежа для пополнения баланса
- `GET /status/{transaction_id}` - Статус платежа
- `GET /history` - История транзакций
- `POST /webhook/cryptomus` - Webhook от Cryptomus
- `POST /test-webhook` - Тестовый webhook

### Прокси (`/api/v1/proxies/`)
- `GET /my` - Список купленных прокси
- `POST /{purchase_id}/generate` - Генерация списка прокси
- `GET /{purchase_id}/download` - Скачивание прокси файла
- `POST /{purchase_id}/extend` - Продление прокси
- `GET /expiring` - Прокси, которые скоро истекают

### Система здоровья
- `GET /` - Основная информация о API
- `GET /health` - Проверка состояния сервисов

## 💰 Платежная система

### Интеграция с Cryptomus
- Создание платежей для пополнения баланса
- Автоматическая обработка webhook уведомлений
- Безопасная проверка подписей платежей
- Поддержка различных криптовалют
- Автоматическое пополнение баланса при успешной оплате

Создание платежа
````
payment_result = await cryptomus_api.create_payment(
amount=Decimal('50.00'),
currency="USD",
order_id="unique_order_id",
callback_url="https://your-domain.com/webhook"
)
````


### Система баланса
- Точные вычисления с Decimal
- История всех транзакций
- Автоматическое списание при покупке
- Возврат средств при отмене заказов

## 🌐 Интеграция с провайдерами прокси

### 711 Proxy API
- Автоматическая покупка прокси после оплаты заказа
- Получение списков прокси с учетными данными
- Продление срока действия прокси
- Мониторинг статуса заказов

Покупка прокси
````
proxy_data = await proxy_711_api.purchase_proxies(
product_id="1",
quantity=10,
duration_days=30,
country_code="US"
)
````


### Система генерации прокси
- Поддержка различных форматов вывода:
  - `ip:port:user:pass`
  - `user:pass@ip:port`
  - `ip:port`
- Скачивание списков в текстовых файлах
- Копирование в буфер обмена

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
- **ProxyPurchaseCRUD**: Управление купленными прокси, продление

## 🏢 Бизнес-логика (Services)

### Архитектура сервисов
Все сервисы наследуются от базового класса с валидацией бизнес-правил:

````
class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
def init(self, model: Type[ModelType]):
self.model = model
self.business_rules = BusinessRuleValidator()
````
``
async def validate_business_rules(self, data: dict, db: AsyncSession) -> bool
``


### Реализованные сервисы
- **OrderService**: Управление заказами, активация прокси после оплаты
- **PaymentService**: Обработка платежей, интеграция с Cryptomus
- **ProxyService**: Активация и управление прокси, генерация списков
- **ProductService**: Управление каталогом, фильтрация, поиск

## 🗃️ Кэширование и Redis

Расширенный Redis клиент с специализированными методами:

### Основные возможности
- Пул соединений для производительности
- Автоматическая обработка ошибок
- JSON операции для сложных данных
- Rate limiting для защиты API

### Специализированные методы

Кэширование сессий

``
await redis.cache_user_session(session_id, user_data, expire_hours=24)
``

Кэширование корзин

``
await redis.cache_cart(cart_id, cart_data, expire_hours=2)
``

Кэширование списков прокси

``
await redis.cache_proxy_list(purchase_id, proxy_data, expire_days=30)
``

Rate limiting

``
await redis.rate_limit_check(identifier, limit=100, window_seconds=3600)
``


## 🧪 Тестирование

### Полное покрытие тестами
- **132 теста** покрывают весь функционал
- **Unit тесты** для всех сервисов и CRUD операций
- **Integration тесты** для API эндпоинтов
- **Моки** для внешних интеграций (Cryptomus, 711 Proxy)

### Структура тестов

````
tests/
├── unit/ # Unit тесты
│ ├── test_auth.py
│ ├── test_order_service.py
│ ├── test_payment_service.py
│ ├── test_proxy_service.py
│ └── test_cryptomus_api.py
├── integration/ # Integration тесты
│ ├── test_auth_routes.py
│ ├── test_orders_routes.py
│ ├── test_payments_routes.py
│ └── test_proxies_routes.py
└── conftest.py # Общие фикстуры
````


### Запуск тестов

*Все тесты*
`make test`

*Unit тесты*
`make test-unit`

*Integration тесты*
`make test-integration`

*С покрытием кода*
`make test-cov`


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

``make dev # Запуск для разработки``

``make dev-watch # Запуск с Docker Compose Watch``

``make prod # Запуск для продакшена``

``make logs # Просмотр логов``

``make shell # Подключение к контейнеру``

``make migrate # Применение миграций``

``make test # Запуск тестов``


## ⚙️ Конфигурация

### Переменные окружения
Все настройки через `.env` файл с валидацией через Pydantic:

**База данных**

````
POSTGRES_USER=gemup_user

POSTGRES_PASSWORD=secure_password

POSTGRES_DB=gemup_marketplace
````

**Безопасность**

````
SECRET_KEY=your-secret-key-32-chars-minimum

ACCESS_TOKEN_EXPIRE_MINUTES=30
````

**Redis**

````
REDIS_HOST=redis

REDIS_PORT=6379
````

**Cryptomus**

````
CRYPTOMUS_API_KEY=your_cryptomus_api_key

CRYPTOMUS_MERCHANT_ID=your_merchant_id

CRYPTOMUS_WEBHOOK_SECRET=your_webhook_secret
````

**711 Proxy**

````
PROVIDER_711_API_KEY=your_711_api_key

PROVIDER_711_BASE_URL=https://api.711proxy.com
````

**Приложение**

````
DEBUG=true

ENVIRONMENT=development

LOG_LEVEL=INFO

BASE_URL=http://localhost:8000

FRONTEND_URL=http://localhost:3000
````

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

*Создание миграции*
`make create-migration msg="Описание изменений"`

*Применение миграций*
`make migrate`

*Просмотр истории*
`docker compose exec web alembic history`


## 📝 Логирование

### Структурированное логирование
- Настраиваемый уровень логирования через переменные окружения
- Отдельные логи для компонентов (Redis, миграции, аутентификация)
- Поддержка эмодзи для лучшей читаемости
- Интеграция с Uvicorn логами

### Примеры логов

2025-05-28 19:37:33,195 - app.core.main - INFO - 🚀 Запуск приложения...
2025-05-28 19:37:33,199 - app.core.redis - INFO - ✅ Redis connection established successfully
2025-05-28 19:37:33,205 - app.services.payment - INFO - 💰 Payment created for user 123: 50.00 USD
2025-05-28 19:37:33,210 - app.services.proxy - INFO - 🌐 Activated 10 proxies for order ORD-20250528-ABC123


## 🚀 Запуск проекта

### Требования
- Docker и Docker Compose
- Make (опционально, для удобства)

### Быстрый старт

**Клонирование репозитория**
`git clone <repository-url>`
`cd gemup-marketplace`

**Настройка переменных окружения**
`cp .env.example .env`

**Отредактируйте .env файл**
`Запуск для разработки`
`make dev`

**Или без Make**
`docker compose -f docker-compose.dev.yml up --build`

### Доступ к сервисам
- **API**: http://localhost:8000
- **Swagger документация**: http://localhost:8000/docs
- **ReDoc документация**: http://localhost:8000/redoc
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## 📊 Метрики проекта

- **132 теста** - 100% успешных
- **15+ API эндпоинтов** - полный CRUD функционал
- **8 основных моделей** - покрывают весь бизнес-процесс
- **3 внешние интеграции** - Cryptomus, 711 Proxy, Redis
- **5 сервисов** - бизнес-логика с валидацией
- **Docker ready** - готов к деплою в production

---