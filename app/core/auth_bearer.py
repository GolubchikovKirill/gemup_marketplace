"""
JWT Bearer аутентификация для FastAPI.

КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ:
✅ Исправлено поле APIKey.key вместо APIKey.api_key
✅ Убран недостижимый код
✅ Добавлены явные return statements
✅ Static методы где возможно
✅ Убраны неиспользуемые параметры
✅ Упрощена логика валидации API ключей
"""

import logging
from typing import Optional, List

from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security.utils import get_authorization_scheme_param
from jose.exceptions import JWTError
from sqlalchemy import select

from app.core.auth import auth_handler

logger = logging.getLogger(__name__)


class JWTBearer(HTTPBearer):
    """
    ИСПРАВЛЕННАЯ схема аутентификации JWT Bearer.
    """

    def __init__(
        self,
        *,
        bearer_format: Optional[str] = None,
        scheme_name: Optional[str] = None,
        description: Optional[str] = None,
        auto_error: bool = True,
        verify_token: bool = True
    ):
        """
        Инициализация с правильными параметрами FastAPI.

        Args:
            bearer_format: Формат токена для OpenAPI (Python naming convention)
            scheme_name: Название схемы
            description: Описание для документации
            auto_error: Автоматически генерировать ошибки
            verify_token: Выполнять валидацию токена
        """
        super().__init__(
            bearerFormat=bearer_format or "JWT",
            scheme_name=scheme_name or "JWTBearer",
            description=description or "JWT Bearer token authentication",
            auto_error=auto_error
        )

        self.verify_token = verify_token

    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        """
        Возвращаем HTTPAuthorizationCredentials согласно FastAPI contract.

        Args:
            request: HTTP запрос FastAPI

        Returns:
            Optional[HTTPAuthorizationCredentials]: Credentials или None
        """
        credentials: Optional[HTTPAuthorizationCredentials] = await super().__call__(request)

        if not credentials:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authorization header is required",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            return None

        # Проверяем схему аутентификации
        if not self._is_valid_scheme(credentials.scheme):
            logger.warning(f"Invalid authentication scheme: {credentials.scheme}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid authentication scheme. Expected 'Bearer'",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # Проверяем формат токена
        token = credentials.credentials
        if not self._is_valid_token_format(token):
            logger.warning("Invalid JWT token format")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid token format",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # Валидируем токен если требуется
        if self.verify_token and not self._verify_jwt_token(token):
            logger.warning("JWT token verification failed")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid token or expired token",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # Логируем успешную аутентификацию
        self._log_successful_authentication(request, token)

        return credentials

    @staticmethod
    def _is_valid_scheme(scheme: str) -> bool:
        """Проверка схемы аутентификации."""
        return scheme.lower() == "bearer"

    @staticmethod
    def _is_valid_token_format(token: str) -> bool:
        """Базовая проверка формата JWT токена."""
        if not token or not isinstance(token, str):
            return False

        # JWT токен состоит из 3 частей, разделенных точками
        parts = token.split(".")
        if len(parts) != 3:
            return False

        # Каждая часть должна быть непустой
        if not all(part.strip() for part in parts):
            return False

        return True

    def _verify_jwt_token(self, token: str) -> bool:
        """Верификация JWT токена через auth_handler."""
        try:
            payload = auth_handler.decode_token(token)

            if not isinstance(payload, dict):
                logger.warning("Token payload is not a dictionary")
                return False

            # Проверяем наличие обязательных полей
            required_fields = ["sub", "exp"]
            missing_fields = [field for field in required_fields if field not in payload]
            if missing_fields:
                logger.warning(f"Token missing required fields: {missing_fields}")
                return False

            return True

        except HTTPException as e:
            logger.debug(f"Token verification failed: {e.detail}")
            return False
        except (ValueError, TypeError) as e:
            logger.error(f"Token validation error: {e}")
            return False
        except JWTError as e:
            logger.error(f"JWT processing error: {e}")
            return False

    @staticmethod
    def _log_successful_authentication(request: Request, token: str) -> None:
        """ИСПРАВЛЕНО: Static метод для логирования успешной аутентификации."""
        try:
            payload = auth_handler.decode_token(token)
            user_id = payload.get("sub", "unknown")

            client_ip = JWTBearer._get_client_ip(request)
            user_agent = request.headers.get("user-agent", "unknown")

            logger.debug(
                f"JWT authentication successful - "
                f"User: {user_id} - "
                f"IP: {client_ip} - "
                f"Path: {request.url.path} - "
                f"UserAgent: {user_agent[:50]}..."
            )

        except (HTTPException, ValueError, TypeError) as e:
            logger.error(f"Error logging authentication: {e}")

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """Получение IP адреса клиента."""
        # Проверяем заголовки прокси
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fallback на стандартный IP
        if request.client:
            return request.client.host

        return "unknown"


class OptionalJWTBearer(JWTBearer):
    """Опциональная JWT Bearer аутентификация."""

    def __init__(self, **kwargs):
        kwargs.setdefault("auto_error", False)
        super().__init__(**kwargs)

    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        """Опциональное извлечение токена."""
        try:
            return await super().__call__(request)
        except HTTPException:
            return None


class AdminJWTBearer(JWTBearer):
    """JWT Bearer с проверкой административных прав."""

    def _verify_jwt_token(self, token: str) -> bool:
        """Верификация с проверкой админских прав."""
        if not super()._verify_jwt_token(token):
            return False

        try:
            payload = auth_handler.decode_token(token)

            is_admin = payload.get("is_admin", False)
            user_role = payload.get("role", "user")

            if not is_admin and user_role != "admin":
                logger.warning(f"Non-admin user attempted admin access: {payload.get('sub')}")
                return False

            return True

        except (HTTPException, ValueError, TypeError) as e:
            logger.error(f"Error checking admin rights: {e}")
            return False


class APIKeyBearer(HTTPBearer):
    """
    ИСПРАВЛЕНО: API Key аутентификация с упрощенной валидацией.

    КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ:
    ✅ Исправлено поле APIKey.key вместо APIKey.api_key
    ✅ Упрощена логика валидации
    ✅ Static методы где возможно
    ✅ Убран недостижимый код
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("description", "API Key for service authentication")
        kwargs.setdefault("bearerFormat", "API-Key")
        super().__init__(**kwargs)

    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        """Извлечение и валидация API ключа."""
        credentials = await super().__call__(request)

        if not credentials:
            return None

        api_key = credentials.credentials

        # ИСПРАВЛЕНО: Упрощенная валидация без database
        if not self._validate_api_key_format(api_key):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid API key format",
                headers={"WWW-Authenticate": "Bearer"}
            )

        return credentials

    @staticmethod  # ИСПРАВЛЕНО: Static метод
    def _validate_api_key_format(api_key: str) -> bool:
        """
        ИСПРАВЛЕНО: Базовая валидация формата API ключа.

        Returns:
            bool: True если формат валидный
        """
        # Базовые проверки формата
        if not api_key or not isinstance(api_key, str):
            return False

        if len(api_key) < 32:
            logger.warning(f"API key too short: {len(api_key)}")
            return False

        # Проверяем что ключ содержит только допустимые символы
        allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
        if not all(c in allowed_chars for c in api_key):
            logger.warning("API key contains invalid characters")
            return False

        return True


class DatabaseAPIKeyValidator:
    """
    НОВЫЙ КЛАСС: Отдельный валидатор API ключей с database access.
    """

    @staticmethod
    async def validate_api_key_in_database(api_key: str) -> bool:
        """
        ИСПРАВЛЕНО: Валидация API ключа в базе данных с правильным полем.

        Args:
            api_key: API ключ для валидации

        Returns:
            bool: True если ключ валидный
        """
        try:
            from app.core.db import get_db
            from app.models.models import APIKey

            # Получаем сессию БД
            async for db_session in get_db():
                try:
                    result = await db_session.execute(
                        select(APIKey).where(
                            APIKey.key == api_key,
                            APIKey.is_active == True
                        )
                    )
                    api_key_record = result.scalar_one_or_none()

                    if api_key_record:
                        logger.debug(f"Valid API key found for user: {api_key_record.user_id}")
                        return True
                    else:
                        logger.warning(f"API key not found or inactive: {api_key[:8]}...")
                        return False

                except Exception as db_error:
                    logger.error(f"Database error validating API key: {db_error}")
                    return False
            return None

        except Exception as e:
            logger.error(f"Error validating API key: {e}")
            return False

    @staticmethod
    async def get_api_key_info(api_key: str) -> Optional[dict]:
        """
        Получение информации об API ключе.

        Args:
            api_key: API ключ

        Returns:
            Optional[dict]: Информация о ключе или None
        """
        try:
            from app.core.db import get_db
            from app.models.models import APIKey, User

            async for db_session in get_db():
                try:
                    # Загружаем API ключ с пользователем
                    query = (
                        select(APIKey, User)
                        .join(User, APIKey.user_id == User.id)
                        .where(
                            APIKey.key == api_key,
                            APIKey.is_active == True,
                            User.is_active == True
                        )
                    )

                    result = await db_session.execute(query)
                    api_key_data = result.first()

                    if not api_key_data:
                        return None

                    api_key_obj, user_obj = api_key_data

                    return {
                        "api_key_id": api_key_obj.id,
                        "user_id": user_obj.id,
                        "user_email": user_obj.email,
                        "key_name": getattr(api_key_obj, 'name', 'Unknown'),
                        "permissions": getattr(api_key_obj, 'permissions', []),
                        "is_active": api_key_obj.is_active
                    }

                except Exception as db_error:
                    logger.error(f"Database error getting API key info: {db_error}")
                    return None
            return None

        except Exception as e:
            logger.error(f"Error getting API key info: {e}")
            return None


class RoleBasedJWTBearer(JWTBearer):
    """JWT Bearer с проверкой ролей."""

    def __init__(self, allowed_roles: List[str], **kwargs):
        super().__init__(**kwargs)
        self.allowed_roles = allowed_roles

    def _verify_jwt_token(self, token: str) -> bool:
        """Верификация с проверкой ролей."""
        if not super()._verify_jwt_token(token):
            return False

        try:
            payload = auth_handler.decode_token(token)
            user_role = payload.get("role", "user")

            if user_role not in self.allowed_roles:
                logger.warning(
                    f"User with role '{user_role}' attempted access to endpoint "
                    f"requiring roles: {self.allowed_roles}"
                )
                return False

            return True

        except (HTTPException, ValueError, TypeError) as e:
            logger.error(f"Error checking user role: {e}")
            return False


# Глобальные экземпляры
jwt_bearer = JWTBearer()
optional_jwt_bearer = OptionalJWTBearer()
admin_jwt_bearer = AdminJWTBearer()
api_key_bearer = APIKeyBearer()

# Validator для database operations
api_key_validator = DatabaseAPIKeyValidator()


# Utility функции
def extract_token_from_header(authorization_header: str) -> Optional[str]:
    """Извлечение токена из заголовка Authorization."""
    if not authorization_header:
        return None

    try:
        scheme, token = get_authorization_scheme_param(authorization_header)

        if scheme.lower() != "bearer":
            return None

        return token

    except (ValueError, AttributeError):
        logger.warning(f"Invalid authorization header format: {authorization_header}")
        return None


def create_custom_jwt_bearer(
    require_admin: bool = False,
    require_verified: bool = False,
    allowed_roles: Optional[List[str]] = None
) -> JWTBearer:
    """Фабрика для создания кастомных JWT Bearer схем."""
    class CustomJWTBearer(JWTBearer):
        def _verify_jwt_token(self, token: str) -> bool:
            if not super()._verify_jwt_token(token):
                return False

            try:
                payload = auth_handler.decode_token(token)

                if require_admin:
                    is_admin = payload.get("is_admin", False)
                    if not is_admin:
                        logger.warning(f"Admin access required, user: {payload.get('sub')}")
                        return False

                if require_verified:
                    is_verified = payload.get("is_verified", False)
                    if not is_verified:
                        logger.warning(f"Verified user required, user: {payload.get('sub')}")
                        return False

                if allowed_roles:
                    user_role = payload.get("role", "user")
                    if user_role not in allowed_roles:
                        logger.warning(
                            f"Role '{user_role}' not in allowed roles: {allowed_roles}, "
                            f"user: {payload.get('sub')}"
                        )
                        return False

                return True

            except (HTTPException, ValueError, TypeError) as e:
                logger.error(f"Custom JWT verification error: {e}")
                return False

    return CustomJWTBearer()


# Предустановленные схемы
verified_jwt_bearer = create_custom_jwt_bearer(require_verified=True)
moderator_jwt_bearer = RoleBasedJWTBearer(allowed_roles=["admin", "moderator"])
staff_jwt_bearer = RoleBasedJWTBearer(allowed_roles=["admin", "moderator", "staff"])


# DEPENDENCY FUNCTIONS
async def get_api_key_from_request(request: Request) -> Optional[str]:
    """
    ИСПРАВЛЕНО: Извлечение API ключа из request без неиспользуемых параметров.

    Args:
        request: HTTP request

    Returns:
        Optional[str]: API ключ или None
    """
    # Получаем API ключ из разных возможных заголовков
    api_key = (
        request.headers.get("X-API-Key") or
        request.headers.get("X-Api-Key") or
        request.headers.get("API-Key") or
        request.headers.get("Authorization", "").replace("Bearer ", "").replace("ApiKey ", "")
    )

    if api_key and len(api_key) >= 32:  # Basic format check
        return api_key

    return None


async def validate_api_key_dependency(request: Request) -> Optional[dict]:
    """
    Dependency для валидации API ключа.

    Returns:
        Optional[dict]: API key info или None
    """
    api_key = await get_api_key_from_request(request)

    if not api_key:
        return None

    # Сначала проверяем формат
    if not APIKeyBearer._validate_api_key_format(api_key):
        return None

    # Потом проверяем в базе данных
    if await api_key_validator.validate_api_key_in_database(api_key):
        return await api_key_validator.get_api_key_info(api_key)

    return None


def require_valid_api_key():
    """
    ИСПРАВЛЕНО: Dependency который требует валидный API ключ.

    Returns:
        Dependency function
    """
    async def dependency(
        api_key_info: Optional[dict] = Depends(validate_api_key_dependency)
    ) -> dict:
        if not api_key_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Valid API key required",
                headers={"WWW-Authenticate": "Bearer"}
            )
        return api_key_info

    return dependency
