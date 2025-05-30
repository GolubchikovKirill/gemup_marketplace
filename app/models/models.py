from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from enum import Enum as PyEnum

from sqlalchemy import String, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


# Енумы для типов данных
class ProxyType(str, PyEnum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"


class ProxyCategory(str, PyEnum):
    RESIDENTIAL = "residential"
    DATACENTER = "datacenter"
    ISP = "isp"
    NODEPAY = "nodepay"
    GRASS = "grass"


class SessionType(str, PyEnum):
    STICKY = "sticky"
    ROTATING = "rotating"


class OrderStatus(str, PyEnum):
    PENDING = "pending"
    PAID = "paid"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"
    REFUNDED = "refunded"


class TransactionType(str, PyEnum):
    DEPOSIT = "deposit"
    PURCHASE = "purchase"
    REFUND = "refund"
    WITHDRAWAL = "withdrawal"


class TransactionStatus(str, PyEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProviderType(str, PyEnum):
    PROVIDER_711 = "711"
    PROXY_SELLER = "proxy_seller"
    LIGHTNING = "lightning"
    GOPROXY = "goproxy"


# Основные модели

class User(Base):
    """Модель пользователя (включая гостевых через cookies)"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255))
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))

    balance: Mapped[Decimal] = mapped_column(default=Decimal('0.00000000'))

    is_active: Mapped[bool] = mapped_column(default=True, server_default='true')
    is_verified: Mapped[bool] = mapped_column(default=False, server_default='false')
    is_guest: Mapped[bool] = mapped_column(default=False, server_default='false')

    guest_session_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    guest_expires_at: Mapped[Optional[datetime]] = mapped_column()

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    last_login: Mapped[Optional[datetime]] = mapped_column()

    # Relationships
    orders: Mapped[List["Order"]] = relationship(back_populates="user")
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="user")
    proxy_purchases: Mapped[List["ProxyPurchase"]] = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', is_guest={self.is_guest})>"


class ProxyProduct(Base):
    """Продукты прокси от различных провайдеров"""
    __tablename__ = "proxy_products"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)

    proxy_type: Mapped[ProxyType] = mapped_column()
    proxy_category: Mapped[ProxyCategory] = mapped_column()
    session_type: Mapped[SessionType] = mapped_column()
    provider: Mapped[ProviderType] = mapped_column()

    country_code: Mapped[str] = mapped_column(String(2))
    country_name: Mapped[str] = mapped_column(String(100))
    city: Mapped[Optional[str]] = mapped_column(String(100))

    # Ценообразование
    price_per_proxy: Mapped[Decimal] = mapped_column()
    price_per_gb: Mapped[Optional[Decimal]] = mapped_column()

    min_quantity: Mapped[int] = mapped_column(default=1)
    max_quantity: Mapped[int] = mapped_column(default=1000)

    duration_days: Mapped[int] = mapped_column()
    max_threads: Mapped[int] = mapped_column(default=1)
    bandwidth_limit_gb: Mapped[Optional[int]] = mapped_column()

    # Характеристики по категориям
    uptime_guarantee: Mapped[Optional[Decimal]] = mapped_column()
    speed_mbps: Mapped[Optional[int]] = mapped_column()
    ip_pool_size: Mapped[Optional[int]] = mapped_column()

    # Nodepay и Grass
    points_per_hour: Mapped[Optional[int]] = mapped_column()  # Очки в час для фарминга
    farm_efficiency: Mapped[Optional[Decimal]] = mapped_column()  # Эффективность фарминга в %
    auto_claim: Mapped[bool] = mapped_column(default=False)  # Автоматический клейм
    multi_account_support: Mapped[bool] = mapped_column(default=False)  # Поддержка мульти-аккаунтов

    is_active: Mapped[bool] = mapped_column(default=True, server_default='true')
    is_featured: Mapped[bool] = mapped_column(default=False, server_default='false')
    stock_available: Mapped[int] = mapped_column(default=0)

    provider_product_id: Mapped[Optional[str]] = mapped_column(String(255))
    provider_metadata: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # Relationships
    order_items: Mapped[List["OrderItem"]] = relationship(back_populates="proxy_product")
    proxy_purchases: Mapped[List["ProxyPurchase"]] = relationship(back_populates="proxy_product")

    def __repr__(self) -> str:
        return f"<ProxyProduct(id={self.id}, name='{self.name}', category='{self.proxy_category.value}')>"


class Order(Base):
    """Заказы пользователей"""
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    total_amount: Mapped[Decimal] = mapped_column()
    currency: Mapped[str] = mapped_column(String(10), default="USD")

    status: Mapped[OrderStatus] = mapped_column(default=OrderStatus.PENDING)
    payment_method: Mapped[Optional[str]] = mapped_column(String(50))
    payment_id: Mapped[Optional[str]] = mapped_column(String(255))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    expires_at: Mapped[Optional[datetime]] = mapped_column()

    # Relationships
    user: Mapped["User"] = relationship(back_populates="orders")
    order_items: Mapped[List["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="order")

    def __repr__(self) -> str:
        return f"<Order(id={self.id}, order_number='{self.order_number}', status='{self.status.value}')>"


class OrderItem(Base):
    """Элементы заказа"""
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    proxy_product_id: Mapped[int] = mapped_column(ForeignKey("proxy_products.id"))

    quantity: Mapped[int] = mapped_column(default=1)
    unit_price: Mapped[Decimal] = mapped_column()
    total_price: Mapped[Decimal] = mapped_column()

    generation_params: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    order: Mapped["Order"] = relationship(back_populates="order_items")
    proxy_product: Mapped["ProxyProduct"] = relationship(
        back_populates="order_items",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<OrderItem(id={self.id}, order_id={self.order_id}, quantity={self.quantity})>"


class Transaction(Base):
    """Финансовые транзакции"""
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    transaction_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orders.id"))

    amount: Mapped[Decimal] = mapped_column()
    currency: Mapped[str] = mapped_column(String(10))
    transaction_type: Mapped[TransactionType] = mapped_column()
    status: Mapped[TransactionStatus] = mapped_column(default=TransactionStatus.PENDING)

    payment_provider: Mapped[str] = mapped_column(String(50), default="cryptomus")
    external_transaction_id: Mapped[Optional[str]] = mapped_column(String(255))
    payment_url: Mapped[Optional[str]] = mapped_column(String(500))

    description: Mapped[Optional[str]] = mapped_column(String(500))
    provider_metadata: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column()

    # Relationships
    user: Mapped["User"] = relationship(back_populates="transactions")
    order: Mapped[Optional["Order"]] = relationship(back_populates="transactions")

    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, transaction_id='{self.transaction_id}', amount={self.amount})>"


class ProxyPurchase(Base):
    """Приобретенные прокси (результат выполненного заказа)"""
    __tablename__ = "proxy_purchases"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    proxy_product_id: Mapped[int] = mapped_column(ForeignKey("proxy_products.id"))
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))

    proxy_list: Mapped[str] = mapped_column(Text)
    username: Mapped[Optional[str]] = mapped_column(String(100))
    password: Mapped[Optional[str]] = mapped_column(String(255))

    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")
    expires_at: Mapped[datetime] = mapped_column()

    traffic_used_gb: Mapped[Decimal] = mapped_column(default=Decimal('0.00'))
    last_used: Mapped[Optional[datetime]] = mapped_column()

    provider_order_id: Mapped[Optional[str]] = mapped_column(String(255))
    provider_metadata: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="proxy_purchases")
    proxy_product: Mapped["ProxyProduct"] = relationship(back_populates="proxy_purchases")

    def __repr__(self) -> str:
        return f"<ProxyPurchase(id={self.id}, user_id={self.user_id}, expires_at={self.expires_at})>"


class ShoppingCart(Base):
    """Корзина покупок (для зарегистрированных и гостевых пользователей)"""
    __tablename__ = "shopping_carts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    session_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    proxy_product_id: Mapped[int] = mapped_column(ForeignKey("proxy_products.id"))

    quantity: Mapped[int] = mapped_column(default=1)
    generation_params: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    expires_at: Mapped[Optional[datetime]] = mapped_column()

    # Relationships
    user: Mapped[Optional["User"]] = relationship()
    proxy_product: Mapped["ProxyProduct"] = relationship(lazy="selectin")

    def __repr__(self) -> str:
        return f"<ShoppingCart(id={self.id}, user_id={self.user_id}, quantity={self.quantity})>"
