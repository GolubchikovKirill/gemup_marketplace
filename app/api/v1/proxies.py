"""
Роуты для управления купленными прокси - исправлено для MVP.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.dependencies import get_current_registered_user
from app.core.exceptions import BusinessLogicError
from app.models.models import User
from app.schemas.base import MessageResponse
from app.schemas.proxy_purchase import (
    ProxyExtensionRequest, ProxyExtensionResponse,
    ProxyStatsResponse, ProxyGenerationRequest,
    ProxyGenerationResponse, ProxyListResponse
)
from app.services.proxy_service import proxy_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/proxies", tags=["Proxies"])


@router.get("/", response_model=ProxyListResponse)
async def get_my_proxies(
    current_user: User = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db),
    active_only: bool = Query(True, description="Показывать только активные прокси"),
    skip: int = Query(0, ge=0, description="Пропустить записей"),
    limit: int = Query(50, ge=1, le=100, description="Максимум записей")
):
    """Получение списка купленных прокси пользователя - КЛЮЧЕВОЕ для раздела "Мои покупки"."""
    try:
        proxies = await proxy_service.get_user_proxies(
            db,
            user_id=current_user.id,
            active_only=active_only,
            skip=skip,
            limit=limit
        )

        # Подсчитываем общее количество
        total_proxies = await proxy_service.get_user_proxies(
            db, user_id=current_user.id, active_only=active_only, skip=0, limit=1000
        )
        total = len(total_proxies)

        pages = (total + limit - 1) // limit if total > 0 else 0

        logger.info(f"Retrieved {len(proxies)} proxies for user {current_user.id}")

        return ProxyListResponse(
            purchases=proxies,
            total=total,
            page=(skip // limit) + 1,
            per_page=limit,
            pages=pages
        )

    except Exception as e:
        logger.error(f"Error getting user proxies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get proxies"
        )


@router.get("/expiring", response_model=List[dict])
async def get_expiring_proxies(
    current_user: User = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db),
    days_ahead: int = Query(7, ge=1, le=30, description="За сколько дней до истечения показывать")
):
    """Получение прокси, которые скоро истекают."""
    try:
        expiring_proxies = await proxy_service.get_expiring_proxies(
            db,
            user_id=current_user.id,
            days_ahead=days_ahead
        )

        logger.info(f"Found {len(expiring_proxies)} expiring proxies for user {current_user.id}")
        return expiring_proxies

    except Exception as e:
        logger.error(f"Error getting expiring proxies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get expiring proxies"
        )


@router.get("/stats", response_model=ProxyStatsResponse)
async def get_proxy_stats(
    current_user: User = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db),
    period_days: int = Query(30, ge=1, le=365, description="Период для статистики в днях"),
    include_expired: bool = Query(False, description="Включать истекшие"),
    group_by: str = Query("category", description="Группировка")
):
    """Получение статистики по прокси пользователя."""
    try:
        # Исправлено: используем правильный параметр
        stats = await proxy_service.get_proxy_statistics(
            db,
            user_id=current_user.id,
            days=period_days  # Исправлено: используем days вместо stats_request
        )

        logger.info(f"Retrieved proxy stats for user {current_user.id}")
        return ProxyStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Error getting proxy stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get proxy statistics"
        )


@router.get("/{purchase_id}")
async def get_proxy_details(
    purchase_id: int,
    current_user: User = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db)
):
    """Получение детальной информации о покупке прокси."""
    try:
        # Исправлено: используем правильный метод
        proxy_details = await proxy_service.get_proxy_usage_details(
            db,
            purchase_id=purchase_id,
            user_id=current_user.id
        )

        if not proxy_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proxy purchase not found or access denied"
            )

        return proxy_details

    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting proxy details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get proxy details"
        )


@router.post("/{purchase_id}/generate", response_model=ProxyGenerationResponse)
async def generate_proxy_list(
    purchase_id: int,
    generation_request: ProxyGenerationRequest,
    current_user: User = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db)
):
    """Генерация отформатированного списка прокси - КЛЮЧЕВОЕ для страницы генерации."""
    try:
        proxy_list = await proxy_service.generate_proxy_list(
            db,
            purchase_id=purchase_id,
            user_id=current_user.id,
            generation_request=generation_request
        )

        logger.info(f"Generated proxy list for purchase {purchase_id}")
        return proxy_list

    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error generating proxy list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate proxy list"
        )


@router.get("/{purchase_id}/download", response_class=PlainTextResponse)
async def download_proxy_list(
    purchase_id: int,
    current_user: User = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db),
    format_type: str = Query("ip:port:user:pass", description="Формат вывода"),
    include_auth: bool = Query(True, description="Включить данные аутентификации"),
    separator: str = Query("\n", description="Разделитель между прокси")
):
    """Скачивание списка прокси в виде текстового файла - КЛЮЧЕВОЕ для скачивания."""
    try:
        generation_request = ProxyGenerationRequest(
            format_type=format_type,
            include_auth=include_auth,
            separator=separator
        )

        proxy_list = await proxy_service.generate_proxy_list(
            db,
            purchase_id=purchase_id,
            user_id=current_user.id,
            generation_request=generation_request
        )

        if not proxy_list.proxies:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No proxies found for this purchase"
            )

        proxy_text = separator.join(proxy_list.proxies)

        # Генерируем имя файла
        safe_format = format_type.replace(":", "_").replace("@", "_at_").replace("/", "_")
        filename = f"proxies_{purchase_id}_{safe_format}.txt"

        logger.info(f"Downloaded proxy list for purchase {purchase_id}")

        return PlainTextResponse(
            content=proxy_text,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "text/plain; charset=utf-8"
            }
        )

    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading proxy list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download proxy list"
        )


@router.post("/{purchase_id}/extend", response_model=ProxyExtensionResponse)
async def extend_proxies(
    purchase_id: int,
    extension_request: ProxyExtensionRequest,
    current_user: User = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db)
):
    """Продление прокси подписки - КЛЮЧЕВОЕ для продления услуг."""
    try:
        extension_result = await proxy_service.extend_proxy_subscription(
            db,
            purchase_id=purchase_id,
            user_id=current_user.id,
            extension_request=extension_request
        )

        logger.info(f"Extended proxies for purchase {purchase_id} by {extension_request.days} days")
        return extension_result

    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error extending proxies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extend proxies"
        )


@router.post("/{purchase_id}/deactivate", response_model=MessageResponse)
async def deactivate_proxy(
    purchase_id: int,
    current_user: User = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db),
    reason: Optional[str] = Query(None, max_length=500, description="Причина деактивации")
):
    """Деактивация прокси подписки."""
    try:
        success = await proxy_service.deactivate_proxy_purchase(
            db,
            purchase_id=purchase_id,
            user_id=current_user.id,
            reason=reason
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to deactivate proxy or already inactive"
            )

        return MessageResponse(
            message="Proxy deactivated successfully",
            success=True,
            details={"purchase_id": purchase_id, "reason": reason}
        )

    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating proxy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate proxy"
        )


@router.post("/{purchase_id}/sync", response_model=dict)
async def sync_with_provider(
    purchase_id: int,
    current_user: User = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db)
):
    """Синхронизация с провайдером - для интеграции с 711."""
    try:
        sync_result = await proxy_service.sync_proxy_with_provider(
            db,
            purchase_id=purchase_id,
            user_id=current_user.id
        )

        return sync_result

    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error syncing with provider: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync with provider"
        )
