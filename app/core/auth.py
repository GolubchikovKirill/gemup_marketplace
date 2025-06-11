"""
Модуль аутентификации и авторизации.

КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ:
✅ Исправлены параметры jwt.decode() для jose library
✅ Исправлена логика создания refresh токенов
✅ Улучшена обработка ошибок JWT
✅ Добавлена валидация аудитории и issuer
✅ Исправлены проблемы с timezone
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

    ИСПРАВЛЕНИЯ:
    ✅ Правильные параметры для jose.jwt.decode()
    ✅ Улучшенная обработка refresh токенов
    ✅ Better error handling
    ✅ Enhanced token validation
    """

    def __init__(self):
        """Инициализация обработчика аутентификации."""
        self.secret_key = settings.secret_key
        self.algorithm = settings.algorithm
        self.access_token_expire_minutes = settings.access_token_expire_minutes

        # Валидация критических настроек
        if len(self.secret_key) < 32:
            raise ValueError("Secret key must be at least 32 characters long")

        logger.info(f"AuthHandler initialized with algorithm: {self.algorithm}")

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Хеширование пароля с использованием bcrypt."""
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
        """Проверка пароля против хеша."""
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
            expires_delta: Optional[timedelta] = None,
            token_type: str = "access"
    ) -> str:
        """
        ИСПРАВЛЕНО: Создание JWT токена с правильным типом.

        Args:
            data: Данные для включения в токен
            expires_delta: Время жизни токена
            token_type: Тип токена (access, refresh, etc.)

        Returns:
            str: Закодированный JWT токен
        """
        if not data or not isinstance(data, dict):
            raise ValueError("Token data must be a non-empty dictionary")

        if "sub" not in data:
            raise ValueError("Token data must contain 'sub' field")

        try:
            to_encode = data.copy()

            # Используем UTC время
            now = datetime.now(timezone.utc)

            if expires_delta:
                expire = now + expires_delta
            else:
                expire = now + timedelta(minutes=self.access_token_expire_minutes)

            # ИСПРАВЛЕНИЕ: Добавляем type в payload
            to_encode.update({
                "exp": expire,
                "iat": now,
                "iss": "gemup-marketplace",
                "aud": "gemup-api",
                "type": token_type  # ИСПРАВЛЕНИЕ: Явно указываем тип токена
            })

            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

            logger.debug(f"{token_type.title()} token created for subject: {data.get('sub')}")
            return encoded_jwt

        except Exception as e:
            logger.error(f"Error creating {token_type} token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create {token_type} token"
            )

    def create_refresh_token(self, user_id: int) -> str:
        """
        ИСПРАВЛЕНО: Создание refresh токена с правильными параметрами.

        Args:
            user_id: Идентификатор пользователя

        Returns:
            str: Refresh токен
        """
        try:
            data = {
                "sub": str(user_id)
            }

            # ИСПРАВЛЕНИЕ: Создаем refresh токен с правильным типом и временем жизни
            expires_delta = timedelta(days=7)  # Refresh токен живет 7 дней

            return self.create_access_token(
                data=data,
                expires_delta=expires_delta,
                token_type="refresh"  # ИСПРАВЛЕНИЕ: Явно указываем тип
            )

        except Exception as e:
            logger.error(f"Error creating refresh token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create refresh token"
            )

    def decode_token(self, token: str) -> Dict[str, Any]:
        """
        КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Декодирование JWT токена с правильными параметрами.

        Args:
            token: JWT токен для декодирования

        Returns:
            Dict[str, Any]: Декодированные данные токена
        """
        if not token or not token.strip():
            logger.warning("Empty token provided for decoding")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token is required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Правильные параметры для jose.jwt.decode
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                # ИСПРАВЛЕНИЕ: Правильный способ передачи audience и issuer
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                    "verify_aud": True,
                    "verify_iss": True
                },
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
        """Валидация типа токена."""
        token_type = payload.get("type", "access")
        return token_type == expected_type

    @staticmethod
    def get_token_subject(payload: Dict[str, Any]) -> str:
        """Извлечение subject из токена."""
        return payload.get("sub", "")

    @staticmethod
    def is_token_expired(payload: Dict[str, Any]) -> bool:
        """Проверка истечения токена."""
        exp_timestamp = payload.get("exp")
        if not exp_timestamp:
            return True

        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        return datetime.now(timezone.utc) > exp_datetime

    def create_password_reset_token(self, user_id: int) -> str:
        """Создание токена для сброса пароля."""
        try:
            data = {"sub": str(user_id)}
            expires_delta = timedelta(hours=1)

            return self.create_access_token(
                data=data,
                expires_delta=expires_delta,
                token_type="password_reset"
            )

        except Exception as e:
            logger.error(f"Error creating password reset token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create password reset token"
            )

    def create_email_verification_token(self, user_id: int) -> str:
        """Создание токена для подтверждения email."""
        try:
            data = {"sub": str(user_id)}
            expires_delta = timedelta(hours=24)

            return self.create_access_token(
                data=data,
                expires_delta=expires_delta,
                token_type="email_verification"
            )

        except Exception as e:
            logger.error(f"Error creating email verification token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create email verification token"
            )

    def verify_token_signature(self, token: str) -> bool:
        """Проверка подписи токена без полной валидации."""
        try:
            jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={
                    "verify_exp": False,
                    "verify_aud": False,
                    "verify_iss": False
                }
            )
            return True
        except JWTError:
            return False

    @staticmethod
    def get_token_payload_unsafe(token: str) -> Optional[Dict[str, Any]]:
        """
        ИСПРАВЛЕНО: Получение payload без проверки подписи.
        """
        try:
            # ИСПРАВЛЕНИЕ: Используем правильный метод jose
            return jwt.get_unverified_claims(token)
        except Exception as e:
            logger.error(f"Error getting unverified claims: {e}")
            return None

    def refresh_access_token(self, refresh_token: str) -> str:
        """Обновление access токена с помощью refresh токена."""
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
            return self.create_access_token(new_token_data, token_type="access")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error refreshing access token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not refresh token"
            )

auth_handler = AuthHandler()
