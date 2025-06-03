"""
Конфигурация приложения.

Централизованное управление настройками приложения с использованием Pydantic Settings.
Поддерживает загрузку из переменных окружения и .env файлов.
"""

import os
from typing import List, Optional
from pydantic import Field, field_validator, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

DOTENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")


class Settings(BaseSettings):
    """
    Настройки приложения.

    Автоматически загружает значения из переменных окружения
    и .env файла. Обеспечивает валидацию и типизацию настроек.
    """

    model_config = SettingsConfigDict(
        env_file=DOTENV_PATH,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Database settings
    postgres_user: str = Field(..., description="PostgreSQL username")
    postgres_password: str = Field(..., description="PostgreSQL password")
    postgres_db: str = Field(..., description="PostgreSQL database name")
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, ge=1, le=65535, description="PostgreSQL port")
    database_echo: bool = Field(default=False, description="Enable SQLAlchemy query logging")

    @computed_field
    @property
    def database_url(self) -> str:
        """Строка подключения к PostgreSQL"""
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    # Redis settings
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, ge=1, le=65535, description="Redis port")
    redis_db: int = Field(default=0, ge=0, le=15, description="Redis database number")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    redis_max_connections: int = Field(default=20, ge=1, le=100, description="Redis max connections")
    redis_socket_timeout: int = Field(default=5, ge=1, description="Redis socket timeout")
    redis_socket_connect_timeout: int = Field(default=5, ge=1, description="Redis connect timeout")

    @computed_field
    @property
    def redis_url(self) -> str:
        """Строка подключения к Redis"""
        if self.redis_password:
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
    secret_key: str = Field(..., min_length=32, description="Secret key for JWT")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30,
        ge=1,
        le=43200,
        description="Access token expiration in minutes"
    )

    # CORS settings
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8000,http://localhost:8080",
        description="Comma-separated list of allowed origins"
    )

    @computed_field
    @property
    def cors_origins_list(self) -> List[str]:
        """Список разрешенных CORS origin"""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    # Cache settings
    cache_default_ttl: int = Field(default=3600, ge=1, description="Default cache TTL in seconds")
    cache_session_ttl: int = Field(default=86400, ge=1, description="Session cache TTL in seconds")
    cache_cart_ttl: int = Field(default=7200, ge=1, description="Cart cache TTL in seconds")
    cache_proxy_ttl: int = Field(default=2592000, ge=1, description="Proxy cache TTL in seconds")

    # Rate limiting
    rate_limit_requests: int = Field(default=100, ge=1, description="Rate limit requests per window")
    rate_limit_window: int = Field(default=3600, ge=1, description="Rate limit window in seconds")

    # Guest session settings
    guest_session_expire_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Guest session expiration in hours"
    )
    guest_cart_expire_hours: int = Field(
        default=2,
        ge=1,
        le=24,
        description="Guest cart expiration in hours"
    )

    # URL settings
    base_url: str = Field(
        default="http://localhost:8080",
        description="Base URL of the application"
    )
    frontend_url: str = Field(
        default="http://localhost:3000",
        description="Frontend application URL"
    )

    # Cryptomus payment settings
    cryptomus_api_key: str = Field(default="", description="Cryptomus API key")
    cryptomus_merchant_id: str = Field(default="", description="Cryptomus merchant ID")
    cryptomus_webhook_secret: str = Field(default="", description="Cryptomus webhook secret")
    cryptomus_base_url: str = Field(
        default="https://api.cryptomus.com/v1",
        description="Cryptomus API base URL"
    )

    # 711 Proxy settings
    proxy_711_api_key: str = Field(default="", description="711 Proxy API key")
    proxy_711_username: Optional[str] = Field(default=None, description="711 Proxy username")
    proxy_711_password: Optional[str] = Field(default=None, description="711 Proxy password")
    proxy_711_base_url: str = Field(
        default="https://service.711proxy.com/api",
        description="711 Proxy API base URL"
    )

    # ProxySeller settings
    proxy_seller_api_key: str = Field(default="", description="ProxySeller API key")
    proxy_seller_base_url: str = Field(
        default="https://proxy-seller.com/api",
        description="ProxySeller API base URL"
    )

    # Lightning Proxies settings
    lightning_api_key: str = Field(default="", description="Lightning Proxies API key")
    lightning_base_url: str = Field(
        default="https://api.lightningproxies.com",
        description="Lightning Proxies API base URL"
    )

    # GoProxy settings
    goproxy_api_key: str = Field(default="", description="GoProxy API key")
    goproxy_base_url: str = Field(
        default="https://api.goproxy.com",
        description="GoProxy API base URL"
    )

    # Logging settings
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format"
    )

    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f'Log level must be one of: {allowed}')
        return v_upper

    # ИСПРАВЛЕНО: Добавлен effective_log_level
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

    # ИСПРАВЛЕНО: Добавлены effective URLs для документации
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

    # API settings
    api_prefix: str = Field(default="/api/v1", description="API prefix")
    docs_url: Optional[str] = Field(default="/docs", description="Swagger docs URL")
    redoc_url: Optional[str] = Field(default="/redoc", description="ReDoc URL")

    # Pagination settings
    default_page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Default page size for pagination"
    )
    max_page_size: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum page size for pagination"
    )

    # Методы для проверки окружения
    def is_production(self) -> bool:
        """Проверка production окружения"""
        return self.environment == "production"

    def is_development(self) -> bool:
        """Проверка development окружения"""
        return self.environment == "development"

    def is_test(self) -> bool:
        """Проверка test окружения"""
        return self.environment == "test"

    def is_staging(self) -> bool:
        """Проверка staging окружения"""
        return self.environment == "staging"

    # ИСПРАВЛЕНО: Добавлен метод для получения включенных провайдеров
    def get_enabled_proxy_providers(self) -> List[str]:
        """Получение списка включенных провайдеров прокси."""
        enabled = []

        if self.proxy_711_api_key:
            enabled.append("711proxy")
        if self.proxy_seller_api_key:
            enabled.append("proxyseller")
        if self.lightning_api_key:
            enabled.append("lightning")
        if self.goproxy_api_key:
            enabled.append("goproxy")

        return enabled

    # ИСПРАВЛЕНО: Добавлен метод валидации обязательных настроек
    def validate_required_settings(self) -> List[str]:
        """Валидация обязательных настроек для production."""
        missing = []

        if self.is_production():
            if not self.secret_key or len(self.secret_key) < 32:
                missing.append("secret_key")
            if not self.postgres_user:
                missing.append("postgres_user")
            if not self.postgres_password:
                missing.append("postgres_password")
            if not self.postgres_db:
                missing.append("postgres_db")

        return missing


# Создание глобального экземпляра настроек
settings = Settings()

# Валидация при загрузке (только в development)
if settings.is_development():
    print(f"📁 Путь к .env файлу: {DOTENV_PATH}")
    print(f"📁 Файл существует: {os.path.exists(DOTENV_PATH)}")
    print(f"🌍 Окружение: {settings.environment}")
    print(f"📊 Эффективный уровень логирования: {settings.effective_log_level}")
