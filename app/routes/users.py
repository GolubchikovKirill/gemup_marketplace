from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.dependencies import (
    get_current_registered_user,
    get_current_user_or_create_guest
)
from app.crud.user import user_crud
from app.schemas.user import (
    UserResponse,
    UserUpdate,
    UserCreate
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
        current_user=Depends(get_current_user_or_create_guest)
):
    """Получение профиля текущего пользователя"""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_my_profile(
        user_update: UserUpdate,
        current_user=Depends(get_current_registered_user),
        db: AsyncSession = Depends(get_db)
):
    """Обновление профиля пользователя"""

    # Проверяем уникальность email если он изменяется
    if user_update.email and user_update.email != current_user.email:
        existing_user = await user_crud.get_by_email(db, email=user_update.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )

    # Проверяем уникальность username если он изменяется
    if user_update.username and user_update.username != current_user.username:
        existing_user = await user_crud.get_by_username(db, username=user_update.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this username already exists"
            )

    updated_user = await user_crud.update(db, db_obj=current_user, obj_in=user_update)
    return updated_user


@router.get("/balance")
async def get_balance(
        current_user=Depends(get_current_user_or_create_guest)
):
    """Получение баланса пользователя"""
    return {
        "balance": current_user.balance,
        "currency": "USD",
        "user_id": current_user.id,
        "is_guest": current_user.is_guest
    }


@router.post("/convert-guest", response_model=UserResponse)
async def convert_guest_to_registered(
        user_data: UserCreate,
        current_user=Depends(get_current_user_or_create_guest),
        db: AsyncSession = Depends(get_db)
):
    """Конвертация гостевого пользователя в зарегистрированного"""

    if not current_user.is_guest:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already registered"
        )

    # Проверяем уникальность данных
    existing_email = await user_crud.get_by_email(db, email=user_data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

    if user_data.username:
        existing_username = await user_crud.get_by_username(db, username=user_data.username)
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this username already exists"
            )

    # Конвертируем пользователя
    converted_user = await user_crud.convert_guest_to_registered(
        db, guest_user=current_user, user_data=user_data
    )

    return converted_user
