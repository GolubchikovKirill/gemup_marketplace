import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.dependencies import get_current_registered_user
from app.core.exceptions import BusinessLogicError
from app.models.models import User
from app.schemas.proxy_purchase import (
    ProxyPurchaseResponse, ProxyGenerationRequest, ProxyGenerationResponse,
    ProxyExtendRequest
)
from app.services.proxy_service import proxy_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/proxies", tags=["Proxies"])


@router.get("/my", response_model=List[ProxyPurchaseResponse])
async def get_my_proxies(
        active_only: bool = Query(True, description="Показывать только активные прокси"),
        current_user: User = Depends(get_current_registered_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Получение списка купленных прокси пользователя

    - **active_only**: Показывать только активные прокси
    """
    try:
        proxies = await proxy_service.get_user_proxies(
            db, user=current_user, active_only=active_only
        )

        logger.info(f"Retrieved {len(proxies)} proxies for user {current_user.id}")
        return proxies

    except Exception as e:
        logger.error(f"Error getting user proxies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get proxies"
        )


@router.post("/{purchase_id}/generate", response_model=ProxyGenerationResponse)
async def generate_proxy_list(
        purchase_id: int,
        request: ProxyGenerationRequest,
        current_user: User = Depends(get_current_registered_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Генерация списка прокси в нужном формате

    - **purchase_id**: ID покупки прокси
    - **format_type**: Формат вывода (ip:port:user:pass, user:pass@ip:port, ip:port)
    """
    try:
        proxy_data = await proxy_service.generate_proxy_list(
            db,
            purchase_id=purchase_id,
            user=current_user,
            format_type=request.format_type
        )

        logger.info(f"Generated proxy list for purchase {purchase_id}")
        return ProxyGenerationResponse(**proxy_data)

    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e.message) if hasattr(e, 'message') else str(e)
        )
    except Exception as e:
        logger.error(f"Error generating proxy list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate proxy list"
        )


@router.get("/{purchase_id}/download")
async def download_proxy_list(
        purchase_id: int,
        format_type: str = Query("ip:port:user:pass", description="Формат вывода"),
        current_user: User = Depends(get_current_registered_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Скачивание списка прокси в виде текстового файла

    - **purchase_id**: ID покупки прокси
    - **format_type**: Формат вывода
    """
    try:
        proxy_data = await proxy_service.generate_proxy_list(
            db,
            purchase_id=purchase_id,
            user=current_user,
            format_type=format_type
        )

        # Создаем текстовый файл
        proxy_text = "\n".join(proxy_data["proxies"])

        # Генерируем имя файла
        filename = f"proxies_{purchase_id}_{format_type.replace(':', '_')}.txt"

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
            detail=str(e.message) if hasattr(e, 'message') else str(e)
        )
    except Exception as e:
        logger.error(f"Error downloading proxy list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download proxy list"
        )


@router.post("/{purchase_id}/extend", response_model=ProxyPurchaseResponse)
async def extend_proxies(
        purchase_id: int,
        request: ProxyExtendRequest,
        current_user: User = Depends(get_current_registered_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Продление прокси

    - **purchase_id**: ID покупки прокси
    - **days**: Количество дней для продления
    """
    try:
        extended_purchase = await proxy_service.extend_proxy_purchase(
            db,
            purchase_id=purchase_id,
            user=current_user,
            days=request.days
        )

        logger.info(f"Extended proxies for purchase {purchase_id} by {request.days} days")
        return extended_purchase

    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e.message) if hasattr(e, 'message') else str(e)
        )
    except Exception as e:
        logger.error(f"Error extending proxies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extend proxies"
        )


@router.get("/expiring", response_model=List[ProxyPurchaseResponse])
async def get_expiring_proxies(
        days_ahead: int = Query(7, ge=1, le=365, description="За сколько дней до истечения показывать"),
        current_user: User = Depends(get_current_registered_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Получение прокси, которые скоро истекают

    - **days_ahead**: За сколько дней до истечения показывать
    """
    try:
        expiring_proxies = await proxy_service.get_expiring_proxies(
            db, user=current_user, days_ahead=days_ahead
        )

        logger.info(f"Found {len(expiring_proxies)} expiring proxies for user {current_user.id}")
        return expiring_proxies

    except Exception as e:
        logger.error(f"Error getting expiring proxies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get expiring proxies"
        )


@router.get("/stats", response_model=dict)
async def get_proxy_stats(
        current_user: User = Depends(get_current_registered_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Получение статистики по прокси пользователя
    """
    try:
        stats = await proxy_service.get_user_proxy_stats(db, user=current_user)

        logger.info(f"Retrieved proxy stats for user {current_user.id}")
        return stats

    except Exception as e:
        logger.error(f"Error getting proxy stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get proxy statistics"
        )
