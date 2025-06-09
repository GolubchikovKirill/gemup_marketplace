"""
Роуты для аутентификации и авторизации - исправлено для MVP.

Обеспечивает API endpoints для регистрации, входа в систему,
выхода и управления токенами доступа.
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.dependencies import get_current_user_or_create_guest
from app.models.models import User
from app.schemas.base import MessageResponse
from app.schemas.user import (
    UserCreate, UserResponse, UserLogin, TokenResponse,
    PasswordChangeRequest, PasswordResetRequest, PasswordResetConfirm,
    GuestUserCreate, GuestToRegisteredRequest
)
from app.services.auth_service import auth_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Регистрация нового пользователя в системе."""
    try:
        user = await auth_service.register_user(user_data, db)
        logger.info(f"User registered successfully: {user.email}")
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


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Авторизация пользователя через form-data."""
    try:
        user = await auth_service.authenticate_user(
            form_data.username, form_data.password, db
        )

        access_token = auth_service.create_access_token(user.id)
        refreshed_token = auth_service.create_refresh_token(user.id)

        token_response = auth_service.create_token_response(user, access_token, refreshed_token)

        user_identifier = user.email or f"user_id:{user.id}"
        logger.info(f"User logged in successfully: {user_identifier}")
        return TokenResponse(**token_response)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again."
        )


@router.post("/login/json", response_model=TokenResponse)
async def login_json(
    user_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Авторизация пользователя через JSON."""
    try:
        user = await auth_service.authenticate_user(
            str(user_data.email), user_data.password, db
        )

        access_token = auth_service.create_access_token(user.id)
        refreshed_token = auth_service.create_refresh_token(user.id)

        token_response = auth_service.create_token_response(user, access_token, refreshed_token)

        logger.info(f"User logged in via JSON: {user.email}")
        return TokenResponse(**token_response)

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
    current_user: User = Depends(get_current_user_or_create_guest)
):
    """Выход пользователя из системы."""
    try:
        success = auth_service.logout_user(current_user)

        if success:
            logger.info(f"User logged out: {current_user.email or current_user.guest_session_id}")
            return MessageResponse(
                message="Successfully logged out",
                success=True,
                details={"user_id": current_user.id}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Logout failed"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user_or_create_guest)
):
    """Получение информации о текущем авторизованном пользователе."""
    try:
        logger.debug(f"User info requested: {current_user.email or current_user.guest_session_id}")
        return current_user
    except Exception as e:
        logger.error(f"Error getting user info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information"
        )


@router.post("/refresh", response_model=Dict[str, Any])
async def refresh_token(
    current_user: User = Depends(get_current_user_or_create_guest)
):
    """Обновление токена доступа."""
    try:
        access_token = await auth_service.refresh_user_token(current_user)

        logger.info(f"Token refreshed for user: {current_user.email or current_user.guest_session_id}")
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
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user_or_create_guest),
    db: AsyncSession = Depends(get_db)
):
    """Изменение пароля пользователя."""
    try:
        if current_user.is_guest:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Guest users cannot change password"
            )

        success = await auth_service.change_user_password(
            current_user, password_data.old_password, password_data.new_password, db
        )

        if success:
            logger.info(f"Password changed for user: {current_user.email}")
            return MessageResponse(
                message="Password changed successfully",
                success=True,
                details={"user_id": current_user.id}
            )
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


@router.post("/password-reset/request", response_model=MessageResponse)
async def request_password_reset(
    reset_request: PasswordResetRequest,
    db: AsyncSession = Depends(get_db)
):
    """Запрос на сброс пароля."""
    try:
        reset_token = await auth_service.generate_password_reset_token(
            str(reset_request.email), db
        )

        if reset_token:
            logger.info(f"Password reset requested for: {reset_request.email}")

        return MessageResponse(
            message="If the email exists, a password reset link has been sent",
            success=True
        )

    except Exception as e:
        logger.error(f"Error requesting password reset: {e}")
        return MessageResponse(
            message="If the email exists, a password reset link has been sent",
            success=True
        )


@router.post("/password-reset/confirm", response_model=MessageResponse)
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db)
):
    """Подтверждение сброса пароля."""
    try:
        success = await auth_service.reset_password_with_token(
            reset_data.token, reset_data.new_password, db
        )

        if success:
            logger.info("Password reset completed successfully")
            return MessageResponse(
                message="Password reset successfully",
                success=True
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password reset failed"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming password reset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )


@router.post("/verify-email/{user_id}", response_model=MessageResponse)
async def verify_email(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Подтверждение email пользователя."""
    try:
        success = await auth_service.verify_user_email(user_id, db)

        if success:
            logger.info(f"Email verified for user_id: {user_id}")
            return MessageResponse(
                message="Email verified successfully",
                success=True,
                details={"user_id": user_id}
            )
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


@router.post("/guest", response_model=UserResponse)
async def create_guest_user(
    guest_data: GuestUserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Создание гостевого пользователя - КЛЮЧЕВОЕ для MVP."""
    try:
        guest_user = await auth_service.create_guest_user(db, guest_data.session_id)

        logger.info(f"Guest user created: {guest_data.session_id}")
        return guest_user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating guest user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create guest user"
        )


@router.post("/convert-guest", response_model=UserResponse)
async def convert_guest_to_registered(
    user_data: GuestToRegisteredRequest,
    current_user: User = Depends(get_current_user_or_create_guest),
    db: AsyncSession = Depends(get_db)
):
    """Конвертация гостевого пользователя в зарегистрированного - КЛЮЧЕВОЕ для MVP."""
    try:
        if not current_user.is_guest:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already registered"
            )

        # Создаем UserCreate из GuestToRegisteredRequest
        user_create_data = UserCreate(
            email=user_data.email,
            username=user_data.username,
            password=user_data.password,
            first_name=user_data.first_name,
            last_name=user_data.last_name
        )

        converted_user = await auth_service.convert_guest_to_registered(
            current_user, user_create_data, db
        )

        logger.info(f"Guest user converted: {converted_user.email}")
        return converted_user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error converting guest user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to convert guest user"
        )
