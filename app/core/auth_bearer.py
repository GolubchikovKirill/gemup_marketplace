"""
JWT Bearer аутентификация для FastAPI.

Кастомная реализация HTTPBearer схемы для извлечения и валидации
JWT токенов из заголовков Authorization. Интегрируется с auth.py.
"""

import logging
from typing import Optional, List

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security.utils import get_authorization_scheme_param
from jose.exceptions import JWTError

from app.core.auth import auth_handler

logger = logging.getLogger(__name__)


class JWTBearer(HTTPBearer):
    """
    Кастомная схема аутентификации JWT Bearer.

    Расширяет стандартную HTTPBearer схему FastAPI дополнительной
    валидацией JWT токенов и улучшенной обработкой ошибок.
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
        Инициализация JWT Bearer схемы.

        Args:
            bearer_format: Формат токена (обычно "JWT")
            scheme_name: Название схемы для OpenAPI
            description: Описание для документации
            auto_error: Автоматически генерировать ошибки при отсутствии токена
            verify_token: Выполнять валидацию токена
        """
        super().__init__(
            bearerFormat=bearer_format or "JWT",  # FastAPI ожидает bearerFormat
            scheme_name=scheme_name or "JWTBearer",
            description=description or "JWT Bearer token authentication",
            auto_error=auto_error
        )

        self.verify_token = verify_token
        self.model.description = description or "Enter JWT Bearer token"

    async def __call__(self, request: Request) -> Optional[str]:
        """
        Извлечение и валидация JWT токена из запроса.

        Args:
            request: HTTP запрос FastAPI

        Returns:
            Optional[str]: Валидный JWT токен или None

        Raises:
            HTTPException: При некорректном токене или ошибке валидации
        """
        # Извлекаем токен из заголовков
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

        return token

    @staticmethod  # ИСПРАВЛЕНО: сделан статическим
    def _is_valid_scheme(scheme: str) -> bool:
        """
        Проверка схемы аутентификации.

        Args:
            scheme: Схема аутентификации из заголовка

        Returns:
            bool: True если схема валидна
        """
        return scheme.lower() == "bearer"

    @staticmethod  # ИСПРАВЛЕНО: сделан статическим
    def _is_valid_token_format(token: str) -> bool:
        """
        Базовая проверка формата JWT токена.

        Args:
            token: JWT токен

        Returns:
            bool: True если формат валиден
        """
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
        """
        Верификация JWT токена через auth_handler.

        Args:
            token: JWT токен для проверки

        Returns:
            bool: True если токен валиден
        """
        try:
            # Используем auth_handler для декодирования токена
            payload = auth_handler.decode_token(token)

            # Базовые проверки payload
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
            # auth_handler.decode_token генерирует HTTPException при ошибках
            logger.debug(f"Token verification failed: {e.detail}")
            return False
        except (ValueError, TypeError) as e:
            logger.error(f"Token validation error: {e}")
            return False
        except JWTError as e:
            logger.error(f"JWT processing error: {e}")
            return False

    def _log_successful_authentication(self, request: Request, token: str) -> None:
        """
        Логирование успешной аутентификации.

        Args:
            request: HTTP запрос
            token: Валидный токен
        """
        try:
            # Извлекаем информацию о пользователе из токена (без повторной валидации)
            payload = auth_handler.decode_token(token)
            user_id = payload.get("sub", "unknown")

            # Получаем информацию о запросе
            client_ip = self._get_client_ip(request)
            user_agent = request.headers.get("user-agent", "unknown")

            logger.debug(
                f"JWT authentication successful - "
                f"User: {user_id} - "
                f"IP: {client_ip} - "
                f"Path: {request.url.path} - "
                f"UserAgent: {user_agent[:50]}..."
            )

        except (HTTPException, ValueError, TypeError) as e:
            # Не прерываем процесс аутентификации из-за ошибок логирования
            logger.error(f"Error logging authentication: {e}")

    @staticmethod  # ИСПРАВЛЕНО: сделан статическим
    def _get_client_ip(request: Request) -> str:
        """
        Получение IP адреса клиента.

        Args:
            request: HTTP запрос

        Returns:
            str: IP адрес клиента
        """
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
    """
    Опциональная JWT Bearer аутентификация.

    Не генерирует ошибки при отсутствии токена,
    используется для endpoints доступных как авторизованным,
    так и неавторизованным пользователям.
    """

    def __init__(self, **kwargs):
        """Инициализация с auto_error=False."""
        kwargs.setdefault("auto_error", False)
        super().__init__(**kwargs)

    async def __call__(self, request: Request) -> Optional[str]:
        """
        Опциональное извлечение токена.

        Args:
            request: HTTP запрос

        Returns:
            Optional[str]: Токен если присутствует и валиден, None в противном случае
        """
        try:
            return await super().__call__(request)
        except HTTPException:
            # Игнорируем ошибки аутентификации для опционального токена
            return None


class AdminJWTBearer(JWTBearer):
    """
    JWT Bearer аутентификация с проверкой административных прав.

    Дополнительно проверяет наличие административных прав
    в токене пользователя.
    """

    def _verify_jwt_token(self, token: str) -> bool:
        """
        Верификация токена с проверкой административных прав.

        Args:
            token: JWT токен

        Returns:
            bool: True если токен валиден и пользователь - администратор
        """
        # Базовая проверка токена
        if not super()._verify_jwt_token(token):
            return False

        try:
            # Проверяем административные права
            payload = auth_handler.decode_token(token)

            # Проверяем флаг администратора в токене
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
    API Key аутентификация через Bearer токен.

    Альтернативная схема аутентификации для API ключей,
    используется для интеграций и внешних сервисов.
    """

    def __init__(self, **kwargs):
        """Инициализация с кастомным описанием."""
        kwargs.setdefault("description", "API Key for service authentication")
        kwargs.setdefault("bearerFormat", "API-Key")  # FastAPI параметр остается как есть
        super().__init__(**kwargs)

    async def __call__(self, request: Request) -> Optional[str]:
        """
        Извлечение и валидация API ключа.

        Args:
            request: HTTP запрос

        Returns:
            Optional[str]: Валидный API ключ

        Raises:
            HTTPException: При некорректном API ключе
        """
        credentials = await super().__call__(request)

        if not credentials:
            return None

        api_key = credentials.credentials

        # Валидация API ключа
        if not self._validate_api_key(api_key):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"}
            )

        return api_key

    @staticmethod  # ИСПРАВЛЕНО: сделан статическим
    def _validate_api_key(api_key: str) -> bool:
        """
        Валидация API ключа.

        Args:
            api_key: API ключ для проверки

        Returns:
            bool: True если ключ валиден
        """
        # Здесь должна быть логика проверки API ключа
        # Например, проверка в базе данных или против списка валидных ключей

        # Базовые проверки формата
        if not api_key or len(api_key) < 32:
            return False

        # TODO: Реализовать реальную валидацию API ключей
        # valid_keys = get_valid_api_keys()
        # return api_key in valid_keys

        logger.warning("API key validation not implemented")
        return False


class RoleBasedJWTBearer(JWTBearer):
    """
    JWT Bearer аутентификация с проверкой ролей.

    Позволяет ограничить доступ к endpoint только пользователям
    с определенными ролями.
    """

    def __init__(self, allowed_roles: List[str], **kwargs):
        """
        Инициализация с указанием разрешенных ролей.

        Args:
            allowed_roles: Список разрешенных ролей
            **kwargs: Дополнительные параметры для базового класса
        """
        super().__init__(**kwargs)
        self.allowed_roles = allowed_roles

    def _verify_jwt_token(self, token: str) -> bool:
        """
        Верификация токена с проверкой ролей.

        Args:
            token: JWT токен

        Returns:
            bool: True если токен валиден и роль разрешена
        """
        # Базовая проверка токена
        if not super()._verify_jwt_token(token):
            return False

        try:
            # Проверяем роль пользователя
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


# Глобальные экземпляры схем аутентификации
jwt_bearer = JWTBearer()
optional_jwt_bearer = OptionalJWTBearer()
admin_jwt_bearer = AdminJWTBearer()
api_key_bearer = APIKeyBearer()


# Utility функции
def extract_token_from_header(authorization_header: str) -> Optional[str]:
    """
    Извлечение токена из заголовка Authorization.

    Args:
        authorization_header: Значение заголовка Authorization

    Returns:
        Optional[str]: Извлеченный токен или None
    """
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
    """
    Фабрика для создания кастомных JWT Bearer схем.

    Args:
        require_admin: Требовать административные права
        require_verified: Требовать верифицированного пользователя
        allowed_roles: Список разрешенных ролей

    Returns:
        JWTBearer: Настроенная схема аутентификации
    """
    class CustomJWTBearer(JWTBearer):
        def _verify_jwt_token(self, token: str) -> bool:
            if not super()._verify_jwt_token(token):
                return False

            try:
                payload = auth_handler.decode_token(token)

                # Проверка административных прав
                if require_admin:
                    is_admin = payload.get("is_admin", False)
                    if not is_admin:
                        logger.warning(f"Admin access required, user: {payload.get('sub')}")
                        return False

                # Проверка верификации
                if require_verified:
                    is_verified = payload.get("is_verified", False)
                    if not is_verified:
                        logger.warning(f"Verified user required, user: {payload.get('sub')}")
                        return False

                # Проверка ролей
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


def create_role_based_bearer(allowed_roles: List[str]) -> RoleBasedJWTBearer:
    """
    Создание Bearer схемы с проверкой ролей.

    Args:
        allowed_roles: Список разрешенных ролей

    Returns:
        RoleBasedJWTBearer: Схема с проверкой ролей
    """
    return RoleBasedJWTBearer(allowed_roles=allowed_roles)


# Предустановленные схемы для часто используемых случаев
verified_jwt_bearer = create_custom_jwt_bearer(require_verified=True)
moderator_jwt_bearer = create_role_based_bearer(["admin", "moderator"])
staff_jwt_bearer = create_role_based_bearer(["admin", "moderator", "staff"])
