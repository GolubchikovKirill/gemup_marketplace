"""
Роуты для управления пользователями.

Обеспечивает API endpoints для управления профилями пользователей,
включая просмотр и обновление данных, управление балансом
и конвертацию гостевых аккаунтов в зарегистрированные.
"""

import logging
from datetime import datetime

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
    UserCreate,
    UserBalanceResponse,
    UserStatsResponse
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me",
            response_model=UserResponse,
            summary="Мой профиль",
            description="Получение профиля текущего пользователя (зарегистрированного или гостевого)")
async def get_my_profile(
        current_user=Depends(get_current_user_or_create_guest)
):
    """
    Получение профиля текущего пользователя.

    Возвращает полную информацию о профиле текущего пользователя,
    включая персональные данные, баланс и статистику аккаунта.

    - **Поддержка**: Зарегистрированные и гостевые пользователи
    - **Автосоздание**: Гостевой аккаунт создается автоматически при первом запросе

    **Информация включает:**
    - Основные данные (ID, email, username, имя)
    - Баланс и валюту
    - Статус аккаунта (активен, верифицирован, гость)
    - Временные метки (регистрация, последний вход)

    **Для гостевых пользователей:**
    - Ограниченная функциональность
    - Временный ID сессии
    - Срок действия сессии
    """
    try:
        logger.info(f"Profile requested for user {current_user.id} (guest: {current_user.is_guest})")
        return current_user
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get profile"
        )


@router.put("/me",
            response_model=UserResponse,
            summary="Обновить профиль",
            description="Обновление данных профиля зарегистрированного пользователя")
async def update_my_profile(
        user_update: UserUpdate,
        current_user=Depends(get_current_registered_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Обновление профиля пользователя.

    Позволяет зарегистрированным пользователям обновлять свои
    персональные данные с проверкой уникальности.

    - **Требования**: Зарегистрированный пользователь
    - **Проверки**: Уникальность email и username
    - **Валидация**: Формат email, сложность пароля

    **Обновляемые поля:**
    - Email (с проверкой уникальности)
    - Username (с проверкой уникальности)
    - Имя и фамилия
    - Пароль (с хешированием)

    **Бизнес-правила:**
    - Email должен быть уникальным в системе
    - Username должен быть уникальным в системе
    - Пароль должен соответствовать требованиям безопасности

    **Ошибки:**
    - 400: Нарушение уникальности или валидации
    - 403: Недостаточно прав (только для гостей)
    """
    try:
        # Проверяем уникальность email если он изменяется
        if user_update.email and str(user_update.email) != current_user.email:
            existing_user = await user_crud.get_by_email(db, email=str(user_update.email))
            if existing_user:
                logger.warning(f"Attempt to use existing email: {user_update.email}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this email already exists"
                )

        # Проверяем уникальность username если он изменяется
        if user_update.username and user_update.username != current_user.username:
            existing_user = await user_crud.get_by_username(db, username=user_update.username)
            if existing_user:
                logger.warning(f"Attempt to use existing username: {user_update.username}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this username already exists"
                )

        # Обновляем пользователя
        updated_user = await user_crud.update(db, db_obj=current_user, obj_in=user_update)

        logger.info(f"Profile updated for user {current_user.id}")
        return updated_user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )


@router.get("/balance",
            response_model=UserBalanceResponse,
            summary="Баланс пользователя",
            description="Получение текущего баланса пользователя")
async def get_balance(
        current_user=Depends(get_current_user_or_create_guest)
):
    """
    Получение баланса пользователя.

    Возвращает текущий баланс пользователя и связанную информацию.
    Поддерживает как зарегистрированных, так и гостевых пользователей.

    - **Поддержка**: Зарегистрированные и гостевые пользователи
    - **Валюта**: USD (может быть расширено в будущем)

    **Информация включает:**
    - Текущий баланс с высокой точностью
    - Валюта счета
    - Тип пользователя (зарегистрированный/гость)
    - ID пользователя для связи с транзакциями

    **Для гостевых пользователей:**
    - Баланс всегда 0.00
    - Пополнение недоступно
    - Покупки только после регистрации
    """
    try:
        balance_info = {
            "balance": str(current_user.balance),
            "currency": "USD",
            "user_id": current_user.id,
            "is_guest": current_user.is_guest,
            "formatted_balance": f"${current_user.balance:.2f}"
        }

        logger.debug(f"Balance requested for user {current_user.id}: ${current_user.balance}")
        return balance_info

    except Exception as e:
        logger.error(f"Error getting user balance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get balance"
        )


@router.post("/convert-guest",
             response_model=UserResponse,
             summary="Конвертация гостевого аккаунта",
             description="Преобразование гостевого пользователя в зарегистрированного")
async def convert_guest_to_registered(
        user_data: UserCreate,
        current_user=Depends(get_current_user_or_create_guest),
        db: AsyncSession = Depends(get_db)
):
    """
    Конвертация гостевого пользователя в зарегистрированного.

    Преобразует временную гостевую сессию в полноценный зарегистрированный
    аккаунт с сохранением баланса и истории покупок.

    - **Требования**: Действующая гостевая сессия
    - **Сохранение данных**: Баланс, корзина, история
    - **Валидация**: Все данные нового пользователя

    **Процесс конвертации:**
    1. Проверка уникальности email и username
    2. Валидация данных регистрации
    3. Преобразование аккаунта
    4. Сохранение всех связанных данных
    5. Активация полной функциональности

    **Преимущества после конвертации:**
    - Возможность пополнения баланса
    - Полная история заказов
    - Управление профилем
    - Безопасность аккаунта

    **Ошибки:**
    - 400: Пользователь уже зарегистрирован или данные не уникальны
    - 422: Ошибки валидации данных
    """
    try:
        # Проверяем что пользователь действительно гость
        if not current_user.is_guest:
            logger.warning(f"Non-guest user {current_user.id} attempted guest conversion")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already registered"
            )

        # Проверяем уникальность email
        existing_email = await user_crud.get_by_email(db, email=str(user_data.email))
        if existing_email:
            logger.warning(f"Guest conversion failed - email exists: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )

        # Проверяем уникальность username если указан
        if user_data.username:
            existing_username = await user_crud.get_by_username(db, username=user_data.username)
            if existing_username:
                logger.warning(f"Guest conversion failed - username exists: {user_data.username}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this username already exists"
                )

        # Конвертируем пользователя
        converted_user = await user_crud.convert_guest_to_registered(
            db, guest_user=current_user, user_data=user_data
        )

        if not converted_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to convert guest user"
            )

        logger.info(f"Guest user {current_user.id} converted to registered user {converted_user.id}")
        return converted_user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error converting guest user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to convert guest user"
        )


@router.get("/stats",
            response_model=UserStatsResponse,
            summary="Статистика пользователя",
            description="Получение статистики активности пользователя")
async def get_user_stats(
        current_user=Depends(get_current_registered_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Получение статистики пользователя.

    Возвращает агрегированную статистику активности и использования
    сервиса зарегистрированным пользователем.

    - **Требования**: Зарегистрированный пользователь
    - **Период**: За все время использования сервиса

    **Статистика включает:**
    - Общее количество заказов
    - Общая потраченная сумма
    - Количество активных прокси
    - Дата последнего заказа
    - Время с момента регистрации
    - Среднюю стоимость заказа

    **Применение:**
    - Анализ личной активности
    - Планирование бюджета
    - Отслеживание использования сервиса
    """
    try:
        # Получаем статистику заказов
        order_stats = await user_crud.get_user_order_stats(db, user_id=current_user.id)

        # Получаем статистику прокси
        proxy_stats = await user_crud.get_user_proxy_stats(db, user_id=current_user.id)

        # Рассчитываем дополнительные метрики
        days_since_registration = (
                datetime.now() - current_user.created_at
        ).days if current_user.created_at else 0

        stats = {
            "total_orders": order_stats.get("total_orders", 0),
            "total_spent": str(order_stats.get("total_amount", 0)),
            "active_proxies": proxy_stats.get("active_count", 0),
            "last_order_date": order_stats.get("last_order_date"),
            "registration_date": current_user.created_at.isoformat() if current_user.created_at else None,
            "days_since_registration": days_since_registration,
            "average_order_amount": str(order_stats.get("average_amount", 0)),
            "total_proxies_purchased": proxy_stats.get("total_purchased", 0)
        }

        logger.info(f"Stats retrieved for user {current_user.id}")
        return stats

    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user statistics"
        )


@router.delete("/me",
               summary="Удаление аккаунта",
               description="Удаление аккаунта пользователя (помечается как неактивный)")
async def delete_my_account(
        current_user=Depends(get_current_registered_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Удаление аккаунта пользователя.

    Помечает аккаунт пользователя как неактивный вместо физического удаления
    для сохранения целостности данных и возможности восстановления.

    - **Требования**: Зарегистрированный пользователь
    - **Действие**: Деактивация аккаунта (не физическое удаление)
    - **Сохранение**: История заказов и транзакций сохраняется

    **Последствия деактивации:**
    - Невозможность входа в систему
    - Деактивация всех активных прокси
    - Блокировка новых операций
    - Сохранение данных для аудита

    **Восстановление:**
    Возможно через службу поддержки при обращении
    с подтверждением личности.

    **Внимание:**
    Действие необратимо без участия администрации.
    Активные подписки будут отменены без возврата средств.
    """
    try:
        # Деактивируем пользователя
        await user_crud.deactivate_user(db, user_id=current_user.id)

        # Деактивируем все активные прокси
        await user_crud.deactivate_user_proxies(db, user_id=current_user.id)

        logger.info(f"User account deactivated: {current_user.id}")

        return {
            "message": "Account deactivated successfully",
            "user_id": current_user.id,
            "deactivated_at": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error deactivating user account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate account"
        )
