"""
CRUD операции для пользователей.

Содержит методы для управления пользователями, аутентификации,
баланса и статистики. Оптимизировано для MVP функций.
"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional, Dict, Any

from passlib.context import CryptContext
from sqlalchemy import select, and_, func, desc, update, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.models import User, UserRole, Order, Transaction, ProxyPurchase
from app.schemas.user import UserCreate, UserUpdate

logger = logging.getLogger(__name__)

# Настройка хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """
    CRUD для управления пользователями.

    Обеспечивает регистрацию, аутентификацию, управление балансом
    и статистикой пользователей. Поддерживает гостевых пользователей.
    """

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Хеширование пароля."""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Проверка пароля."""
        return pwd_context.verify(plain_password, hashed_password)

    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[User]:
        """
        Получение пользователя по email.

        Args:
            db: Сессия базы данных
            email: Email пользователя

        Returns:
            Optional[User]: Пользователь или None
        """
        try:
            result = await db.execute(
                select(User).where(User.email == email.lower())
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            return None

    async def get_by_username(self, db: AsyncSession, *, username: str) -> Optional[User]:
        """
        Получение пользователя по username.

        Args:
            db: Сессия базы данных
            username: Имя пользователя

        Returns:
            Optional[User]: Пользователь или None
        """
        try:
            result = await db.execute(
                select(User).where(User.username == username.lower())
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by username {username}: {e}")
            return None

    async def get_by_session_id(self, db: AsyncSession, *, session_id: str) -> Optional[User]:
        """
        Получение гостевого пользователя по session_id.

        Args:
            db: Сессия базы данных
            session_id: ID сессии

        Returns:
            Optional[User]: Гостевой пользователь или None
        """
        try:
            current_time = datetime.now(timezone.utc)
            result = await db.execute(
                select(User).where(
                    and_(
                        User.guest_session_id == session_id,
                        User.is_guest.is_(True),
                        or_(
                            User.guest_expires_at.is_(None),
                            User.guest_expires_at > current_time
                        )
                    )
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by session_id {session_id}: {e}")
            return None

    async def create_registered_user(self, db: AsyncSession, *, user_in: UserCreate) -> Optional[User]:
        """
        Создание зарегистрированного пользователя - КЛЮЧЕВОЕ для MVP.

        Args:
            db: Сессия базы данных
            user_in: Данные для создания пользователя

        Returns:
            Optional[User]: Созданный пользователь или None
        """
        try:
            # Проверяем уникальность email и username
            existing_email = await self.get_by_email(db, email=str(user_in.email))
            if existing_email:
                raise ValueError("User with this email already exists")

            existing_username = await self.get_by_username(db, username=user_in.username)
            if existing_username:
                raise ValueError("User with this username already exists")

            # Создаем пользователя
            hashed_password = self.get_password_hash(user_in.password)

            db_user = User(
                email=str(user_in.email).lower(),
                username=user_in.username.lower(),
                hashed_password=hashed_password,
                first_name=user_in.first_name,
                last_name=user_in.last_name,
                is_active=True,
                is_verified=False,
                is_guest=False,
                role=UserRole.USER,
                balance=Decimal('0.00000000'),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )

            db.add(db_user)
            await db.commit()
            await db.refresh(db_user)

            logger.info(f"Created registered user: {db_user.email}")
            return db_user

        except ValueError:
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating registered user: {e}")
            return None

    async def create_guest_user(self, db: AsyncSession, *, session_id: str) -> Optional[User]:
        """
        Создание гостевого пользователя - КЛЮЧЕВОЕ для покупок без регистрации.

        Args:
            db: Сессия базы данных
            session_id: ID сессии

        Returns:
            Optional[User]: Созданный гостевой пользователь или None
        """
        try:
            # Проверяем, нет ли уже такого гостя
            existing_guest = await self.get_by_session_id(db, session_id=session_id)
            if existing_guest:
                return existing_guest

            # Создаем гостевого пользователя
            expires_at = datetime.now(timezone.utc) + timedelta(days=30)

            db_user = User(
                email=None,
                username=None,
                hashed_password=None,
                is_active=True,
                is_verified=False,
                is_guest=True,
                role=UserRole.USER,
                balance=Decimal('0.00000000'),
                guest_session_id=session_id,
                guest_expires_at=expires_at,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )

            db.add(db_user)
            await db.commit()
            await db.refresh(db_user)

            logger.info(f"Created guest user with session_id: {session_id}")
            return db_user

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating guest user: {e}")
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

            # Проверяем уникальность email и username
            existing_email = await self.get_by_email(db, email=str(user_data.email))
            if existing_email:
                raise ValueError("User with this email already exists")

            existing_username = await self.get_by_username(db, username=user_data.username)
            if existing_username:
                raise ValueError("User with this username already exists")

            # Обновляем гостевого пользователя
            guest_user.email = str(user_data.email).lower()
            guest_user.username = user_data.username.lower()
            guest_user.hashed_password = self.get_password_hash(user_data.password)
            guest_user.first_name = user_data.first_name
            guest_user.last_name = user_data.last_name
            guest_user.is_guest = False
            guest_user.guest_session_id = None
            guest_user.guest_expires_at = None
            guest_user.updated_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(guest_user)

            logger.info(f"Converted guest user to registered: {guest_user.email}")
            return guest_user

        except ValueError:
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error converting guest to registered: {e}")
            return None

    async def authenticate(self, db: AsyncSession, *, email: str, password: str) -> Optional[User]:
        """
        Аутентификация пользователя.

        Args:
            db: Сессия базы данных
            email: Email пользователя
            password: Пароль

        Returns:
            Optional[User]: Аутентифицированный пользователь или None
        """
        try:
            user = await self.get_by_email(db, email=email)
            if not user or user.is_guest:
                return None

            if not self.verify_password(password, user.hashed_password):
                return None

            return user

        except Exception as e:
            logger.error(f"Error authenticating user {email}: {e}")
            return None

    async def update_balance(
        self,
        db: AsyncSession,
        *,
        user: User,
        amount: Decimal
    ) -> Optional[User]:
        """
        Обновление баланса пользователя - КЛЮЧЕВОЕ для системы баланса.

        Args:
            db: Сессия базы данных
            user: Пользователь
            amount: Сумма изменения (может быть отрицательной)

        Returns:
            Optional[User]: Обновленный пользователь или None
        """
        try:
            new_balance = user.balance + amount

            if new_balance < 0:
                raise ValueError("Insufficient balance")

            user.balance = new_balance
            user.updated_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(user)

            logger.info(f"Updated balance for user {user.id}: {amount} (new balance: {new_balance})")
            return user

        except ValueError:
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating balance for user {user.id}: {e}")
            return None

    async def update_last_login(self, db: AsyncSession, *, user_id: int) -> bool:
        """
        Обновление времени последнего входа.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя

        Returns:
            bool: Успешность операции
        """
        try:
            result = await db.execute(
                update(User)
                .where(User.id == user_id)
                .values(
                    last_login=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
            )
            await db.commit()
            return result.rowcount > 0

        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating last login for user {user_id}: {e}")
            return False

    async def verify_user_email(self, db: AsyncSession, *, user_id: int) -> Optional[User]:
        """
        Подтверждение email пользователя.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя

        Returns:
            Optional[User]: Пользователь с подтвержденным email или None
        """
        try:
            user = await self.get(db, id=user_id)
            if not user:
                return None

            user.is_verified = True
            user.email_verification_token = None
            user.email_verification_expires = None
            user.updated_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(user)

            logger.info(f"Verified email for user {user_id}")
            return user

        except Exception as e:
            await db.rollback()
            logger.error(f"Error verifying email for user {user_id}: {e}")
            return None

    async def get_user_order_stats(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Получение статистики заказов пользователя - для раздела "Мои покупки".

        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            days: Период в днях

        Returns:
            Dict[str, Any]: Статистика заказов
        """
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)

            # Общее количество заказов
            total_orders_result = await db.execute(
                select(func.count(Order.id))
                .where(
                    and_(
                        Order.user_id == user_id,
                        Order.created_at >= start_date
                    )
                )
            )
            total_orders = total_orders_result.scalar() or 0

            # Общая сумма
            total_amount_result = await db.execute(
                select(func.sum(Order.total_amount))
                .where(
                    and_(
                        Order.user_id == user_id,
                        Order.created_at >= start_date,
                        Order.status.in_(["paid", "completed"])
                    )
                )
            )
            total_amount = total_amount_result.scalar() or Decimal('0.00000000')

            # Последний заказ
            last_order_result = await db.execute(
                select(Order.created_at)
                .where(Order.user_id == user_id)
                .order_by(desc(Order.created_at))
                .limit(1)
            )
            last_order_date = last_order_result.scalar()

            # Средняя сумма заказа
            average_amount = total_amount / max(total_orders, 1)

            return {
                "total_orders": total_orders,
                "total_amount": str(total_amount),
                "average_amount": str(average_amount),
                "last_order_date": last_order_date.isoformat() if last_order_date else None
            }

        except Exception as e:
            logger.error(f"Error getting order stats for user {user_id}: {e}")
            return {
                "total_orders": 0,
                "total_amount": "0.00000000",
                "average_amount": "0.00000000",
                "last_order_date": None
            }

    async def get_user_proxy_stats(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Получение статистики прокси пользователя.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            days: Период в днях

        Returns:
            Dict[str, Any]: Статистика прокси
        """
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)
            current_time = datetime.now(timezone.utc)

            # Активные прокси
            active_count_result = await db.execute(
                select(func.count(ProxyPurchase.id))
                .where(
                    and_(
                        ProxyPurchase.user_id == user_id,
                        ProxyPurchase.is_active.is_(True),
                        ProxyPurchase.expires_at > current_time
                    )
                )
            )
            active_count = active_count_result.scalar() or 0

            # Всего куплено за период
            total_purchased_result = await db.execute(
                select(func.count(ProxyPurchase.id))
                .where(
                    and_(
                        ProxyPurchase.user_id == user_id,
                        ProxyPurchase.created_at >= start_date
                    )
                )
            )
            total_purchased = total_purchased_result.scalar() or 0

            return {
                "active_count": active_count,
                "total_purchased": total_purchased
            }

        except Exception as e:
            logger.error(f"Error getting proxy stats for user {user_id}: {e}")
            return {
                "active_count": 0,
                "total_purchased": 0
            }

    async def deactivate_user(self, db: AsyncSession, *, user_id: int) -> bool:
        """
        Деактивация пользователя.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя

        Returns:
            bool: Успешность операции
        """
        try:
            result = await db.execute(
                update(User)
                .where(User.id == user_id)
                .values(
                    is_active=False,
                    updated_at=datetime.now(timezone.utc)
                )
            )
            await db.commit()

            success = result.rowcount > 0
            if success:
                logger.info(f"Deactivated user {user_id}")
            return success

        except Exception as e:
            await db.rollback()
            logger.error(f"Error deactivating user {user_id}: {e}")
            return False

    async def reactivate_user(self, db: AsyncSession, *, user_id: int) -> bool:
        """
        Реактивация пользователя.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя

        Returns:
            bool: Успешность операции
        """
        try:
            result = await db.execute(
                update(User)
                .where(User.id == user_id)
                .values(
                    is_active=True,
                    updated_at=datetime.now(timezone.utc)
                )
            )
            await db.commit()

            success = result.rowcount > 0
            if success:
                logger.info(f"Reactivated user {user_id}")
            return success

        except Exception as e:
            await db.rollback()
            logger.error(f"Error reactivating user {user_id}: {e}")
            return False

    async def search_users(
        self,
        db: AsyncSession,
        *,
        query: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """
        Поиск пользователей.

        Args:
            db: Сессия базы данных
            query: Поисковый запрос
            skip: Пропустить записей
            limit: Максимум записей

        Returns:
            List[User]: Список найденных пользователей
        """
        try:
            search_pattern = f"%{query.strip()}%"

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
            logger.error(f"Error searching users: {e}")
            return []

    async def count_search_results(self, db: AsyncSession, *, query: str) -> int:
        """
        Подсчет результатов поиска пользователей.

        Args:
            db: Сессия базы данных
            query: Поисковый запрос

        Returns:
            int: Количество найденных пользователей
        """
        try:
            search_pattern = f"%{query.strip()}%"

            result = await db.execute(
                select(func.count(User.id))
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
            )
            return result.scalar() or 0

        except Exception as e:
            logger.error(f"Error counting search results: {e}")
            return 0

    async def get_user_activity(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Получение активности пользователя.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            days: Период в днях

        Returns:
            Dict[str, Any]: Данные активности
        """
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)

            # Количество заказов
            orders_result = await db.execute(
                select(func.count(Order.id))
                .where(
                    and_(
                        Order.user_id == user_id,
                        Order.created_at >= start_date
                    )
                )
            )
            orders_count = orders_result.scalar() or 0

            # Количество транзакций
            transactions_result = await db.execute(
                select(func.count(Transaction.id))
                .where(
                    and_(
                        Transaction.user_id == user_id,
                        Transaction.created_at >= start_date
                    )
                )
            )
            transactions_count = transactions_result.scalar() or 0

            return {
                "orders_count": orders_count,
                "transactions_count": transactions_count,
                "period_days": days
            }

        except Exception as e:
            logger.error(f"Error getting user activity: {e}")
            return {
                "orders_count": 0,
                "transactions_count": 0,
                "period_days": days
            }

    async def export_user_data(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        include_orders: bool = True,
        include_transactions: bool = True,
        include_proxies: bool = True
    ) -> Dict[str, Any]:
        """
        Экспорт данных пользователя (GDPR).

        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            include_orders: Включать заказы
            include_transactions: Включать транзакции
            include_proxies: Включать прокси

        Returns:
            Dict[str, Any]: Экспортированные данные
        """
        try:
            user = await self.get(db, id=user_id)
            if not user:
                return {}

            export_data = {
                "user_profile": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "balance": str(user.balance),
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "last_login": user.last_login.isoformat() if user.last_login else None
                }
            }

            if include_orders:
                orders_result = await db.execute(
                    select(Order)
                    .where(Order.user_id == user_id)
                    .order_by(desc(Order.created_at))
                )
                orders = list(orders_result.scalars().all())
                export_data["orders"] = [
                    {
                        "order_number": order.order_number,
                        "total_amount": str(order.total_amount),
                        "status": order.status.value,
                        "created_at": order.created_at.isoformat()
                    }
                    for order in orders
                ]

            if include_transactions:
                transactions_result = await db.execute(
                    select(Transaction)
                    .where(Transaction.user_id == user_id)
                    .order_by(desc(Transaction.created_at))
                )
                transactions = list(transactions_result.scalars().all())
                export_data["transactions"] = [
                    {
                        "amount": str(transaction.amount),
                        "transaction_type": transaction.transaction_type.value,
                        "status": transaction.status.value,
                        "created_at": transaction.created_at.isoformat()
                    }
                    for transaction in transactions
                ]

            return export_data

        except Exception as e:
            logger.error(f"Error exporting user data: {e}")
            return {}

    async def deactivate_user_proxies(self, db: AsyncSession, *, user_id: int) -> int:
        """
        Деактивация всех прокси пользователя.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя

        Returns:
            int: Количество деактивированных прокси
        """
        try:
            result = await db.execute(
                update(ProxyPurchase)
                .where(ProxyPurchase.user_id == user_id)
                .values(
                    is_active=False,
                    updated_at=datetime.now(timezone.utc)
                )
            )
            await db.commit()

            count = result.rowcount or 0
            if count > 0:
                logger.info(f"Deactivated {count} proxies for user {user_id}")
            return count

        except Exception as e:
            await db.rollback()
            logger.error(f"Error deactivating proxies for user {user_id}: {e}")
            return 0


user_crud = CRUDUser(User)
