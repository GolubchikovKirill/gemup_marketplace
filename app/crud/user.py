"""
CRUD операции для пользователей с enhanced security и исправлениями.

"""

import asyncio
import concurrent.futures
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, Dict, Any, List
from functools import wraps

import bcrypt
from sqlalchemy import select, and_, update, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.models import User, UserRole, Order, Transaction, ProxyPurchase
from app.schemas.user import UserCreate, UserUpdate

logger = logging.getLogger(__name__)

# Thread pool для CPU-intensive операций
_thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)

def run_in_thread(func):
    """Decorator для выполнения CPU-intensive функций в thread pool"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_thread_pool, func, *args, **kwargs)
    return wrapper

class PasswordManager:
    """
    Enhanced password manager с async support и dual field compatibility.
    """

    @staticmethod
    @run_in_thread
    def hash_password(password: str) -> str:
        """Async password hashing с enhanced security."""
        if not password:
            raise ValueError("Password cannot be empty")

        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt(rounds=12)  # Enhanced security
        hashed_bytes = bcrypt.hashpw(password_bytes, salt)
        return hashed_bytes.decode('utf-8')

    @staticmethod
    @run_in_thread
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Async password verification."""
        if not plain_password or not hashed_password:
            return False

        try:
            password_bytes = plain_password.encode('utf-8')
            hash_bytes = hashed_password.encode('utf-8')
            return bcrypt.checkpw(password_bytes, hash_bytes)
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False

class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """
    CRUD для управления пользователями с enhanced security и исправлениями.

    КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ:
    ✅ Dual password field support
    ✅ Security fields support
    ✅ Async operations
    ✅ Enhanced error handling
    ✅ Static методы где возможно
    ✅ Исправлено shadowing переменных
    ✅ Добавлен get_guest_by_session_id для dependencies.py
    """

    def __init__(self, model):
        super().__init__(model)
        self.password_manager = PasswordManager()

    @staticmethod
    async def get_by_email(db: AsyncSession, *, email: str) -> Optional[User]:
        """
        Получение пользователя по email с proper error handling.

        Args:
            db: Сессия базы данных
            email: Email пользователя

        Returns:
            Optional[User]: Пользователь или None
        """
        try:
            email_lower = email.lower()
            result = await db.execute(
                select(User).where(User.email == email_lower)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            try:
                await db.rollback()
            except Exception as rollback_error:
                logger.error(f"Error during rollback: {rollback_error}")
            return None

    @staticmethod
    async def get_by_username(db: AsyncSession, *, username: str) -> Optional[User]:
        """Получение пользователя по username"""
        try:
            username_lower = username.lower()
            result = await db.execute(
                select(User).where(User.username == username_lower)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by username {username}: {e}")
            try:
                await db.rollback()
            except Exception as rollback_error:
                logger.error(f"Error during rollback: {rollback_error}")
            return None

    async def get(self, db: AsyncSession, id: Any) -> Optional[User]:
        """
        Базовый метод получения пользователя по ID.

        Соответствует signature базового класса CRUDBase.
        """
        try:
            result = await db.execute(select(User).where(User.id == id))
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by id {id}: {e}")
            try:
                await db.rollback()
            except Exception as rollback_error:
                logger.error(f"Error during rollback: {rollback_error}")
            return None

    @staticmethod
    async def get_by_session_id(db: AsyncSession, *, session_id: str) -> Optional[User]:
        """
        Получение гостевого пользователя по session_id.
        """
        try:
            current_time = datetime.now(timezone.utc)

            conditions = [
                User.guest_session_id == session_id,
                User.is_guest == True
            ]

            if hasattr(User, 'guest_expires_at'):
                conditions.append(
                    or_(
                        User.guest_expires_at.is_(None),
                        User.guest_expires_at > current_time
                    )
                )

            result = await db.execute(
                select(User).where(and_(*conditions))
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by session_id {session_id}: {e}")
            try:
                await db.rollback()
            except Exception as rollback_error:
                logger.error(f"Error during rollback: {rollback_error}")
            return None

    # ИСПРАВЛЕНИЕ: Добавлен отсутствующий метод для dependencies.py
    async def get_guest_by_session_id(self, db: AsyncSession, *, session_id: str) -> Optional[User]:
        """
        КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Alias для get_by_session_id для совместимости с dependencies.py

        Этот метод ожидается в dependencies.py но отсутствовал в классе.

        Args:
            db: Сессия базы данных
            session_id: ID сессии

        Returns:
            Optional[User]: Гостевой пользователь или None
        """
        return await self.get_by_session_id(db, session_id=session_id)

    async def create_registered_user(self, db: AsyncSession, *, user_in: UserCreate) -> Optional[User]:
        """
        Создание зарегистрированного пользователя.

        КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ:
        ✅ Dual password field support
        ✅ Async password hashing
        ✅ Enhanced security fields
        ✅ Proper error handling
        ✅ Dictionary literals
        """
        try:
            # Проверяем уникальность email и username
            existing_email = await self.get_by_email(db, email=str(user_in.email))
            if existing_email:
                raise ValueError("User with this email already exists")

            if user_in.username:
                existing_username = await self.get_by_username(db, username=user_in.username)
                if existing_username:
                    raise ValueError("User with this username already exists")

            # Async password hashing
            hashed_password = await self.password_manager.hash_password(user_in.password)

            # String operations без await
            email_lower = str(user_in.email).lower()
            username_lower = user_in.username.lower() if user_in.username else None

            # Dictionary literal - все поля в одном dictionary
            user_data = {
                'email': email_lower,
                'username': username_lower,
                'first_name': user_in.first_name,
                'last_name': user_in.last_name,
                'is_active': True,
                'is_verified': False,
                'is_guest': False,
                'role': UserRole.USER,
                'balance': Decimal('0.00000000'),
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc),
                # Dual password field support в основном dictionary
                'hashed_password': hashed_password,    # Старое поле (backup)
                'password_hash': hashed_password       # Новое поле (primary)
            }

            # Добавляем новые security поля если они существуют
            security_fields = {
                'failed_login_attempts': 0,
                'locked_until': None,
                'last_login_ip': None,
                'last_user_agent_hash': None,
                'email_verification_token': None,
                'email_verification_expires': None,
                'password_reset_token': None,
                'password_reset_expires': None,
                'last_login': None
            }

            for field, default_value in security_fields.items():
                if hasattr(User, field):
                    user_data[field] = default_value

            db_user = User(**user_data)
            db.add(db_user)
            await db.commit()
            await db.refresh(db_user)

            logger.info(f"Created registered user: {db_user.email} with dual password support")
            return db_user

        except ValueError:
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating registered user: {e}")
            return None

    async def create_guest_user(self, db: AsyncSession, *, session_id: str = None, obj_in = None) -> Optional[User]:
        """
        Создание гостевого пользователя.

        ИСПРАВЛЕНИЯ:
        ✅ Enhanced guest fields support
        ✅ IP tracking support
        ✅ Proper expiration handling
        ✅ Dictionary literals
        ✅ Support для обоих способов вызова
        """
        try:
            # Получаем session_id из параметров или объекта
            if obj_in and hasattr(obj_in, 'session_id'):
                session_id = obj_in.session_id
            elif not session_id:
                raise ValueError("session_id is required")

            # Проверяем, нет ли уже такого гостя
            existing_guest = await self.get_by_session_id(db, session_id=session_id)
            if existing_guest:
                return existing_guest

            # Dictionary literal + все поля в одном dictionary
            user_data = {
                'email': None,
                'username': None,
                'is_active': True,
                'is_verified': False,
                'is_guest': True,
                'role': UserRole.USER,
                'balance': Decimal('0.00000000'),
                'guest_session_id': session_id,
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc),
                # Dual password field support (NULL для guest)
                'hashed_password': None,
                'password_hash': None
            }

            # Enhanced guest fields если существуют
            guest_fields = {
                'guest_expires_at': datetime.now(timezone.utc) + timedelta(days=30),
                'failed_login_attempts': 0,
                'locked_until': None,
                'last_login_ip': None,
                'last_user_agent_hash': None,
                'last_login': datetime.now(timezone.utc)
            }

            for field, default_value in guest_fields.items():
                if hasattr(User, field):
                    user_data[field] = default_value

            db_user = User(**user_data)
            db.add(db_user)
            await db.commit()
            await db.refresh(db_user)

            logger.info(f"Created guest user with session_id: {session_id}")
            return db_user

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating guest user: {e}")
            return None

    # Алиас для совместимости с API
    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        """Алиас для create_registered_user"""
        return await self.create_registered_user(db, user_in=obj_in)

    async def authenticate(self, db: AsyncSession, *, email: str, password: str) -> Optional[User]:
        """
        Аутентификация пользователя с dual password support.

        КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ:
        ✅ Dual password field checking
        ✅ Async password verification
        ✅ Enhanced security logging
        ✅ Failed attempts tracking
        """
        try:
            db_user = await self.get_by_email(db, email=email)
            if not db_user:
                logger.warning(f"User not found: {email}")
                return None

            if db_user.is_guest:
                logger.warning(f"User is guest: {email}")
                return None

            # Enhanced account security checks
            if hasattr(db_user, 'locked_until') and db_user.locked_until:
                current_time = datetime.now(timezone.utc)
                if db_user.locked_until > current_time:
                    logger.warning(f"User account locked: {email}")
                    return None

            # Dual password field support
            password_hash = None

            # Приоритет: новое поле password_hash, потом старое hashed_password
            if hasattr(db_user, 'password_hash') and db_user.password_hash:
                password_hash = db_user.password_hash
                logger.debug(f"Using new password_hash field for {email}")
            elif hasattr(db_user, 'hashed_password') and db_user.hashed_password:
                password_hash = db_user.hashed_password
                logger.debug(f"Using legacy hashed_password field for {email}")

            if not password_hash:
                logger.error(f"No password hash found for user: {email}")
                await self._increment_failed_attempts(db, db_user)
                return None

            # Async password verification
            is_valid = await self.password_manager.verify_password(password, password_hash)

            if not is_valid:
                logger.warning(f"Invalid password for user: {email}")
                await self._increment_failed_attempts(db, db_user)
                return None

            # Reset failed attempts on successful login
            await self._reset_failed_attempts(db, db_user)

            logger.info(f"Authentication successful for: {email}")
            return db_user

        except Exception as e:
            logger.error(f"Error authenticating user {email}: {e}")
            try:
                await db.rollback()
            except Exception as rollback_error:
                logger.error(f"Error during rollback: {rollback_error}")
            return None

    @staticmethod
    async def _increment_failed_attempts(db: AsyncSession, db_user: User) -> None:
        """Увеличение счетчика неудачных попыток."""
        try:
            if not hasattr(db_user, 'failed_login_attempts'):
                return

            current_attempts = getattr(db_user, 'failed_login_attempts', 0) + 1
            current_time = datetime.now(timezone.utc)

            update_data = {
                'failed_login_attempts': current_attempts,
                'updated_at': current_time
            }

            # Блокируем аккаунт после 5 неудачных попыток
            if current_attempts >= 5 and hasattr(db_user, 'locked_until'):
                lock_duration = timedelta(minutes=30)  # 30 минут блокировки
                update_data['locked_until'] = current_time + lock_duration

            await db.execute(
                update(User)
                .where(User.id == db_user.id)
                .values(**update_data)
            )
            await db.commit()

        except Exception as e:
            logger.error(f"Error incrementing failed attempts for user {db_user.id}: {e}")
            await db.rollback()

    @staticmethod
    async def _reset_failed_attempts(db: AsyncSession, db_user: User) -> None:
        """Сброс счетчика неудачных попыток."""
        try:
            update_data = {
                'updated_at': datetime.now(timezone.utc)
            }

            if hasattr(db_user, 'failed_login_attempts'):
                update_data['failed_login_attempts'] = 0

            if hasattr(db_user, 'locked_until'):
                update_data['locked_until'] = None

            if len(update_data) > 1:  # Есть что обновлять кроме updated_at
                await db.execute(
                    update(User)
                    .where(User.id == db_user.id)
                    .values(**update_data)
                )
                await db.commit()

        except Exception as e:
            logger.error(f"Error resetting failed attempts for user {db_user.id}: {e}")
            await db.rollback()

    @staticmethod
    async def update_last_login(
        db: AsyncSession,
        *,
        user_id: int,
        client_ip: str = None,
        user_agent: str = None
    ) -> bool:
        """
        Обновление времени последнего входа с enhanced tracking.

        ИСПРАВЛЕНИЕ: Совместимость с dependencies.py - принимает только user_id
        """
        try:
            current_time = datetime.now(timezone.utc)

            update_data = {
                'updated_at': current_time
            }

            # Основные поля
            if hasattr(User, 'last_login'):
                update_data['last_login'] = current_time

            # Enhanced security поля
            if client_ip and hasattr(User, 'last_login_ip'):
                update_data['last_login_ip'] = client_ip

            if user_agent and hasattr(User, 'last_user_agent_hash'):
                import hashlib
                user_agent_hash = hashlib.sha256(user_agent.encode()).hexdigest()[:16]
                update_data['last_user_agent_hash'] = user_agent_hash

            result = await db.execute(
                update(User)
                .where(User.id == user_id)
                .values(**update_data)
            )
            await db.commit()

            logger.debug(f"Updated last login for user {user_id} from IP {client_ip}")
            return result.rowcount > 0

        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating last login for user {user_id}: {e}")
            return False

    async def update_password(
        self, db: AsyncSession, *, db_user: User, new_password: str
    ) -> Optional[User]:
        """Обновление пароля пользователя."""
        try:
            # Async password hashing
            hashed_password = await self.password_manager.hash_password(new_password)

            update_data = {
                'updated_at': datetime.now(timezone.utc),
                'password_reset_token': None,
                'password_reset_expires': None
            }

            # Обновляем ОБА password поля
            if hasattr(db_user, 'password_hash'):
                update_data['password_hash'] = hashed_password

            if hasattr(db_user, 'hashed_password'):
                update_data['hashed_password'] = hashed_password

            for field, value in update_data.items():
                if hasattr(db_user, field):
                    setattr(db_user, field, value)

            await db.commit()
            await db.refresh(db_user)

            logger.info(f"Password updated for user: {db_user.email}")
            return db_user

        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating password for user {db_user.id}: {e}")
            return None

    @staticmethod
    async def update_balance(
            db: AsyncSession, *, db_user: User, amount: Decimal
    ) -> Optional[User]:
        """Обновление баланса пользователя."""
        try:
            new_balance = db_user.balance + amount
            if new_balance < 0:
                raise ValueError("Insufficient balance")

            db_user.balance = new_balance
            db_user.updated_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(db_user)

            logger.info(f"Updated balance for user {db_user.id}: {db_user.balance}")
            return db_user

        except ValueError:
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating balance for user {db_user.id}: {e}")
            return None

    async def verify_user_email(self, db: AsyncSession, *, user_id: int) -> Optional[User]:
        """Подтверждение email пользователя."""
        try:
            db_user = await self.get(db, user_id)
            if not db_user:
                return None

            update_data = {
                'is_verified': True,
                'updated_at': datetime.now(timezone.utc),
                'email_verification_token': None,
                'email_verification_expires': None
            }

            for field, value in update_data.items():
                if hasattr(db_user, field):
                    setattr(db_user, field, value)

            await db.commit()
            await db.refresh(db_user)

            logger.info(f"Verified email for user {user_id}")
            return db_user

        except Exception as e:
            await db.rollback()
            logger.error(f"Error verifying email for user {user_id}: {e}")
            return None

    @staticmethod
    async def get_user_orders(
            db: AsyncSession, *, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[Order]:
        """Получение заказов пользователя."""
        try:
            result = await db.execute(
                select(Order)
                .where(Order.user_id == user_id)
                .order_by(desc(Order.created_at))
                .offset(skip)
                .limit(limit)
            )
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Error getting orders for user {user_id}: {e}")
            return []

    @staticmethod
    async def get_user_transactions(
            db: AsyncSession, *, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[Transaction]:
        """Получение транзакций пользователя."""
        try:
            result = await db.execute(
                select(Transaction)
                .where(Transaction.user_id == user_id)
                .order_by(desc(Transaction.created_at))
                .offset(skip)
                .limit(limit)
            )
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Error getting transactions for user {user_id}: {e}")
            return []

    @staticmethod
    async def get_user_proxy_purchases(
            db: AsyncSession, *, user_id: int, active_only: bool = False
    ) -> List[ProxyPurchase]:
        """Получение купленных прокси пользователя."""
        try:
            query = select(ProxyPurchase).where(ProxyPurchase.user_id == user_id)

            if active_only:
                current_time = datetime.now(timezone.utc)
                query = query.where(
                    and_(
                        ProxyPurchase.is_active.is_(True),
                        ProxyPurchase.expires_at > current_time
                    )
                )

            query = query.order_by(desc(ProxyPurchase.created_at))
            result = await db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Error getting proxy purchases for user {user_id}: {e}")
            return []

    @staticmethod
    async def get_user_order_stats(db: AsyncSession, *, user_id: int) -> Dict[str, Any]:
        """Получение статистики заказов пользователя."""
        try:
            # Общее количество заказов
            total_orders_result = await db.execute(
                select(func.count(Order.id)).where(Order.user_id == user_id)
            )
            total_orders = total_orders_result.scalar() or 0

            # Сумма всех заказов
            total_spent_result = await db.execute(
                select(func.coalesce(func.sum(Order.total_amount), 0))
                .where(and_(Order.user_id == user_id, Order.status == 'completed'))
            )
            total_spent = total_spent_result.scalar() or Decimal('0')

            # Количество активных прокси
            current_time = datetime.now(timezone.utc)
            active_proxies_result = await db.execute(
                select(func.count(ProxyPurchase.id))
                .where(and_(
                    ProxyPurchase.user_id == user_id,
                    ProxyPurchase.is_active.is_(True),
                    ProxyPurchase.expires_at > current_time
                ))
            )
            active_proxies = active_proxies_result.scalar() or 0

            return {
                'total_orders': total_orders,
                'total_spent': str(total_spent),
                'active_proxies': active_proxies
            }

        except Exception as e:
            logger.error(f"Error getting order stats for user {user_id}: {e}")
            return {
                'total_orders': 0,
                'total_spent': '0',
                'active_proxies': 0
            }

    @staticmethod
    def is_active(db_user: User) -> bool:
        """Проверка активности пользователя"""
        return db_user.is_active

    @staticmethod
    def is_verified(db_user: User) -> bool:
        """Проверка верификации пользователя"""
        return getattr(db_user, 'is_verified', True)

    async def authenticate_by_username_or_email(
        self, db: AsyncSession, *, identifier: str, password: str
    ) -> Optional[User]:
        """Аутентификация по username или email."""
        # Сначала пробуем email
        authenticated_user = await self.authenticate(db, email=identifier, password=password)
        if authenticated_user:
            return authenticated_user

        # Потом пробуем username
        db_user = await self.get_by_username(db, username=identifier)
        if db_user and db_user.email:
            return await self.authenticate(db, email=db_user.email, password=password)

        return None

# Создание экземпляра CRUD
user_crud = CRUDUser(User)

# Переименованный alias для избежания shadowing
crud_user = user_crud
