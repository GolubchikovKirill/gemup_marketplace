"""
CRUD операции для пользователей.

Содержит методы для создания, аутентификации и управления пользователями,
включая зарегистрированных пользователей и гостевые сессии.
"""

import logging
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any

from passlib.context import CryptContext
from sqlalchemy import select, and_, func, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.models import User, UserRole  # ИСПРАВЛЕНО: импорт UserRole enum
from app.schemas.user import UserCreate, UserUpdate

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """
    CRUD для управления пользователями.

    Обеспечивает создание, аутентификацию и управление как зарегистрированными
    пользователями, так и гостевыми сессиями. Включает работу с балансом,
    ролями и разрешениями.
    """

    @staticmethod
    def get_password_hash(password: str) -> str:
        """
        Хеширование пароля с использованием bcrypt.

        Args:
            password: Пароль в открытом виде

        Returns:
            str: Хешированный пароль

        Raises:
            ValueError: При некорректном пароле
        """
        if not password or len(password.strip()) == 0:
            raise ValueError("Password cannot be empty")

        if len(password) > 128:
            raise ValueError("Password is too long (max 128 characters)")

        try:
            return pwd_context.hash(password)
        except Exception as e:
            logger.error(f"Error hashing password: {e}")
            raise ValueError("Failed to hash password")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Проверка пароля против хеша.

        Args:
            plain_password: Пароль в открытом виде
            hashed_password: Хешированный пароль

        Returns:
            bool: True если пароль корректный
        """
        if not plain_password or not hashed_password:
            return False

        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False

    async def create_registered_user(
            self,
            db: AsyncSession,
            *,
            user_in: UserCreate
    ) -> Optional[User]:
        """
        Создание зарегистрированного пользователя.

        Args:
            db: Сессия базы данных
            user_in: Данные для создания пользователя

        Returns:
            Optional[User]: Созданный пользователь или None

        Raises:
            ValueError: При некорректных данных
        """
        try:
            # Проверяем уникальность email
            existing_email = await self.get_by_email(db, email=str(user_in.email))
            if existing_email:
                logger.warning(f"Email {user_in.email} already exists")
                raise ValueError("Email already registered")

            # Проверяем уникальность username если указан
            if user_in.username:
                existing_username = await self.get_by_username(db, username=user_in.username)
                if existing_username:
                    logger.warning(f"Username {user_in.username} already exists")
                    raise ValueError("Username already taken")

            # Хешируем пароль
            hashed_password = self.get_password_hash(user_in.password)

            # Создаем пользователя
            db_user = User(
                email=str(user_in.email),
                username=user_in.username,
                hashed_password=hashed_password,
                first_name=user_in.first_name,
                last_name=user_in.last_name,
                role=UserRole.USER,  # ИСПРАВЛЕНО: используем enum
                is_guest=False,
                is_active=True,
                is_verified=False
            )

            db.add(db_user)
            await db.commit()
            await db.refresh(db_user)

            logger.info(f"Created registered user {db_user.id} with email {db_user.email}")
            return db_user

        except ValueError:
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating registered user: {e}")
            return None

    async def create_guest_user(
            self,
            db: AsyncSession,
            *,
            session_id: Optional[str] = None,
            expires_in_hours: int = 24
    ) -> Optional[User]:
        """
        Создание гостевого пользователя.

        Args:
            db: Сессия базы данных
            session_id: ID сессии (если не указан, будет сгенерирован)
            expires_in_hours: Время жизни гостевой сессии в часах

        Returns:
            Optional[User]: Созданный гостевой пользователь или None
        """
        try:
            if not session_id:
                session_id = str(uuid.uuid4())

            # Проверяем уникальность session_id
            existing_guest = await self.get_guest_by_session_id(db, session_id=session_id)
            if existing_guest:
                # Если сессия уже существует и не истекла, возвращаем её
                if existing_guest.guest_expires_at > datetime.now():
                    return existing_guest
                else:
                    # Удаляем истекшую сессию
                    await self.delete(db, obj_id=existing_guest.id)

            # Валидация времени жизни
            if expires_in_hours <= 0 or expires_in_hours > 168:  # Максимум неделя
                expires_in_hours = 24

            expires_at = datetime.now() + timedelta(hours=expires_in_hours)

            # Создаем гостевого пользователя
            db_user = User(
                is_guest=True,
                is_active=True,
                guest_session_id=session_id,
                guest_expires_at=expires_at,
                role=UserRole.USER  # ИСПРАВЛЕНО: используем enum
            )

            db.add(db_user)
            await db.commit()
            await db.refresh(db_user)

            logger.info(f"Created guest user {db_user.id} with session {session_id}")
            return db_user

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating guest user: {e}")
            return None

    @staticmethod
    async def get_by_email(db: AsyncSession, *, email: str) -> Optional[User]:
        """
        Получение пользователя по email.

        Args:
            db: Сессия базы данных
            email: Email пользователя

        Returns:
            Optional[User]: Пользователь или None
        """
        try:
            if not email or "@" not in email:
                return None

            result = await db.execute(
                select(User)
                .options(selectinload(User.permissions))
                .where(
                    and_(
                        User.email == email.lower().strip(),
                        User.is_guest.is_(False)
                    )
                )
            )
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            return None

    @staticmethod
    async def get_by_username(db: AsyncSession, *, username: str) -> Optional[User]:
        """
        Получение пользователя по username.

        Args:
            db: Сессия базы данных
            username: Username пользователя

        Returns:
            Optional[User]: Пользователь или None
        """
        try:
            if not username:
                return None

            result = await db.execute(
                select(User)
                .options(selectinload(User.permissions))
                .where(
                    and_(
                        User.username == username.strip(),
                        User.is_guest.is_(False)
                    )
                )
            )
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error getting user by username {username}: {e}")
            return None

    @staticmethod
    async def get_guest_by_session_id(
            db: AsyncSession,
            *,
            session_id: str
    ) -> Optional[User]:
        """
        Получение гостевого пользователя по session_id.

        Args:
            db: Сессия базы данных
            session_id: ID гостевой сессии

        Returns:
            Optional[User]: Гостевой пользователь или None
        """
        try:
            if not session_id:
                return None

            result = await db.execute(
                select(User).where(
                    and_(
                        User.guest_session_id == session_id,
                        User.is_guest.is_(True),
                        User.guest_expires_at > datetime.now()
                    )
                )
            )
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error getting guest by session ID {session_id}: {e}")
            return None

    async def authenticate(
            self,
            db: AsyncSession,
            *,
            email: str,
            password: str
    ) -> Optional[User]:
        """
        Аутентификация пользователя.

        Args:
            db: Сессия базы данных
            email: Email пользователя
            password: Пароль пользователя

        Returns:
            Optional[User]: Аутентифицированный пользователь или None
        """
        try:
            user = await self.get_by_email(db, email=email)
            if not user:
                logger.debug(f"User with email {email} not found")
                return None

            if not user.hashed_password:
                logger.warning(f"User {user.id} has no password set")
                return None

            if not self.verify_password(password, user.hashed_password):
                logger.debug(f"Invalid password for user {user.id}")
                return None

            if not user.is_active:
                logger.warning(f"Inactive user {user.id} attempted to authenticate")
                return None

            logger.info(f"User {user.id} authenticated successfully")
            return user

        except Exception as e:
            logger.error(f"Error during authentication for {email}: {e}")
            return None

    async def convert_guest_to_registered(
            self,
            db: AsyncSession,
            *,
            guest_user: User,
            user_data: UserCreate
    ) -> Optional[User]:
        """
        Конвертация гостевого пользователя в зарегистрированного.

        Args:
            db: Сессия базы данных
            guest_user: Гостевой пользователь
            user_data: Данные для регистрации

        Returns:
            Optional[User]: Конвертированный пользователь или None
        """
        try:
            if not guest_user.is_guest:
                raise ValueError("User is not a guest")

            # Проверяем уникальность email
            existing_email = await self.get_by_email(db, email=str(user_data.email))
            if existing_email:
                raise ValueError("Email already registered")

            # Проверяем уникальность username если указан
            if user_data.username:
                existing_username = await self.get_by_username(db, username=user_data.username)
                if existing_username:
                    raise ValueError("Username already taken")

            # Хешируем пароль
            hashed_password = self.get_password_hash(user_data.password)

            # Обновляем гостевого пользователя
            guest_user.email = str(user_data.email)
            guest_user.username = user_data.username
            guest_user.hashed_password = hashed_password
            guest_user.first_name = user_data.first_name
            guest_user.last_name = user_data.last_name
            guest_user.is_guest = False
            guest_user.is_verified = False
            guest_user.guest_session_id = None
            guest_user.guest_expires_at = None
            guest_user.updated_at = datetime.now()

            await db.commit()
            await db.refresh(guest_user)

            logger.info(f"Converted guest user {guest_user.id} to registered user {guest_user.email}")
            return guest_user

        except ValueError:
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error converting guest to registered user: {e}")
            return None

    @staticmethod
    async def update_balance(
            db: AsyncSession,
            *,
            user: User,
            amount: Decimal
    ) -> Optional[User]:
        """
        Обновление баланса пользователя.

        Args:
            db: Сессия базы данных
            user: Пользователь
            amount: Сумма для изменения баланса (может быть отрицательной)

        Returns:
            Optional[User]: Пользователь с обновленным балансом или None
        """
        try:
            # Валидация суммы
            if not isinstance(amount, Decimal):
                amount = Decimal(str(amount))

            new_balance = user.balance + amount

            # Проверяем, что баланс не становится отрицательным
            if new_balance < 0:
                logger.warning(f"Insufficient balance for user {user.id}: {user.balance} + {amount} = {new_balance}")
                raise ValueError("Insufficient balance")

            old_balance = user.balance
            user.balance = new_balance
            user.updated_at = datetime.now()

            await db.commit()
            await db.refresh(user)

            logger.info(f"Updated balance for user {user.id}: {old_balance} -> {new_balance}")
            return user

        except ValueError:
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating balance for user {user.id}: {e}")
            return None

    @staticmethod
    async def set_balance(
            db: AsyncSession,
            *,
            user: User,
            new_balance: Decimal
    ) -> Optional[User]:
        """
        Установка нового баланса пользователя.

        Args:
            db: Сессия базы данных
            user: Пользователь
            new_balance: Новый баланс

        Returns:
            Optional[User]: Пользователь с обновленным балансом или None
        """
        try:
            if not isinstance(new_balance, Decimal):
                new_balance = Decimal(str(new_balance))

            if new_balance < 0:
                raise ValueError("Balance cannot be negative")

            old_balance = user.balance
            user.balance = new_balance
            user.updated_at = datetime.now()

            await db.commit()
            await db.refresh(user)

            logger.info(f"Set balance for user {user.id}: {old_balance} -> {new_balance}")
            return user

        except ValueError:
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error setting balance for user {user.id}: {e}")
            return None

    async def update_last_login(self, db: AsyncSession, *, user_id: int) -> bool:
        """
        Обновление времени последнего входа.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя

        Returns:
            bool: True если обновление прошло успешно
        """
        try:
            user = await self.get(db, obj_id=user_id)
            if user:
                user.last_login = datetime.now()
                await db.commit()
                logger.debug(f"Updated last login for user {user_id}")
                return True
            return False

        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating last login for user {user_id}: {e}")
            return False

    async def verify_user_email(
            self,
            db: AsyncSession,
            *,
            user_id: int
    ) -> Optional[User]:
        """
        Верификация email пользователя.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя

        Returns:
            Optional[User]: Верифицированный пользователь или None
        """
        try:
            user = await self.get(db, obj_id=user_id)
            if not user:
                return None

            if user.is_verified:
                return user  # Уже верифицирован

            user.is_verified = True
            user.updated_at = datetime.now()

            await db.commit()
            await db.refresh(user)

            logger.info(f"Verified email for user {user_id}")
            return user

        except Exception as e:
            await db.rollback()
            logger.error(f"Error verifying user {user_id}: {e}")
            return None

    async def change_user_role(
            self,
            db: AsyncSession,
            *,
            user_id: int,
            new_role: UserRole,  # ИСПРАВЛЕНО: используем enum
            is_admin: bool = False
    ) -> Optional[User]:
        """
        Изменение роли пользователя.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            new_role: Новая роль
            is_admin: Флаг администратора

        Returns:
            Optional[User]: Пользователь с обновленной ролью или None
        """
        try:
            user = await self.get(db, obj_id=user_id)
            if not user:
                return None

            old_role = user.role
            old_admin = user.is_admin

            user.role = new_role
            user.is_admin = is_admin
            user.updated_at = datetime.now()

            await db.commit()
            await db.refresh(user)

            logger.info(f"Changed user {user_id} role: {old_role}/{old_admin} -> {new_role}/{is_admin}")
            return user

        except Exception as e:
            await db.rollback()
            logger.error(f"Error changing role for user {user_id}: {e}")
            return None

    @staticmethod
    async def get_active_users(
            db: AsyncSession,
            *,
            skip: int = 0,
            limit: int = 100
    ) -> List[User]:
        """
        Получение активных пользователей.

        Args:
            db: Сессия базы данных
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            List[User]: Список активных пользователей
        """
        try:
            result = await db.execute(
                select(User)
                .where(
                    and_(
                        User.is_active.is_(True),
                        User.is_guest.is_(False)
                    )
                )
                .order_by(desc(User.created_at))
                .offset(skip)
                .limit(limit)
            )
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error getting active users: {e}")
            return []

    @staticmethod
    async def search_users(
            db: AsyncSession,
            *,
            search_term: str,
            skip: int = 0,
            limit: int = 100
    ) -> List[User]:
        """
        Поиск пользователей по email, username или имени.

        Args:
            db: Сессия базы данных
            search_term: Поисковый термин
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            List[User]: Список найденных пользователей
        """
        try:
            if not search_term or len(search_term.strip()) < 2:
                return []

            search_pattern = f"%{search_term.strip()}%"

            result = await db.execute(
                select(User)
                .where(
                    and_(
                        User.is_guest.is_(False),
                        or_(
                            User.email.ilike(search_pattern),
                            User.username.ilike(search_pattern),
                            User.first_name.ilike(search_pattern),
                            User.last_name.ilike(search_pattern)
                        )
                    )
                )
                .order_by(desc(User.created_at))
                .offset(skip)
                .limit(limit)
            )
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error searching users with term '{search_term}': {e}")
            return []

    @staticmethod
    async def get_users_stats(
            db: AsyncSession,
            *,
            days: int = 30
    ) -> Dict[str, Any]:
        """
        Получение статистики пользователей.

        Args:
            db: Сессия базы данных
            days: Период для статистики в днях

        Returns:
            Dict[str, Any]: Статистика пользователей
        """
        try:
            start_date = datetime.now() - timedelta(days=days)

            # Общее количество зарегистрированных пользователей
            total_result = await db.execute(
                select(func.count(User.id))
                .where(User.is_guest.is_(False))
            )
            total_users = total_result.scalar() or 0

            # Активные пользователи
            active_result = await db.execute(
                select(func.count(User.id))
                .where(
                    and_(
                        User.is_active.is_(True),
                        User.is_guest.is_(False)
                    )
                )
            )
            active_users = active_result.scalar() or 0

            # Верифицированные пользователи
            verified_result = await db.execute(
                select(func.count(User.id))
                .where(
                    and_(
                        User.is_verified.is_(True),
                        User.is_guest.is_(False)
                    )
                )
            )
            verified_users = verified_result.scalar() or 0

            # Новые пользователи за период
            new_users_result = await db.execute(
                select(func.count(User.id))
                .where(
                    and_(
                        User.created_at >= start_date,
                        User.is_guest.is_(False)
                    )
                )
            )
            new_users = new_users_result.scalar() or 0

            # Пользователи с балансом > 0
            users_with_balance_result = await db.execute(
                select(func.count(User.id))
                .where(
                    and_(
                        User.balance > 0,
                        User.is_guest.is_(False)
                    )
                )
            )
            users_with_balance = users_with_balance_result.scalar() or 0

            # Общий баланс всех пользователей
            total_balance_result = await db.execute(
                select(func.sum(User.balance))
                .where(User.is_guest.is_(False))
            )
            total_balance = total_balance_result.scalar() or Decimal('0.00')

            return {
                "total_users": total_users,
                "active_users": active_users,
                "verified_users": verified_users,
                "new_users_last_30d": new_users,
                "users_with_balance": users_with_balance,
                "total_balance": str(total_balance),
                "verification_rate": round((verified_users / max(total_users, 1)) * 100, 2),
                "period_days": days
            }

        except Exception as e:
            logger.error(f"Error getting users stats: {e}")
            return {
                "total_users": 0,
                "active_users": 0,
                "verified_users": 0,
                "new_users_last_30d": 0,
                "users_with_balance": 0,
                "total_balance": "0.00",
                "verification_rate": 0,
                "period_days": days
            }

    @staticmethod
    async def cleanup_expired_guests(db: AsyncSession) -> int:
        """
        Очистка просроченных гостевых пользователей.

        Args:
            db: Сессия базы данных

        Returns:
            int: Количество удаленных пользователей
        """
        try:
            current_time = datetime.now()

            # Получаем просроченных гостей
            result = await db.execute(
                select(User).where(
                    and_(
                        User.is_guest.is_(True),
                        User.guest_expires_at < current_time
                    )
                )
            )
            expired_guests = list(result.scalars().all())

            # Удаляем их
            for guest in expired_guests:
                await db.delete(guest)

            await db.commit()

            if expired_guests:
                logger.info(f"Cleaned up {len(expired_guests)} expired guest users")

            return len(expired_guests)

        except Exception as e:
            await db.rollback()
            logger.error(f"Error cleaning up expired guests: {e}")
            return 0


user_crud = CRUDUser(User)
