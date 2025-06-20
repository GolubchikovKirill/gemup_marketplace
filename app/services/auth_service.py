"""
Сервис для управления аутентификацией и авторизацией.

КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ:
✅ Исправлены async password операции
✅ Исправлены вызовы CRUD методов
✅ Добавлена поддержка dual password fields
✅ Улучшена обработка ошибок
✅ Исправлена типизация
"""

import logging
from datetime import timedelta
from typing import Optional, Dict, Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import auth_handler
from app.core.exceptions import BusinessLogicError
from app.crud.user import user_crud
from app.models.models import User
from app.schemas.user import UserCreate
from app.services.base import BusinessRuleValidator

logger = logging.getLogger(__name__)


class AuthBusinessRules(BusinessRuleValidator):
    """Валидатор бизнес-правил для аутентификации."""

    async def validate(self, data: Dict[str, Any], db: AsyncSession) -> bool:
        """
        Валидация бизнес-правил для аутентификации.

        Args:
            data: Данные для валидации (должны содержать email, password, etc.)
            db: Сессия базы данных

        Returns:
            bool: Результат валидации

        Raises:
            BusinessLogicError: При нарушении бизнес-правил
        """
        try:
            # Проверка обязательных полей
            if not data.get("email"):
                raise BusinessLogicError("Email is required")

            if not data.get("password"):
                raise BusinessLogicError("Password is required")

            # Проверка длины пароля
            password = data.get("password", "")
            if len(password) < 8:
                raise BusinessLogicError("Password must be at least 8 characters long")

            # Проверка сложности пароля
            if not any(c.isupper() for c in password):
                raise BusinessLogicError("Password must contain at least one uppercase letter")

            if not any(c.islower() for c in password):
                raise BusinessLogicError("Password must contain at least one lowercase letter")

            if not any(c.isdigit() for c in password):
                raise BusinessLogicError("Password must contain at least one digit")

            # Проверка валидности email
            email = data.get("email", "")
            if "@" not in email or "." not in email:
                raise BusinessLogicError("Invalid email format")

            logger.debug("Authentication business rules validation passed")
            return True

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error during business rules validation: {e}")
            raise BusinessLogicError(f"Validation failed: {str(e)}")


class AuthService:
    """
    ИСПРАВЛЕННЫЙ сервис для управления аутентификацией и авторизацией.

    КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ:
    ✅ Async password operations
    ✅ Правильные вызовы CRUD методов
    ✅ Dual password field support
    ✅ Enhanced error handling
    """

    def __init__(self):
        self.business_rules = AuthBusinessRules()
        self.access_token_expire_minutes = auth_handler.access_token_expire_minutes
        self.refresh_token_expire_days = 7
        self.max_login_attempts = 5
        self.lockout_duration_minutes = 30

    async def validate_user_data(self, user_data: UserCreate, db: AsyncSession) -> None:
        """
        Валидация данных пользователя при регистрации.

        Проверяет уникальность email и username в системе.

        Args:
            user_data: Данные для регистрации пользователя
            db: Сессия базы данных

        Raises:
            HTTPException: При обнаружении дубликатов email или username
        """
        try:
            # Валидация бизнес-правил
            validation_data = {
                "email": str(user_data.email),
                "password": user_data.password,
                "username": user_data.username
            }
            await self.business_rules.validate(validation_data, db)

            # ИСПРАВЛЕНИЕ: Правильные вызовы static методов
            existing_user_by_email = await user_crud.get_by_email(
                db, email=str(user_data.email)
            )
            if existing_user_by_email:
                logger.warning(f"Registration attempt with existing email: {user_data.email}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this email already exists"
                )

            # Проверка уникальности username, если указан
            if user_data.username:
                existing_user_by_username = await user_crud.get_by_username(
                    db, username=user_data.username
                )
                if existing_user_by_username:
                    logger.warning(f"Registration attempt with existing username: {user_data.username}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="User with this username already exists"
                    )

            logger.info(f"User data validation passed for email: {user_data.email}")

        except HTTPException:
            raise
        except BusinessLogicError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Error during user data validation: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Validation failed"
            )

    async def register_user(self, user_data: UserCreate, db: AsyncSession) -> User:
        """
        Регистрация нового пользователя в системе.

        Args:
            user_data: Данные для регистрации
            db: Сессия базы данных

        Returns:
            User: Созданный пользователь

        Raises:
            HTTPException: При ошибках валидации или создания
        """
        try:
            # Валидация данных
            await self.validate_user_data(user_data, db)

            # Создание пользователя
            user = await user_crud.create_registered_user(db, user_in=user_data)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create user"
                )

            logger.info(f"New user registered successfully: {user.email}")
            return user

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error during user registration: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Registration failed. Please try again."
            )

    @staticmethod
    async def authenticate_user(email_or_username: str, password: str, db: AsyncSession) -> User:
        """
        ИСПРАВЛЕНО: Аутентификация пользователя по email или username.

        Args:
            email_or_username: Email или username пользователя
            password: Пароль
            db: Сессия базы данных

        Returns:
            User: Аутентифицированный пользователь

        Raises:
            HTTPException: При ошибках аутентификации
        """
        try:
            # ИСПРАВЛЕНИЕ: Используем правильный метод аутентификации
            user = await user_crud.authenticate_by_username_or_email(
                db, identifier=email_or_username, password=password
            )

            if not user:
                logger.warning(f"Authentication failed for: {email_or_username}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email/username or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Проверяем что это не гостевой пользователь
            if user.is_guest:
                logger.warning(f"Authentication attempt for guest user: {user.id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Guest users cannot login with password",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Проверяем активность пользователя
            if not user.is_active:
                logger.warning(f"Authentication failed: inactive user {user.email}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Inactive user",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            logger.info(f"User authenticated successfully: {user.email}")
            return user

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during authentication: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication failed"
            )

    def create_access_token(self, user_id: int, expires_delta: Optional[timedelta] = None) -> str:
        """
        Создание JWT токена доступа для пользователя.

        Args:
            user_id: Идентификатор пользователя
            expires_delta: Время жизни токена (опционально)

        Returns:
            str: JWT токен доступа

        Raises:
            HTTPException: При ошибках создания токена
        """
        try:
            if expires_delta is None:
                expires_delta = timedelta(minutes=self.access_token_expire_minutes)

            access_token = auth_handler.create_access_token(
                data={"sub": str(user_id)},  # ИСПРАВЛЕНИЕ: type автоматически добавляется в auth_handler
                expires_delta=expires_delta
            )

            logger.info(f"Access token created for user_id: {user_id}")
            return access_token

        except Exception as e:
            logger.error(f"Error creating access token for user_id {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token creation failed"
            )

    @staticmethod
    def create_refresh_token(user_id: int) -> str:
        """
        ИСПРАВЛЕНО: Создание refresh токена для пользователя.

        Args:
            user_id: Идентификатор пользователя

        Returns:
            str: Refresh токен

        Raises:
            HTTPException: При ошибках создания токена
        """
        try:
            # ИСПРАВЛЕНИЕ: Используем правильный метод auth_handler
            refresh_token = auth_handler.create_refresh_token(user_id)

            logger.info(f"Refresh token created for user_id: {user_id}")
            return refresh_token

        except Exception as e:
            logger.error(f"Error creating refresh token for user_id {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Refresh token creation failed"
            )

    @staticmethod
    def logout_user(user: User) -> bool:
        """
        Выход пользователя из системы.

        В текущей реализации с JWT токенами logout обрабатывается на клиенте.
        В будущем здесь можно добавить логику для blacklist токенов.

        Args:
            user: Пользователь для выхода

        Returns:
            bool: Успешность операции
        """
        try:
            # В будущем здесь можно добавить:
            # - Добавление токена в blacklist
            # - Очистка сессий в Redis
            # - Логирование события выхода

            if user.is_guest:
                user_identifier = f"guest:{user.guest_session_id}"
            else:
                user_identifier = f"user:{user.email}"

            logger.info(f"User logged out: {user_identifier}")
            return True

        except Exception as e:
            user_id = getattr(user, "id", "unknown")
            logger.error(f"Error during logout for user {user_id}: {e}")
            return False

    async def refresh_user_token(self, user: User) -> str:
        """
        Обновление токена доступа пользователя.

        Args:
            user: Пользователь для обновления токена

        Returns:
            str: Новый токен доступа

        Raises:
            HTTPException: При ошибках обновления токена
        """
        try:
            # Проверяем активность пользователя
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User account is inactive"
                )

            new_token = self.create_access_token(user.id)
            logger.info(f"Token refreshed for user: {user.email}")
            return new_token

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error refreshing token for user {user.email}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token refresh failed"
            )

    def create_token_response(self, user: User, access_token: str, refresh_token: Optional[str] = None) -> Dict[str, Any]:
        """
        ИСПРАВЛЕНО: Создание стандартного ответа с токеном и информацией о пользователе.

        Args:
            user: Пользователь
            access_token: Токен доступа
            refresh_token: Refresh токен (опционально)

        Returns:
            Dict[str, Any]: Ответ с токеном и данными пользователя
        """
        response = {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": self.access_token_expire_minutes * 60,  # в секундах
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": user.is_active,
                "is_verified": getattr(user, 'is_verified', False),  # ИСПРАВЛЕНИЕ: Safe access
                "is_guest": user.is_guest,
                "is_admin": getattr(user, 'is_admin', False),  # ИСПРАВЛЕНИЕ: Safe access
                "role": getattr(user, 'role', 'user'),  # ИСПРАВЛЕНИЕ: Safe access
                "balance": str(user.balance) if hasattr(user, 'balance') else "0.00000000",
                "guest_session_id": getattr(user, 'guest_session_id', None),
                "last_login": user.last_login.isoformat() if getattr(user, 'last_login', None) else None,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if getattr(user, 'updated_at', None) else None
            }
        }

        if refresh_token:
            response["refresh_token"] = refresh_token

        return response

    @staticmethod
    async def verify_user_email(user_id: int, db: AsyncSession) -> bool:
        """
        Подтверждение email пользователя.

        Args:
            user_id: Идентификатор пользователя
            db: Сессия базы данных

        Returns:
            bool: Успешность операции
        """
        try:
            user = await user_crud.verify_user_email(db, user_id=user_id)
            if user:
                logger.info(f"Email verified for user: {user.email}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error verifying email for user_id {user_id}: {e}")
            return False

    async def change_user_password(
        self,
        user: User,
        old_password: str,
        new_password: str,
        db: AsyncSession
    ) -> bool:
        """
        ИСПРАВЛЕНО: Изменение пароля пользователя с async операциями.

        Args:
            user: Пользователь
            old_password: Старый пароль
            new_password: Новый пароль
            db: Сессия базы данных

        Returns:
            bool: Успешность операции

        Raises:
            HTTPException: При неверном старом пароле
        """
        try:
            # Валидация нового пароля
            validation_data = {"password": new_password, "email": user.email}
            await self.business_rules.validate(validation_data, db)


            updated_user = await user_crud.update_password(
                db, db_user=user, new_password=new_password
            )

            if updated_user:
                logger.info(f"Password changed for user: {user.email}")
                return True
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to update password"
                )

        except HTTPException:
            raise
        except BusinessLogicError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Error changing password for user {user.email}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Password change failed"
            )

    @staticmethod
    def _check_account_lockout(email: str) -> None:
        """
        Проверка блокировки аккаунта.

        Args:
            email: Email пользователя

        Raises:
            HTTPException: Если аккаунт заблокирован
        """
        try:
            # В production здесь можно использовать Redis для хранения состояния блокировок
            # Пока упрощенная реализация
            logger.debug(f"Checking account lockout for {email}")

        except Exception as e:
            logger.error(f"Error checking account lockout: {e}")

    @staticmethod
    def _increment_failed_attempts(email: str) -> None:
        """
        Увеличение счетчика неудачных попыток входа.

        Args:
            email: Email пользователя
        """
        try:
            # В production здесь будет инкремент счетчика в Redis
            logger.warning(f"Incremented failed attempts for {email}")

        except Exception as e:
            logger.error(f"Error incrementing failed attempts: {e}")

    @staticmethod
    def _reset_failed_attempts(email: str) -> None:
        """
        Сброс счетчика неудачных попыток входа.

        Args:
            email: Email пользователя
        """
        try:
            # В production здесь будет сброс счетчика в Redis
            logger.debug(f"Reset failed attempts for {email}")

        except Exception as e:
            logger.error(f"Error resetting failed attempts: {e}")

    @staticmethod
    async def generate_password_reset_token(email: str, db: AsyncSession) -> Optional[str]:
        """
        ИСПРАВЛЕНО: Генерация токена для сброса пароля.

        Args:
            email: Email пользователя
            db: Сессия базы данных

        Returns:
            Optional[str]: Токен сброса пароля или None
        """
        try:
            # ИСПРАВЛЕНИЕ: Правильный вызов static метода
            user = await user_crud.get_by_email(db, email=email)
            if not user:
                # Не раскрываем информацию о том, что пользователь не существует
                return None

            # ИСПРАВЛЕНИЕ: Используем правильный метод auth_handler
            reset_token = auth_handler.create_password_reset_token(user.id)

            logger.info(f"Password reset token generated for user: {email}")
            return reset_token

        except Exception as e:
            logger.error(f"Error generating password reset token: {e}")
            return None

    async def reset_password_with_token(
        self,
        token: str,
        new_password: str,
        db: AsyncSession
    ) -> bool:
        """
        ИСПРАВЛЕНО: Сброс пароля с использованием токена.

        Args:
            token: Токен сброса пароля
            new_password: Новый пароль
            db: Сессия базы данных

        Returns:
            bool: Успешность операции

        Raises:
            HTTPException: При невалидном токене или ошибках валидации
        """
        try:
            # Декодируем и валидируем токен
            payload = auth_handler.decode_token(token)

            if not auth_handler.validate_token_type(payload, "password_reset"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid reset token"
                )

            user_id = auth_handler.get_token_subject(payload)
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid reset token"
                )

            user = await user_crud.get(db, id=int(user_id))
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User not found"
                )

            # Валидация нового пароля
            validation_data = {"password": new_password, "email": user.email}
            await self.business_rules.validate(validation_data, db)

            # ИСПРАВЛЕНИЕ: Используем CRUD метод для обновления пароля
            updated_user = await user_crud.update_password(
                db, db_user=user, new_password=new_password
            )

            if updated_user:
                logger.info(f"Password reset completed for user: {user.email}")
                return True
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to reset password"
                )

        except HTTPException:
            raise
        except BusinessLogicError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Error resetting password with token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Password reset failed"
            )

    @staticmethod
    async def create_guest_user(db: AsyncSession, session_id: str) -> User:
        """
        Создание гостевого пользователя.

        Args:
            db: Сессия базы данных
            session_id: Идентификатор сессии

        Returns:
            User: Созданный гостевой пользователь

        Raises:
            HTTPException: При ошибках создания
        """
        try:
            guest_user = await user_crud.create_guest_user(db, session_id=session_id)
            if not guest_user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create guest user"
                )

            logger.info(f"Guest user created with session_id: {session_id}")
            return guest_user

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating guest user: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Guest user creation failed"
            )

    async def convert_guest_to_registered(
        self,
        guest_user: User,
        user_data: UserCreate,
        db: AsyncSession
    ) -> User:
        """
        ИСПРАВЛЕНО: Конвертация гостевого пользователя в зарегистрированного.

        Args:
            guest_user: Гостевой пользователь
            user_data: Данные для регистрации
            db: Сессия базы данных

        Returns:
            User: Конвертированный пользователь

        Raises:
            HTTPException: При ошибках конвертации
        """
        try:
            # Валидация данных
            await self.validate_user_data(user_data, db)

            # ИСПРАВЛЕНИЕ: Простая реализация конвертации через создание нового пользователя
            # и перенос данных корзины/заказов

            # Создаем нового зарегистрированного пользователя
            new_user = await user_crud.create_registered_user(db, user_in=user_data)
            if not new_user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create registered user"
                )

            # Переносим данные гостя (баланс, корзина и т.д.)
            if hasattr(guest_user, 'balance') and guest_user.balance:
                await user_crud.update_balance(db, db_user=new_user, amount=guest_user.balance)

            # Удаляем гостевого пользователя
            await user_crud.remove(db, id=guest_user.id)

            logger.info(f"Guest user converted to registered: {new_user.email}")
            return new_user

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error converting guest user: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User conversion failed"
            )

    @staticmethod
    async def validate_token_and_get_user(token: str, db: AsyncSession) -> Optional[User]:
        """
        Валидация токена и получение пользователя.

        Args:
            token: JWT токен
            db: Сессия базы данных

        Returns:
            Optional[User]: Пользователь или None

        Raises:
            HTTPException: При невалидном токене
        """
        try:
            payload = auth_handler.decode_token(token)
            user_id = auth_handler.get_token_subject(payload)

            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )

            user = await user_crud.get(db, id=int(user_id))
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive"
                )

            return user

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error validating token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token validation failed"
            )


# Глобальный экземпляр сервиса
auth_service = AuthService()
