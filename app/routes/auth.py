import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import auth_handler
from app.core.db import get_db
from app.core.dependencies import get_current_user_from_token
from app.crud.user import user_crud
from app.models.models import User
from app.schemas.base import MessageResponse
from app.schemas.user import UserCreate, UserResponse, UserLogin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


class AuthService:
    """Сервис для аутентификации (следует принципу SRP)"""

    @staticmethod
    async def validate_user_data(user_data: UserCreate, db: AsyncSession) -> None:
        """Валидация данных пользователя"""
        # Проверяем email
        if await user_crud.get_by_email(db, email=str(user_data.email)):  # Преобразование EmailStr
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )

        # Проверяем username если указан
        if user_data.username:
            if await user_crud.get_by_username(db, username=user_data.username):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this username already exists"
                )

    @staticmethod
    async def authenticate_user(email: str, password: str, db: AsyncSession):
        """Аутентификация пользователя"""
        user = await user_crud.authenticate(db, email=email, password=password)

        if not user:
            logger.warning(f"Failed login attempt for email: {email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            logger.warning(f"Inactive user login attempt: {email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )

        return user

    @staticmethod
    def create_access_token(user_id: int) -> str:
        """Создание токена доступа"""
        access_token_expires = timedelta(minutes=auth_handler.access_token_expire_minutes)
        return auth_handler.create_access_token(
            data={"sub": str(user_id)},
            expires_delta=access_token_expires
        )


auth_service = AuthService()


@router.post("/register", response_model=UserResponse)
async def register(
        user_data: UserCreate,
        db: AsyncSession = Depends(get_db)
):
    """Регистрация нового пользователя"""
    try:
        # Валидация данных
        await auth_service.validate_user_data(user_data, db)

        # Создание пользователя
        user = await user_crud.create_registered_user(db, user_in=user_data)
        logger.info(f"New user registered: {user.email}")

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
    """Авторизация пользователя (form-data)"""
    try:
        # Аутентификация
        user = await auth_service.authenticate_user(
            form_data.username, form_data.password, db
        )

        # Создание токена
        access_token = auth_service.create_access_token(user.id)

        logger.info(f"User logged in: {user.email}")

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "is_verified": user.is_verified
            }
        }

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
    """Авторизация через JSON"""
    try:
        # Аутентификация
        user = await auth_service.authenticate_user(
            str(user_data.email), user_data.password, db  # Преобразование EmailStr
        )

        # Создание токена
        access_token = auth_service.create_access_token(user.id)

        logger.info(f"User logged in via JSON: {user.email}")

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "is_verified": user.is_verified
            }
        }

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
    """Выход из системы"""
    try:
        # В JWT токенах logout обычно обрабатывается на клиенте
        # Здесь можно добавить логику для blacklist токенов в будущем
        logger.info(f"User logged out: {current_user.email}")

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
    """Получение информации о текущем пользователе"""
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
    """Обновление токена доступа"""
    try:
        # Создание нового токена
        access_token = auth_service.create_access_token(current_user.id)

        logger.info(f"Token refreshed for user: {current_user.email}")

        return {
            "access_token": access_token,
            "token_type": "bearer"
        }

    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )
