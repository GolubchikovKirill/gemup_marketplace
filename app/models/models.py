from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Enum
from sqlalchemy.types import DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from app.core.db import Base


# Енумы для типов данных
class ProxyType(str, PyEnum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"


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

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    username = Column(String(100), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)

    balance = Column(DECIMAL(15, 8), default=0.00000000, nullable=False)

    is_active = Column(Boolean, default=True, server_default='true', nullable=False)
    is_verified = Column(Boolean, default=False, server_default='false', nullable=False)
    is_guest = Column(Boolean, default=False, server_default='false', nullable=False)

    guest_session_id = Column(String(255), nullable=True, index=True)
    guest_expires_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)

    orders = relationship("Order", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")
    proxy_purchases = relationship("ProxyPurchase", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', is_guest={self.is_guest})>"


class ProxyProduct(Base):
    """Продукты прокси от различных провайдеров"""
    __tablename__ = "proxy_products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    proxy_type = Column(Enum(ProxyType), nullable=False)
    session_type = Column(Enum(SessionType), nullable=False)
    provider = Column(Enum(ProviderType), nullable=False)

    country_code = Column(String(2), nullable=False)
    country_name = Column(String(100), nullable=False)
    city = Column(String(100), nullable=True)

    price_per_proxy = Column(DECIMAL(10, 8), nullable=False)
    min_quantity = Column(Integer, default=1, nullable=False)
    max_quantity = Column(Integer, default=1000, nullable=False)

    duration_days = Column(Integer, nullable=False)
    max_threads = Column(Integer, default=1, nullable=False)
    bandwidth_limit_gb = Column(Integer, nullable=True)

    is_active = Column(Boolean, server_default='true', nullable=False)
    is_featured = Column(Boolean, server_default='false', nullable=False)
    stock_available = Column(Integer, default=0, nullable=False)

    provider_product_id = Column(String(255), nullable=True)
    provider_metadata = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    order_items = relationship("OrderItem", back_populates="proxy_product")
    proxy_purchases = relationship("ProxyPurchase", back_populates="proxy_product")

    def __repr__(self):
        return f"<ProxyProduct(id={self.id}, name='{self.name}', provider='{self.provider.value}')>"


class Order(Base):
    """Заказы пользователей"""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    total_amount = Column(DECIMAL(15, 8), nullable=False)
    currency = Column(String(10), default="USD", nullable=False)

    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    payment_method = Column(String(50), nullable=True)
    payment_id = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="orders")
    order_items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin"  # ИСПРАВЛЕНО: eager loading для решения MissingGreenlet
    )
    transactions = relationship("Transaction", back_populates="order")

    def __repr__(self):
        return f"<Order(id={self.id}, order_number='{self.order_number}', status='{self.status.value}')>"


class OrderItem(Base):
    """Элементы заказа"""
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    proxy_product_id = Column(Integer, ForeignKey("proxy_products.id"), nullable=False)

    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(DECIMAL(10, 8), nullable=False)
    total_price = Column(DECIMAL(15, 8), nullable=False)

    generation_params = Column(Text, nullable=True)

    order = relationship("Order", back_populates="order_items")
    proxy_product = relationship(
        "ProxyProduct",
        back_populates="order_items",
        lazy="selectin"  # ИСПРАВЛЕНО: eager loading для решения MissingGreenlet
    )

    def __repr__(self):
        return f"<OrderItem(id={self.id}, order_id={self.order_id}, quantity={self.quantity})>"


class Transaction(Base):
    """Финансовые транзакции"""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)

    amount = Column(DECIMAL(15, 8), nullable=False)
    currency = Column(String(10), nullable=False)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING, nullable=False)

    payment_provider = Column(String(50), default="cryptomus", nullable=False)
    external_transaction_id = Column(String(255), nullable=True)
    payment_url = Column(String(500), nullable=True)

    description = Column(String(500), nullable=True)
    provider_metadata = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="transactions")
    order = relationship("Order", back_populates="transactions")

    def __repr__(self):
        return f"<Transaction(id={self.id}, transaction_id='{self.transaction_id}', amount={self.amount})>"


class ProxyPurchase(Base):
    """Приобретенные прокси (результат выполненного заказа)"""
    __tablename__ = "proxy_purchases"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    proxy_product_id = Column(Integer, ForeignKey("proxy_products.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)

    proxy_list = Column(Text, nullable=False)
    username = Column(String(100), nullable=True)
    password = Column(String(255), nullable=True)

    is_active = Column(Boolean, default=True, server_default="true", nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    traffic_used_gb = Column(DECIMAL(10, 2), default=0.00, nullable=False)
    last_used = Column(DateTime(timezone=True), nullable=True)

    provider_order_id = Column(String(255), nullable=True)
    provider_metadata = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="proxy_purchases")
    proxy_product = relationship("ProxyProduct", back_populates="proxy_purchases")

    def __repr__(self):
        return f"<ProxyPurchase(id={self.id}, user_id={self.user_id}, expires_at={self.expires_at})>"


class ShoppingCart(Base):
    """Корзина покупок (для зарегистрированных и гостевых пользователей)"""
    __tablename__ = "shopping_carts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    session_id = Column(String(255), nullable=True, index=True)
    proxy_product_id = Column(Integer, ForeignKey("proxy_products.id"), nullable=False)

    quantity = Column(Integer, nullable=False, default=1)
    generation_params = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User")
    proxy_product = relationship(
        "ProxyProduct",
        lazy="selectin"  # ИСПРАВЛЕНО: eager loading для решения MissingGreenlet
    )

    def __repr__(self):
        return f"<ShoppingCart(id={self.id}, user_id={self.user_id}, quantity={self.quantity})>"
