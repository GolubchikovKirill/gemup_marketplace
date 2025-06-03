"""
Модуль аутентификации и авторизации.

Обеспечивает функциональность для работы с JWT токенами,
хеширования паролей и валидации учетных данных пользователей.
Использует современные криптографические алгоритмы для безопасности.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from jose import jwt
from jose.exceptions import JWTError, ExpiredSignatureError, JWTClaimsError
from passlib.context import CryptContext
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)

# Контекст для хеширования паролей с использованием bcrypt
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # Увеличиваем rounds для большей безопасности
)


class AuthHandler:
    """
    Обработчик аутентификации и авторизации.

    Предоставляет методы для:
    - Хеширования и проверки паролей
    - Создания и валидации JWT токенов
    - Управления сессиями пользователей

    Использует современные криптографические стандарты и лучшие практики безопасности.
    """

    def __init__(self):
        """
        Инициализация обработчика аутентификации.

        Загружает настройки из конфигурации и выполняет базовую валидацию.
        """
        self.secret_key = settings.secret_key
        self.algorithm = settings.algorithm
        self.access_token_expire_minutes = settings.access_token_expire_minutes

        # Валидация критических настроек
        if len(self.secret_key) < 32:
            raise ValueError("Secret key must be at least 32 characters long")

        logger.info(f"AuthHandler initialized with algorithm: {self.algorithm}")

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
            hashed = pwd_context.hash(password)
            logger.debug("Password hashed successfully")
            return hashed
        except Exception as e:
            logger.error(f"Error hashing password: {e}")
            raise ValueError("Failed to hash password")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Проверка пароля против хеша.

        Args:
            plain_password: Пароль в открытом виде
            hashed_password: Хешированный пароль из базы данных

        Returns:
            bool: True если пароль корректный, False в противном случае
        """
        if not plain_password or not hashed_password:
            logger.warning("Empty password or hash provided for verification")
            return False

        try:
            result = pwd_context.verify(plain_password, hashed_password)
            if result:
                logger.debug("Password verification successful")
            else:
                logger.debug("Password verification failed")
            return result
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False

    def create_access_token(
            self,
            data: Dict[str, Any],
            expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Создание JWT токена доступа.

        Args:
            data: Данные для включения в токен (обычно {"sub": user_id})
            expires_delta: Время жизни токена (опционально)

        Returns:
            str: Закодированный JWT токен

        Raises:
            ValueError: При некорректных входных данных
            HTTPException: При ошибке создания токена
        """
        if not data or not isinstance(data, dict):
            raise ValueError("Token data must be a non-empty dictionary")

        if "sub" not in data:
            raise ValueError("Token data must contain 'sub' field")

        try:
            to_encode = data.copy()

            # Используем UTC время для избежания проблем с часовыми поясами
            now = datetime.now(timezone.utc)

            if expires_delta:
                expire = now + expires_delta
            else:
                expire = now + timedelta(minutes=self.access_token_expire_minutes)

            # Добавляем стандартные JWT claims
            to_encode.update({
                "exp": expire,
                "iat": now,  # issued at
                "iss": "gemup-marketplace",  # issuer
                "aud": "gemup-api"  # audience
            })

            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

            logger.debug(f"Access token created for subject: {data.get('sub')}")
            return encoded_jwt

        except Exception as e:
            logger.error(f"Error creating access token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create access token"
            )

    def create_refresh_token(self, user_id: int) -> str:
        """
        Создание refresh токена для обновления access токена.

        Args:
            user_id: Идентификатор пользователя

        Returns:
            str: Refresh токен
        """
        try:
            data = {
                "sub": str(user_id),
                "type": "refresh"
            }

            # Refresh токен живет дольше (7 дней)
            expires_delta = timedelta(days=7)

            return self.create_access_token(data, expires_delta)

        except Exception as e:
            logger.error(f"Error creating refresh token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create refresh token"
            )

    def decode_token(self, token: str) -> Dict[str, Any]:
        """
        Декодирование и валидация JWT токена.

        Args:
            token: JWT токен для декодирования

        Returns:
            Dict[str, Any]: Декодированные данные токена

        Raises:
            HTTPException: При невалидном или истекшем токене
        """
        if not token or not token.strip():
            logger.warning("Empty token provided for decoding")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token is required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            # ИСПРАВЛЕНО: Используем правильные параметры для jose.jwt
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                audience="gemup-api",
                issuer="gemup-marketplace"
            )

            # Проверяем наличие обязательных полей
            if "sub" not in payload:
                logger.warning("Token missing 'sub' claim")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token format",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            logger.debug(f"Token decoded successfully for subject: {payload.get('sub')}")
            return payload

        except ExpiredSignatureError:
            logger.warning("Expired token provided")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except JWTClaimsError as e:
            logger.warning(f"JWT claims error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except JWTError as e:
            logger.warning(f"JWT error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            logger.error(f"Unexpected error during token decoding: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @staticmethod
    def validate_token_type(payload: Dict[str, Any], expected_type: str = "access") -> bool:
        """
        Валидация типа токена.

        Args:
            payload: Декодированные данные токена
            expected_type: Ожидаемый тип токена

        Returns:
            bool: True если тип токена корректный
        """
        token_type = payload.get("type", "access")
        return token_type == expected_type

    @staticmethod
    def get_token_subject(payload: Dict[str, Any]) -> str:
        """
        Извлечение subject (пользователя) из токена.

        Args:
            payload: Декодированные данные токена

        Returns:
            str: Subject токена (обычно user_id)
        """
        return payload.get("sub", "")

    @staticmethod
    def is_token_expired(payload: Dict[str, Any]) -> bool:
        """
        Проверка истечения токена.

        Args:
            payload: Декодированные данные токена

        Returns:
            bool: True если токен истек
        """
        exp_timestamp = payload.get("exp")
        if not exp_timestamp:
            return True

        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        return datetime.now(timezone.utc) > exp_datetime

    def create_password_reset_token(self, user_id: int) -> str:
        """
        Создание токена для сброса пароля.

        Args:
            user_id: Идентификатор пользователя

        Returns:
            str: Токен для сброса пароля (действует 1 час)
        """
        try:
            data = {
                "sub": str(user_id),
                "type": "password_reset"
            }

            # Токен сброса пароля живет 1 час
            expires_delta = timedelta(hours=1)

            return self.create_access_token(data, expires_delta)

        except Exception as e:
            logger.error(f"Error creating password reset token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create password reset token"
            )

    def create_email_verification_token(self, user_id: int) -> str:
        """
        Создание токена для подтверждения email.

        Args:
            user_id: Идентификатор пользователя

        Returns:
            str: Токен для подтверждения email (действует 24 часа)
        """
        try:
            data = {
                "sub": str(user_id),
                "type": "email_verification"
            }

            # Токен подтверждения email живет 24 часа
            expires_delta = timedelta(hours=24)

            return self.create_access_token(data, expires_delta)

        except Exception as e:
            logger.error(f"Error creating email verification token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create email verification token"
            )

    def verify_token_signature(self, token: str) -> bool:
        """
        Проверка подписи токена без полной валидации.

        Args:
            token: JWT токен

        Returns:
            bool: True если подпись валидна
        """
        try:
            # Декодируем без проверки времени жизни
            jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False, "verify_aud": False, "verify_iss": False}
            )
            return True
        except JWTError:
            return False

    def get_token_payload_unsafe(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Получение payload токена без проверки подписи (небезопасно).

        Используется только для отладки или получения информации из просроченных токенов.

        Args:
            token: JWT токен

        Returns:
            Optional[Dict[str, Any]]: Payload токена или None
        """
        try:
            return jwt.get_unverified_claims(token)
        except Exception as e:
            logger.error(f"Error getting unverified claims: {e}")
            return None

    def refresh_access_token(self, refresh_token: str) -> str:
        """
        Обновление access токена с помощью refresh токена.

        Args:
            refresh_token: Refresh токен

        Returns:
            str: Новый access токен

        Raises:
            HTTPException: При невалидном refresh токене
        """
        try:
            # Декодируем refresh токен
            payload = self.decode_token(refresh_token)

            # Проверяем тип токена
            if not self.validate_token_type(payload, "refresh"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )

            # Получаем user_id
            user_id = int(self.get_token_subject(payload))

            # Создаем новый access токен
            new_token_data = {"sub": str(user_id)}
            return self.create_access_token(new_token_data)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error refreshing access token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not refresh token"
            )


# Глобальный экземпляр обработчика аутентификации
auth_handler = AuthHandler()
