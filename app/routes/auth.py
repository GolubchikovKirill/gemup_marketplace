"""
Роуты для аутентификации и авторизации.

Обеспечивает API endpoints для регистрации, входа в систему,
выхода и управления токенами доступа.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.dependencies import get_current_user_from_token
from app.models.models import User
from app.schemas.base import MessageResponse
from app.schemas.user import UserCreate, UserResponse, UserLogin
from app.services.auth_service import auth_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse)
async def register(
        user_data: UserCreate,
        db: AsyncSession = Depends(get_db)
):
    """
    Регистрация нового пользователя в системе.

    Args:
        user_data: Данные для регистрации (email, пароль, и т.д.)
        db: Сессия базы данных

    Returns:
        UserResponse: Данные созданного пользователя

    Raises:
        HTTPException: При ошибках валидации или создания
    """
    try:
        user = await auth_service.register_user(user_data, db)
        return user

    except HTTPException:
        raise
    except IntegrityError as e:
        logger.error(f"Database integrity error during registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists"
        )
    except Exception as e:
        logger.error(f"Unexpected error during registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )


@router.post("/login")
async def login(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: AsyncSession = Depends(get_db)
):
    """
    Авторизация пользователя через form-data.

    Совместимо со стандартом OAuth2 и может использоваться
    с автоматической документацией FastAPI.

    Args:
        form_data: Данные формы с username и password
        db: Сессия базы данных

    Returns:
        dict: Токен доступа и информация о пользователе
    """
    try:
        # Аутентификация пользователя
        user = await auth_service.authenticate_user(
            form_data.username, form_data.password, db
        )

        # Создание токена доступа
        access_token = auth_service.create_access_token(user.id)

        # Возврат стандартного ответа
        return auth_service.create_token_response(user, access_token)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again."
        )


@router.post("/login/json")
async def login_json(
        user_data: UserLogin,
        db: AsyncSession = Depends(get_db)
):
    """
    Авторизация пользователя через JSON.

    Альтернативный способ входа для SPA приложений
    и мобильных клиентов.

    Args:
        user_data: JSON данные с email и password
        db: Сессия базы данных

    Returns:
        dict: Токен доступа и информация о пользователе
    """
    try:
        # Аутентификация пользователя
        user = await auth_service.authenticate_user(
            str(user_data.email), user_data.password, db
        )

        # Создание токена доступа
        access_token = auth_service.create_access_token(user.id)

        # Возврат стандартного ответа
        return auth_service.create_token_response(user, access_token)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during JSON login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again."
        )


@router.post("/logout", response_model=MessageResponse)
async def logout(
        current_user: User = Depends(get_current_user_from_token)
):
    """
    Выход пользователя из системы.

    В текущей реализации с JWT токенами выход обрабатывается
    на стороне клиента путем удаления токена.

    Args:
        current_user: Текущий авторизованный пользователь

    Returns:
        MessageResponse: Сообщение об успешном выходе
    """
    try:
        await auth_service.logout_user(current_user)
        return MessageResponse(message="Successfully logged out")

    except Exception as e:
        logger.error(f"Error during logout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
        current_user: User = Depends(get_current_user_from_token)
):
    """
    Получение информации о текущем авторизованном пользователе.

    Args:
        current_user: Текущий пользователь из токена

    Returns:
        UserResponse: Данные пользователя
    """
    try:
        return current_user
    except Exception as e:
        logger.error(f"Error getting user info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information"
        )


@router.post("/refresh")
async def refresh_token(
        current_user: User = Depends(get_current_user_from_token)
):
    """
    Обновление токена доступа.

    Создает новый токен доступа для текущего пользователя
    без необходимости повторного ввода учетных данных.

    Args:
        current_user: Текущий пользователь из токена

    Returns:
        dict: Новый токен доступа
    """
    try:
        # Создание нового токена
        access_token = await auth_service.refresh_user_token(current_user)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": auth_service.access_token_expire_minutes * 60
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
        old_password: str,
        new_password: str,
        current_user: User = Depends(get_current_user_from_token),
        db: AsyncSession = Depends(get_db)
):
    """
    Изменение пароля пользователя.

    Args:
        old_password: Текущий пароль
        new_password: Новый пароль
        current_user: Текущий пользователь
        db: Сессия базы данных

    Returns:
        MessageResponse: Сообщение об успешном изменении
    """
    try:
        success = await auth_service.change_user_password(
            current_user, old_password, new_password, db
        )

        if success:
            return MessageResponse(message="Password changed successfully")
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Password change failed"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


@router.post("/verify-email/{user_id}", response_model=MessageResponse)
async def verify_email(
        user_id: int,
        db: AsyncSession = Depends(get_db)
):
    """
    Подтверждение email пользователя.

    Обычно вызывается по ссылке из письма подтверждения.

    Args:
        user_id: Идентификатор пользователя
        db: Сессия базы данных

    Returns:
        MessageResponse: Сообщение об успешном подтверждении
    """
    try:
        success = await auth_service.verify_user_email(user_id, db)

        if success:
            return MessageResponse(message="Email verified successfully")
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed"
        )
