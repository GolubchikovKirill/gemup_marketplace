"""
Модели базы данных.
Содержит все основные сущности: пользователи, продукты, заказы, транзакции, покупки прокси.
Используется SQLAlchemy 2.0 с typed annotations.
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, List

from sqlalchemy import (
    String, Text, Integer, Boolean, DateTime, ForeignKey,
    Table, Column, Index, CheckConstraint, UniqueConstraint,
    DECIMAL, func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Базовый класс для всех моделей."""
    pass


# Ассоциативные таблицы (используем Column для Table)
user_permissions = Table(
    "user_permissions",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True),
)

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
)


# Enums
class ProxyType(str, Enum):
    """Типы прокси."""
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"


class ProxyCategory(str, Enum):
    """Категории прокси."""
    DATACENTER = "datacenter"
    RESIDENTIAL = "residential"
    MOBILE = "mobile"
    NODEPAY = "nodepay"


class SessionType(str, Enum):
    """Типы сессий прокси."""
    STICKY = "sticky"
    ROTATING = "rotating"


class ProviderType(str, Enum):
    """Провайдеры прокси."""
    PROVIDER_711 = "provider_711"
    INTERNAL = "internal"


class OrderStatus(str, Enum):
    """Статусы заказов."""
    PENDING = "pending"
    PAID = "paid"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"
    REFUNDED = "refunded"


class TransactionType(str, Enum):
    """Типы транзакций."""
    DEPOSIT = "deposit"
    PURCHASE = "purchase"
    REFUND = "refund"
    WITHDRAWAL = "withdrawal"


class TransactionStatus(str, Enum):
    """Статусы транзакций."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


# ИСПРАВЛЕНО: Добавлен enum для ролей пользователей
class UserRole(str, Enum):
    """Роли пользователей."""
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"
    MANAGER = "manager"


class User(Base):
    """Модель пользователя."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Основная информация
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255))

    # Персональные данные
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))

    # Статусы
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true')
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    is_guest: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')

    # Добавлено поле role
    role: Mapped[UserRole] = mapped_column(default=UserRole.USER, server_default='user')

    # Финансы
    balance: Mapped[Decimal] = mapped_column(
        DECIMAL(precision=18, scale=8),
        default=Decimal('0.00000000'),
        server_default='0.00000000'
    )

    # Гостевые данные
    guest_session_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    guest_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Верификация и восстановление
    email_verification_token: Mapped[Optional[str]] = mapped_column(String(255))
    email_verification_expires: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    password_reset_token: Mapped[Optional[str]] = mapped_column(String(255))
    password_reset_expires: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Временные метки
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now()
    )

    # Relationships
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="user")
    transactions: Mapped[List["Transaction"]] = relationship("Transaction", back_populates="user")
    proxy_purchases: Mapped[List["ProxyPurchase"]] = relationship("ProxyPurchase", back_populates="user")
    cart_items: Mapped[List["ShoppingCart"]] = relationship("ShoppingCart", back_populates="user")

    # Добавлены недостающие relationships
    api_keys: Mapped[List["APIKey"]] = relationship("APIKey", back_populates="user")
    permissions: Mapped[List["Permission"]] = relationship(
        "Permission",
        secondary=user_permissions,
        back_populates="users"
    )
    roles: Mapped[List["Role"]] = relationship(
        "Role",
        secondary=user_roles,
        back_populates="users"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            '(is_guest = false AND email IS NOT NULL AND username IS NOT NULL AND hashed_password IS NOT NULL) OR '
            '(is_guest = true AND guest_session_id IS NOT NULL)',
            name='user_type_constraint'
        ),
        Index('idx_user_session', 'guest_session_id', 'guest_expires_at'),
        Index('idx_user_email_active', 'email', 'is_active'),
    )

    def __repr__(self) -> str:
        if self.is_guest:
            return f"<User(guest_session={self.guest_session_id})>"
        return f"<User(email={self.email}, username={self.username})>"


class ProxyProduct(Base):
    """Модель продукта прокси."""
    __tablename__ = "proxy_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Основная информация
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Технические характеристики
    proxy_type: Mapped[ProxyType] = mapped_column(nullable=False)
    proxy_category: Mapped[ProxyCategory] = mapped_column(nullable=False)
    session_type: Mapped[SessionType] = mapped_column(nullable=False)
    provider: Mapped[ProviderType] = mapped_column(nullable=False)

    # География
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    country_name: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[Optional[str]] = mapped_column(String(100))

    # Ценообразование
    price_per_proxy: Mapped[Decimal] = mapped_column(DECIMAL(precision=10, scale=2), nullable=False)
    price_per_gb: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(precision=10, scale=2))

    # Параметры продукта
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    min_quantity: Mapped[int] = mapped_column(Integer, default=1, server_default='1')
    max_quantity: Mapped[int] = mapped_column(Integer, default=1000, server_default='1000')

    # Технические ограничения
    max_threads: Mapped[Optional[int]] = mapped_column(Integer)
    bandwidth_limit_gb: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(precision=10, scale=2))
    uptime_guarantee: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(precision=5, scale=2))
    speed_mbps: Mapped[Optional[int]] = mapped_column(Integer)

    # Nodepay специфичные поля
    points_per_hour: Mapped[Optional[int]] = mapped_column(Integer)
    farm_efficiency: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(precision=5, scale=2))
    auto_claim: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    multi_account_support: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')

    # Инвентарь
    ip_pool_size: Mapped[Optional[int]] = mapped_column(Integer)
    stock_available: Mapped[int] = mapped_column(Integer, default=0, server_default='0')

    # Статусы
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true')
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')

    # Провайдер
    provider_product_id: Mapped[Optional[str]] = mapped_column(String(255))
    provider_metadata: Mapped[Optional[str]] = mapped_column(Text)

    # Временные метки
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now()
    )

    # Relationships
    order_items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="proxy_product")
    proxy_purchases: Mapped[List["ProxyPurchase"]] = relationship("ProxyPurchase", back_populates="proxy_product")
    cart_items: Mapped[List["ShoppingCart"]] = relationship("ShoppingCart", back_populates="proxy_product")

    # Constraints
    __table_args__ = (
        CheckConstraint('price_per_proxy > 0', name='positive_price'),
        CheckConstraint('duration_days > 0', name='positive_duration'),
        CheckConstraint('min_quantity > 0', name='positive_min_quantity'),
        CheckConstraint('max_quantity >= min_quantity', name='max_gte_min_quantity'),
        CheckConstraint('stock_available >= 0', name='non_negative_stock'),
        Index('idx_product_category_country', 'proxy_category', 'country_code'),
        Index('idx_product_active_featured', 'is_active', 'is_featured'),
        Index('idx_product_provider', 'provider', 'provider_product_id'),
    )

    def __repr__(self) -> str:
        return f"<ProxyProduct(name={self.name}, category={self.proxy_category}, country={self.country_code})>"


class Order(Base):
    """Модель заказа."""
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Финансовая информация
    total_amount: Mapped[Decimal] = mapped_column(DECIMAL(precision=18, scale=8), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", server_default="USD")

    # Статус и метаданные
    status: Mapped[OrderStatus] = mapped_column(default=OrderStatus.PENDING)
    payment_method: Mapped[Optional[str]] = mapped_column(String(50))

    # Временные ограничения
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Временные метки
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="orders")
    order_items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    transactions: Mapped[List["Transaction"]] = relationship("Transaction", back_populates="order")
    proxy_purchases: Mapped[List["ProxyPurchase"]] = relationship("ProxyPurchase", back_populates="order")

    # Constraints
    __table_args__ = (
        CheckConstraint('total_amount > 0', name='positive_total_amount'),
        Index('idx_order_user_status', 'user_id', 'status'),
        Index('idx_order_created', 'created_at'),
    )

    def __repr__(self) -> str:
        return f"<Order(number={self.order_number}, status={self.status}, amount={self.total_amount})>"


class OrderItem(Base):
    """Модель элемента заказа."""
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    proxy_product_id: Mapped[int] = mapped_column(Integer, ForeignKey("proxy_products.id"), nullable=False)

    # Количество и цены
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(DECIMAL(precision=10, scale=2), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(DECIMAL(precision=18, scale=8), nullable=False)

    # Параметры генерации
    generation_params: Mapped[Optional[str]] = mapped_column(Text)

    # Временные метки
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now()
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="order_items")
    proxy_product: Mapped["ProxyProduct"] = relationship("ProxyProduct", back_populates="order_items")

    # Constraints
    __table_args__ = (
        CheckConstraint('quantity > 0', name='positive_quantity'),
        CheckConstraint('unit_price > 0', name='positive_unit_price'),
        CheckConstraint('total_price > 0', name='positive_total_price'),
        Index('idx_order_item_order', 'order_id'),
    )

    def __repr__(self) -> str:
        return f"<OrderItem(order_id={self.order_id}, product_id={self.proxy_product_id}, qty={self.quantity})>"


class Transaction(Base):
    """Модель транзакции."""
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    transaction_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Финансовая информация
    amount: Mapped[Decimal] = mapped_column(DECIMAL(precision=18, scale=8), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", server_default="USD")

    # Тип и статус
    transaction_type: Mapped[TransactionType] = mapped_column(nullable=False)
    status: Mapped[TransactionStatus] = mapped_column(default=TransactionStatus.PENDING)

    # Связи
    order_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("orders.id"), index=True)
    parent_transaction_id: Mapped[Optional[str]] = mapped_column(String(255), ForeignKey("transactions.transaction_id"))

    # Метаданные
    description: Mapped[Optional[str]] = mapped_column(Text)
    provider_transaction_id: Mapped[Optional[str]] = mapped_column(String(255))
    provider_metadata: Mapped[Optional[str]] = mapped_column(Text)

    # Временные метки
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="transactions")
    order: Mapped[Optional["Order"]] = relationship("Order", back_populates="transactions")
    refund_transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction",
        foreign_keys=[parent_transaction_id],
        remote_side=[transaction_id]
    )

    # Constraints
    __table_args__ = (
        CheckConstraint('amount != 0', name='non_zero_amount'),
        Index('idx_transaction_user_type', 'user_id', 'transaction_type'),
        Index('idx_transaction_status_created', 'status', 'created_at'),
        Index('idx_transaction_provider', 'provider_transaction_id'),
    )

    def __repr__(self) -> str:
        return f"<Transaction(id={self.transaction_id}, type={self.transaction_type}, amount={self.amount})>"


class ProxyPurchase(Base):
    """Модель покупки прокси."""
    __tablename__ = "proxy_purchases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    proxy_product_id: Mapped[int] = mapped_column(Integer, ForeignKey("proxy_products.id"), nullable=False)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)

    # Данные прокси
    proxy_list: Mapped[str] = mapped_column(Text, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255))
    password: Mapped[Optional[str]] = mapped_column(String(255))

    # Статус и сроки
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true')
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # Использование
    traffic_used_gb: Mapped[Decimal] = mapped_column(
        DECIMAL(precision=10, scale=2),
        default=Decimal('0.00'),
        server_default='0.00'
    )
    last_used: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Провайдер
    provider_order_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    provider_metadata: Mapped[Optional[str]] = mapped_column(Text)

    # Временные метки
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="proxy_purchases")
    proxy_product: Mapped["ProxyProduct"] = relationship("ProxyProduct", back_populates="proxy_purchases")
    order: Mapped["Order"] = relationship("Order", back_populates="proxy_purchases")

    # Constraints
    __table_args__ = (
        CheckConstraint('traffic_used_gb >= 0', name='non_negative_traffic'),
        Index('idx_purchase_user_active', 'user_id', 'is_active'),
        Index('idx_purchase_expires', 'expires_at', 'is_active'),
        Index('idx_purchase_provider', 'provider_order_id'),
    )

    def __repr__(self) -> str:
        return f"<ProxyPurchase(id={self.id}, user_id={self.user_id}, active={self.is_active})>"


class ShoppingCart(Base):
    """Модель корзины покупок."""
    __tablename__ = "shopping_cart"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Пользователь или сессия
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    guest_session_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)

    # Товар
    proxy_product_id: Mapped[int] = mapped_column(Integer, ForeignKey("proxy_products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    # Параметры
    generation_params: Mapped[Optional[str]] = mapped_column(Text)

    # Истечение для гостевых корзин
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Временные метки
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now()
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="cart_items")
    proxy_product: Mapped["ProxyProduct"] = relationship("ProxyProduct", back_populates="cart_items")

    # Constraints
    __table_args__ = (
        CheckConstraint('quantity > 0', name='positive_cart_quantity'),
        CheckConstraint(
            '(user_id IS NOT NULL AND guest_session_id IS NULL) OR (user_id IS NULL AND guest_session_id IS NOT NULL)',
            name='user_or_session_cart'
        ),
        UniqueConstraint('user_id', 'proxy_product_id', name='unique_user_product'),
        UniqueConstraint('guest_session_id', 'proxy_product_id', name='unique_session_product'),
        Index('idx_cart_user', 'user_id', 'created_at'),
        Index('idx_cart_session', 'guest_session_id', 'expires_at'),
    )

    def __repr__(self) -> str:
        if self.user_id:
            return f"<ShoppingCart(user_id={self.user_id}, product_id={self.proxy_product_id}, qty={self.quantity})>"
        return f"<ShoppingCart(session={self.guest_session_id}, product_id={self.proxy_product_id}, qty={self.quantity})>"


# Дополнительные модели для системы разрешений
class Permission(Base):
    """Модель разрешения."""
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    category: Mapped[str] = mapped_column(String(50), default="general", server_default="general")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true')

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now()
    )

    # Relationships
    users: Mapped[List["User"]] = relationship(
        "User",
        secondary=user_permissions,
        back_populates="permissions"
    )

    def __repr__(self) -> str:
        return f"<Permission(name={self.name})>"


class Role(Base):
    """Модель роли."""
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true')

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now()
    )

    # Relationships
    users: Mapped[List["User"]] = relationship(
        "User",
        secondary=user_roles,
        back_populates="roles"
    )

    def __repr__(self) -> str:
        return f"<Role(name={self.name})>"


class APIKey(Base):
    """Модель API ключа."""
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Основная информация
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Описание и метаданные
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Разрешения и области действия (JSON)
    permissions: Mapped[Optional[str]] = mapped_column(Text)  # JSON array
    scopes: Mapped[Optional[str]] = mapped_column(Text)  # JSON array

    # Настройки
    rate_limit: Mapped[int] = mapped_column(Integer, default=1000, server_default='1000')
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true')

    # Временные данные
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    last_used: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Временные метки
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="api_keys")

    # Constraints
    __table_args__ = (
        CheckConstraint('rate_limit > 0', name='positive_rate_limit'),
        Index('idx_api_key_user_active', 'user_id', 'is_active'),
        Index('idx_api_key_expires', 'expires_at', 'is_active'),
    )

    def __repr__(self) -> str:
        return f"<APIKey(name={self.name}, user_id={self.user_id}, active={self.is_active})>"

