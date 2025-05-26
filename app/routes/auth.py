from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.core.auth import auth_handler
from app.core.dependencies import get_current_user_from_token
from app.crud.user import user_crud
from app.schemas.user import UserCreate, UserResponse, UserLogin
from app.schemas.base import MessageResponse
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse)
async def register(
        user_data: UserCreate,
        db: AsyncSession = Depends(get_db)
):
    """Регистрация нового пользователя"""

    # Проверяем, существует ли пользователь с таким email
    existing_user = await user_crud.get_by_email(db, email=user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

    # Проверяем username
    if user_data.username:
        existing_username = await user_crud.get_by_username(db, username=user_data.username)
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this username already exists"
            )

    # Создаем пользователя
    user = await user_crud.create_registered_user(db, user_in=user_data)
    return user


@router.post("/login")
async def login(
        response: Response,
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: AsyncSession = Depends(get_db)
):
    """Авторизация пользователя"""

    # Аутентифицируем пользователя
    user = await user_crud.authenticate(
        db, email=form_data.username, password=form_data.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    # Создаем токен
    access_token_expires = timedelta(minutes=auth_handler.access_token_expire_minutes)
    access_token = auth_handler.create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )

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


@router.post("/login/json")
async def login_json(
        user_data: UserLogin,
        db: AsyncSession = Depends(get_db)
):
    """Авторизация через JSON"""

    user = await user_crud.authenticate(
        db, email=user_data.email, password=user_data.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    access_token_expires = timedelta(minutes=auth_handler.access_token_expire_minutes)
    access_token = auth_handler.create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )

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


@router.post("/logout", response_model=MessageResponse)
async def logout():
    """Выход из системы"""
    return MessageResponse(message="Successfully logged out")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
        current_user=Depends(get_current_user_from_token)
):
    """Получение информации о текущем пользователе"""
    return current_user
