"""
Роуты для управления пользователями - исправлено для MVP.

Обеспечивает API endpoints для управления профилями пользователей,
включая просмотр и обновление данных, управление балансом
и конвертацию гостевых аккаунтов в зарегистрированные.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.dependencies import (
    get_current_registered_user,
    get_current_user_or_create_guest
)
from app.crud.user import user_crud
from app.schemas.base import MessageResponse
from app.schemas.user import (
    UserResponse,
    UserUpdate,
    UserBalanceResponse,
    UserStatsResponse,
    UserListResponse,
    BalanceTopupRequest,
    BalanceTopupResponse,
    BalanceHistoryResponse
)
from app.services.payment_service import payment_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user=Depends(get_current_user_or_create_guest)
):
    """Получение профиля текущего пользователя."""
    try:
        logger.info(f"Profile requested for user {current_user.id} (guest: {current_user.is_guest})")
        return current_user
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get profile"
        )


@router.put("/me", response_model=UserResponse)
async def update_my_profile(
    user_update: UserUpdate,
    current_user=Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db)
):
    """Обновление профиля пользователя."""
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


@router.get("/balance", response_model=UserBalanceResponse)
async def get_balance(
    current_user=Depends(get_current_user_or_create_guest)
):
    """Получение баланса пользователя - КЛЮЧЕВОЕ для MVP."""
    try:
        balance_info = UserBalanceResponse(
            balance=str(current_user.balance),
            currency="USD",
            user_id=current_user.id,
            is_guest=current_user.is_guest,
            formatted_balance=f"${current_user.balance:.2f}",
            last_updated=current_user.updated_at.isoformat() if current_user.updated_at else None,
            pending_topups="0.00000000",  # TODO: Получать из БД
            total_deposited="0.00000000"  # TODO: Получать из БД
        )

        logger.debug(f"Balance requested for user {current_user.id}: ${current_user.balance}")
        return balance_info

    except Exception as e:
        logger.error(f"Error getting user balance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get balance"
        )


@router.post("/balance/topup", response_model=BalanceTopupResponse)
async def topup_balance(
    topup_request: BalanceTopupRequest,
    current_user=Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db)
):
    """Пополнение баланса - КЛЮЧЕВОЕ для MVP."""
    try:
        # Создаем платеж для пополнения баланса
        from app.schemas.payment import PaymentCreateRequest

        payment_request = PaymentCreateRequest(
            amount=topup_request.amount,
            currency=topup_request.currency,
            payment_method=topup_request.payment_method,
            description=f"Balance topup for user {current_user.id}"
        )

        payment_result = await payment_service.create_payment(
            db=db,
            user=current_user,
            payment_request=payment_request
        )

        # Создаем ответ пополнения
        topup_response = BalanceTopupResponse(
            topup_id=int(payment_result.transaction_id.split('-')[-1], 16) % 1000000,  # Простое преобразование
            amount=str(topup_request.amount),
            currency=topup_request.currency,
            payment_method=topup_request.payment_method,
            payment_url=payment_result.payment_url,
            status="pending",
            created_at=payment_result.created_at.isoformat(),
            expires_at=payment_result.expires_at.isoformat() if payment_result.expires_at else None
        )

        logger.info(f"Balance topup created for user {current_user.id}: {topup_request.amount}")
        return topup_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating balance topup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create balance topup"
        )


@router.get("/balance/history", response_model=BalanceHistoryResponse)
async def get_balance_history(
    current_user=Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0, description="Пропустить записей"),
    limit: int = Query(20, ge=1, le=100, description="Максимум записей")
):
    """Получение истории баланса - для интерфейса пополнения."""
    try:
        # Получаем транзакции пользователя
        transactions = await payment_service.get_user_transactions(
            db,
            user_id=current_user.id,
            skip=skip,
            limit=limit
        )

        # Формируем ответ
        history_response = BalanceHistoryResponse(
            transactions=transactions.get("transactions", []),
            total=transactions.get("total", 0),
            page=(skip // limit) + 1,
            per_page=limit,
            total_deposited="0.00000000",  # TODO: Рассчитывать из транзакций
            total_spent="0.00000000",     # TODO: Рассчитывать из транзакций
            current_balance=str(current_user.balance)
        )

        return history_response

    except Exception as e:
        logger.error(f"Error getting balance history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get balance history"
        )


@router.get("/stats", response_model=UserStatsResponse)
async def get_user_stats(
    current_user=Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365, description="Период статистики в днях")
):
    """Получение статистики пользователя."""
    try:
        # Получаем статистику заказов
        order_stats = await user_crud.get_user_order_stats(db, user_id=current_user.id, days=days)

        # Получаем статистику прокси
        proxy_stats = await user_crud.get_user_proxy_stats(db, user_id=current_user.id, days=days)

        # Рассчитываем дополнительные метрики
        days_since_registration = (
            datetime.now(timezone.utc) - current_user.created_at
        ).days if current_user.created_at else 0

        stats = UserStatsResponse(
            total_orders=order_stats.get("total_orders", 0),
            total_spent=str(order_stats.get("total_amount", "0.00000000")),
            active_proxies=proxy_stats.get("active_count", 0),
            last_order_date=order_stats.get("last_order_date"),
            registration_date=current_user.created_at.isoformat() if current_user.created_at else None,
            days_since_registration=days_since_registration,
            average_order_amount=str(order_stats.get("average_amount", "0.00000000")),
            total_proxies_purchased=proxy_stats.get("total_purchased", 0),
            period_days=days,
            currency="USD"
        )

        logger.info(f"Stats retrieved for user {current_user.id}")
        return stats

    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user statistics"
        )


@router.delete("/me", response_model=MessageResponse)
async def delete_my_account(
    current_user=Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db)
):
    """Удаление аккаунта пользователя."""
    try:
        # Деактивируем пользователя
        await user_crud.deactivate_user(db, user_id=current_user.id)

        # Деактивируем все активные прокси
        await user_crud.deactivate_user_proxies(db, user_id=current_user.id)

        logger.info(f"User account deactivated: {current_user.id}")

        return MessageResponse(
            message="Account deactivated successfully",
            success=True,
            details={
                "user_id": current_user.id,
                "deactivated_at": datetime.now(timezone.utc).isoformat()
            }
        )

    except Exception as e:
        logger.error(f"Error deactivating user account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate account"
        )


@router.get("/search", response_model=UserListResponse)
async def search_users(
    query: str = Query(..., min_length=3, description="Поисковый запрос"),
    skip: int = Query(0, ge=0, description="Пропустить записей"),
    limit: int = Query(20, ge=1, le=100, description="Максимум записей"),
    current_user=Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db)
):
    """Поиск пользователей (для администраторов)."""
    try:
        # Проверяем права администратора
        if not getattr(current_user, 'is_admin', False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

        users = await user_crud.search_users(db, query=query, skip=skip, limit=limit)

        # Добавляем простой подсчет результатов
        try:
            total = await user_crud.count_search_results(db, query=query)
        except AttributeError:
            # Если метод не реализован, используем длину результата
            total = len(users)

        return UserListResponse(
            users=users,
            total=total,
            page=(skip // limit) + 1,
            per_page=limit,
            pages=(total + limit - 1) // limit if total > 0 else 0
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search users"
        )


@router.get("/activity", response_model=Dict[str, Any])
async def get_user_activity(
    current_user=Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db),
    days: int = Query(7, ge=1, le=90, description="Период активности в днях")
):
    """Получение активности пользователя."""
    try:
        activity = await user_crud.get_user_activity(
            db, user_id=current_user.id, days=days
        )

        return {
            "user_id": current_user.id,
            "period_days": days,
            "activity": activity,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting user activity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user activity"
        )


@router.post("/export-data", response_model=Dict[str, Any])
async def export_user_data(
    current_user=Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db),
    include_orders: bool = Query(True, description="Включать заказы"),
    include_transactions: bool = Query(True, description="Включать транзакции"),
    include_proxies: bool = Query(True, description="Включать прокси")
):
    """Экспорт данных пользователя (GDPR compliance)."""
    try:
        export_data = await user_crud.export_user_data(
            db,
            user_id=current_user.id,
            include_orders=include_orders,
            include_transactions=include_transactions,
            include_proxies=include_proxies
        )

        logger.info(f"Data export requested for user {current_user.id}")

        return {
            "user_id": current_user.id,
            "export_date": datetime.now(timezone.utc).isoformat(),
            "data": export_data,
            "format": "json"
        }

    except Exception as e:
        logger.error(f"Error exporting user data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export user data"
        )
