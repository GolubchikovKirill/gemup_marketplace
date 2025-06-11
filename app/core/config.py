"""
Конфигурация приложения с поддержкой Render.com

"""

import os
from typing import List, Optional

from pydantic import Field, field_validator, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ИСПРАВЛЕНИЕ: Правильный путь к .env файлу
DOTENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")

class Settings(BaseSettings):
    """Настройки приложения с поддержкой Render.com"""

    model_config = SettingsConfigDict(
        env_file=DOTENV_PATH,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Database settings (для локальной разработки)
    postgres_user: str = Field(default="gemup_user", description="PostgreSQL username")
    postgres_password: str = Field(default="", description="PostgreSQL password")
    postgres_db: str = Field(default="gemup_marketplace", description="PostgreSQL database name")
    postgres_host: str = Field(default="db", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, ge=1, le=65535, description="PostgreSQL port")
    database_echo: bool = Field(default=False, description="Enable SQLAlchemy query logging")

    # Database pool settings
    database_pool_size: int = Field(default=20, ge=1, le=100, description="Database connection pool size")
    database_max_overflow: int = Field(default=30, ge=0, le=100, description="Database max overflow connections")
    database_pool_timeout: int = Field(default=30, ge=1, le=300, description="Database pool timeout in seconds")
    database_pool_recycle: int = Field(default=3600, ge=300, description="Database connection recycle time")

    @computed_field
    @property
    def database_url(self) -> str:
        """ИСПРАВЛЕНО: Строка подключения к PostgreSQL с поддержкой Render"""

        # 1. ПРИОРИТЕТ: DATABASE_URL от Render (автоматически через fromDatabase)
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            # Render использует postgres://, SQLAlchemy нужен postgresql://
            if database_url.startswith("postgres://"):
                database_url = database_url.replace("postgres://", "postgresql://", 1)

            # Добавляем SSL для Render (обязательно согласно документации)
            if "sslmode" not in database_url:
                separator = "&" if "?" in database_url else "?"
                database_url = f"{database_url}{separator}sslmode=require"

            return database_url

        # 2. FALLBACK: Локальная разработка
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    # Redis settings
    redis_host: str = Field(default="redis", description="Redis host")
    redis_port: int = Field(default=6379, ge=1, le=65535, description="Redis port")
    redis_db: int = Field(default=0, ge=0, le=15, description="Redis database number")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    redis_max_connections: int = Field(default=20, ge=1, le=100, description="Redis max connections")
    redis_socket_timeout: int = Field(default=10, ge=1, description="Redis socket timeout")
    redis_socket_connect_timeout: int = Field(default=10, ge=1, description="Redis connect timeout")
    redis_retry_on_timeout: bool = Field(default=True, description="Redis retry on timeout")

    @computed_field
    @property
    def redis_url(self) -> str:
        """Строка подключения к Redis с правильной обработкой пароля"""
        if self.redis_password and self.redis_password.strip():
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # Application settings
    app_name: str = Field(default="Gemup Marketplace", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="development", description="Environment")

    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = ['development', 'staging', 'production', 'test']
        if v not in allowed:
            raise ValueError(f'Environment must be one of: {allowed}')
        return v

    # Security settings
    secret_key: str = Field(default="dev-secret-key-change-in-production-32-chars-minimum", min_length=32, description="Secret key for JWT")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, ge=1, le=43200, description="Access token expiration in minutes")

    @field_validator('secret_key')
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Валидация SECRET_KEY для безопасности"""
        if len(v) < 32:
            raise ValueError('Secret key must be at least 32 characters long')

        # Проверяем на небезопасные паттерны в production
        unsafe_patterns = ['secret', 'password', 'changeme', 'default', '123456', 'qwerty']
        v_lower = v.lower()

        for pattern in unsafe_patterns:
            if pattern in v_lower:
                # В development предупреждаем, в production блокируем
                env = os.getenv('ENVIRONMENT', 'development')
                if env == 'production':
                    raise ValueError(f'Secret key contains unsafe pattern: {pattern}')
                elif env == 'development':
                    print(f"🚨 Warning: SECRET_KEY contains unsafe pattern: {pattern}")

        return v

    # CORS settings
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8000,http://localhost:8080",
        description="Comma-separated list of allowed origins"
    )

    @computed_field
    @property
    def cors_origins_list(self) -> List[str]:
        """Список разрешенных CORS origin с валидацией"""
        origins = []
        for origin in self.cors_origins.split(","):
            origin = origin.strip()
            if origin and (origin.startswith('http://') or origin.startswith('https://')):
                origins.append(origin)
        return origins

    # Cache settings
    cache_default_ttl: int = Field(default=3600, ge=1, description="Default cache TTL in seconds")
    cache_session_ttl: int = Field(default=86400, ge=1, description="Session cache TTL in seconds")
    cache_cart_ttl: int = Field(default=7200, ge=1, description="Cart cache TTL in seconds")
    cache_proxy_ttl: int = Field(default=2592000, ge=1, description="Proxy cache TTL in seconds")

    # Rate limiting
    rate_limit_requests: int = Field(default=100, ge=1, description="Rate limit requests per window")
    rate_limit_window: int = Field(default=60, ge=1, description="Rate limit window in seconds")
    auth_rate_limit_requests: int = Field(default=5, ge=1, description="Auth rate limit requests")
    auth_rate_limit_window: int = Field(default=300, ge=1, description="Auth rate limit window")

    # Guest session settings
    guest_session_expire_hours: int = Field(default=24, ge=1, le=168, description="Guest session expiration in hours")
    guest_cart_expire_hours: int = Field(default=2, ge=1, le=24, description="Guest cart expiration in hours")

    # URL settings
    base_url: str = Field(default="http://localhost:8000", description="Base URL of the application")
    frontend_url: str = Field(default="http://localhost:3000", description="Frontend application URL")

    # Circuit breaker настройки
    circuit_breaker_failure_threshold: int = Field(default=5, ge=1, description="Circuit breaker failure threshold")
    circuit_breaker_recovery_timeout: int = Field(default=60, ge=1, description="Circuit breaker recovery timeout")
    circuit_breaker_expected_exception: str = Field(default="Exception", description="Expected exception for circuit breaker")

    # Worker settings
    worker_count: int = Field(default=4, ge=1, le=32, description="Worker count")
    max_connections_per_worker: int = Field(default=1000, ge=100, description="Max connections per worker")

    # Cryptomus payment settings
    cryptomus_api_key: str = Field(default="", description="Cryptomus API key")
    cryptomus_merchant_id: str = Field(default="", description="Cryptomus merchant ID")
    cryptomus_webhook_secret: str = Field(default="", description="Cryptomus webhook secret")
    cryptomus_base_url: str = Field(default="https://api.cryptomus.com/v1", description="Cryptomus API base URL")

    # 711 Proxy settings
    proxy_711_api_key: str = Field(default="", description="711 Proxy API key")
    proxy_711_username: Optional[str] = Field(default=None, description="711 Proxy username")
    proxy_711_password: Optional[str] = Field(default=None, description="711 Proxy password")
    proxy_711_base_url: str = Field(default="https://service.711proxy.com/api", description="711 Proxy API base URL")

    # ProxySeller settings
    proxy_seller_api_key: str = Field(default="", description="ProxySeller API key")
    proxy_seller_base_url: str = Field(default="https://proxy-seller.com/api", description="ProxySeller API base URL")

    # Lightning Proxies settings
    lightning_api_key: str = Field(default="", description="Lightning Proxies API key")
    lightning_base_url: str = Field(default="https://api.lightningproxies.com", description="Lightning Proxies API base URL")

    # GoProxy settings
    goproxy_api_key: str = Field(default="", description="GoProxy API key")
    goproxy_base_url: str = Field(default="https://api.goproxy.com", description="GoProxy API base URL")

    # Logging settings
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", description="Log format")
    log_file: Optional[str] = Field(default=None, description="Log file path")

    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f'Log level must be one of: {allowed}')
        return v_upper

    @computed_field
    @property
    def effective_log_level(self) -> str:
        """Эффективный уровень логирования на основе окружения и debug режима."""
        if self.is_development() and self.debug:
            return "DEBUG"
        elif self.is_test():
            return "WARNING"
        elif self.is_production():
            return self.log_level
        else:
            return self.log_level

    # API settings
    api_prefix: str = Field(default="/api/v1", description="API prefix")
    docs_url: Optional[str] = Field(default="/docs", description="Swagger docs URL")
    redoc_url: Optional[str] = Field(default="/redoc", description="ReDoc URL")

    @computed_field
    @property
    def effective_docs_url(self) -> Optional[str]:
        """Эффективный URL для Swagger документации."""
        if self.is_production():
            return None  # Отключаем в production
        return self.docs_url

    @computed_field
    @property
    def effective_redoc_url(self) -> Optional[str]:
        """Эффективный URL для ReDoc документации."""
        if self.is_production():
            return None  # Отключаем в production
        return self.redoc_url

    # Pagination settings
    default_page_size: int = Field(default=20, ge=1, le=100, description="Default page size for pagination")
    max_page_size: int = Field(default=100, ge=1, le=1000, description="Maximum page size for pagination")

    # Методы для проверки окружения
    def is_production(self) -> bool:
        """Проверка production окружения"""
        return self.environment.lower() == "production"

    def is_development(self) -> bool:
        """Проверка development окружения"""
        return self.environment.lower() == "development"

    def is_test(self) -> bool:
        """Проверка test окружения"""
        return self.environment.lower() == "test"

    def is_staging(self) -> bool:
        """Проверка staging окружения"""
        return self.environment.lower() == "staging"

    def get_enabled_proxy_providers(self) -> List[str]:
        """Получение списка включенных провайдеров прокси."""
        enabled = []

        # Проверяем наличие реальных ключей (не dev placeholders)
        if self.proxy_711_api_key and not self.proxy_711_api_key.startswith('test-dev'):
            enabled.append("711proxy")
        elif self.proxy_711_api_key:  # Dev placeholder
            enabled.append("711proxy")

        if self.proxy_seller_api_key and not self.proxy_seller_api_key.startswith('test-dev'):
            enabled.append("proxyseller")
        elif self.proxy_seller_api_key:
            enabled.append("proxyseller")

        if self.lightning_api_key and not self.lightning_api_key.startswith('test-dev'):
            enabled.append("lightning")
        elif self.lightning_api_key:
            enabled.append("lightning")

        if self.goproxy_api_key and not self.goproxy_api_key.startswith('test-dev'):
            enabled.append("goproxy")
        elif self.goproxy_api_key:
            enabled.append("goproxy")

        return enabled

    def validate_required_settings(self) -> List[str]:
        """Валидация обязательных настроек для production."""
        missing = []

        if self.is_production():
            # Critical settings
            if not self.secret_key or len(self.secret_key) < 32:
                missing.append("secret_key")

            # Database URL должен быть доступен в production
            if not os.getenv("DATABASE_URL"):
                missing.append("database_url")

            # Payment settings
            if not self.cryptomus_api_key:
                missing.append("cryptomus_api_key")

            # At least one proxy provider
            if not self.get_enabled_proxy_providers():
                missing.append("proxy_providers")

        return missing

    def log_configuration(self) -> None:
        """Логирование текущей конфигурации."""
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"🌍 Environment: {self.environment}")
        logger.info(f"🐛 Debug mode: {self.debug}")

        # Логируем тип подключения к БД
        if os.getenv("DATABASE_URL"):
            logger.info(f"🗄️ Database: Using Render DATABASE_URL (Internal)")
        else:
            logger.info(f"🗄️ Database: {self.postgres_host}:{self.postgres_port}/{self.postgres_db}")

        logger.info(f"🌐 CORS origins: {len(self.cors_origins_list)} configured")
        logger.info(f"🎯 Frontend URL: {self.frontend_url}")

        # Проверяем провайдеры
        enabled_providers = self.get_enabled_proxy_providers()
        logger.info(f"🔧 Enabled providers: {enabled_providers}")

        # Validation warnings
        missing = self.validate_required_settings()
        if missing:
            logger.warning(f"⚠️ Missing required settings: {missing}")

    @computed_field
    @property
    def is_docker(self) -> bool:
        """Определение запуска в Docker"""
        return self.postgres_host in ['db', 'database'] or self.redis_host in ['redis', 'redis-server']

    @computed_field
    @property
    def is_render(self) -> bool:
        """НОВОЕ: Определение запуска на Render"""
        return bool(os.getenv("DATABASE_URL")) and self.is_production()


# Создание глобального экземпляра настроек с error handling
try:
    settings = Settings()
except Exception as e:
    print(f"❌ Error loading settings: {e}")
    print("🔧 Using default settings for fallback")
    settings = Settings(_env_file=None)  # Fallback без .env файла

# Валидация при загрузке (только в development)
if settings.is_development():
    print(f"📁 .env file: {DOTENV_PATH}")
    print(f"📁 File exists: {os.path.exists(DOTENV_PATH)}")
    print(f"🌍 Environment: {settings.environment}")
    print(f"🔧 Enabled providers: {settings.get_enabled_proxy_providers()}")
