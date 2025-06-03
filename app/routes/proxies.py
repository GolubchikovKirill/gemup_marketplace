"""
Роуты для управления купленными прокси.

Обеспечивает API endpoints для получения, управления и мониторинга
купленных прокси-серверов пользователей.
Включает генерацию списков, продление подписок и статистику.
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
from app.schemas.proxy_purchase import (  # ИСПРАВЛЕНО: правильные имена схем
    ProxyPurchaseResponse,
    ProxyExtensionRequest,  # Правильное имя
    ProxyExtensionResponse,  # Правильное имя
    ProxyStatsResponse,
    ProxyDetailsResponse  # Теперь существует
)
from app.services.proxy_service import proxy_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/proxies", tags=["Proxies"])


@router.get("/my",
            response_model=List[ProxyPurchaseResponse],
            summary="Мои прокси",
            description="Получение списка всех купленных прокси текущего пользователя")
async def get_my_proxies(
        current_user: User = Depends(get_current_registered_user),
        db: AsyncSession = Depends(get_db),
        active_only: bool = Query(True, description="Показывать только активные прокси"),
        skip: int = Query(0, ge=0, description="Пропустить записей"),
        limit: int = Query(50, ge=1, le=100, description="Максимум записей")
):
    """
    Получение списка купленных прокси пользователя.

    Возвращает все прокси-серверы, приобретенные пользователем,
    с возможностью фильтрации по статусу и пагинации.

    - **Требования**: Зарегистрированный пользователь
    - **Фильтрация**: По активности (по умолчанию только активные)
    - **Пагинация**: Поддерживается через skip/limit

    **Информация о каждом прокси:**
    - Основные данные (ID, продукт, количество)
    - Статус и срок действия
    - Учетные данные для подключения
    - Статистика использования

    **Фильтры:**
    - active_only=true: Только активные прокси
    - active_only=false: Все прокси (включая истекшие)
    """
    try:
        proxies = await proxy_service.get_user_proxies(
            db,
            user_id=current_user.id,
            active_only=active_only,
            skip=skip,
            limit=limit
        )

        logger.info(f"Retrieved {len(proxies)} proxies for user {current_user.id}")
        return proxies

    except Exception as e:
        logger.error(f"Error getting user proxies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get proxies"
        )


@router.get("/{purchase_id}",
            response_model=ProxyDetailsResponse,  # ИСПРАВЛЕНО: правильная схема
            summary="Детали прокси",
            description="Получение подробной информации о конкретной покупке прокси")
async def get_proxy_details(
        purchase_id: int,
        current_user: User = Depends(get_current_registered_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Получение детальной информации о покупке прокси.

    Возвращает полную информацию о конкретной покупке прокси включая:
    - Данные продукта и провайдера
    - Список прокси серверов с учетными данными
    - Статус и срок действия
    - Статистику использования
    - Метаданные провайдера

    - **Требования**: Зарегистрированный пользователь, владелец покупки
    - **Доступ**: Только к собственным покупкам

    **Ошибки:**
    - 404: Покупка не найдена или нет доступа
    - 403: Доступ запрещен
    """
    try:
        proxy_details = await proxy_service.get_proxy_details(
            db,
            purchase_id=purchase_id,
            user_id=current_user.id
        )

        if not proxy_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proxy purchase not found or access denied"
            )

        return ProxyDetailsResponse(**proxy_details)  # ИСПРАВЛЕНО: используем схему

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


@router.get("/{purchase_id}/download",
            response_class=PlainTextResponse,
            summary="Скачать список прокси",
            description="Скачивание списка прокси в виде текстового файла")
async def download_proxy_list(
        purchase_id: int,
        current_user: User = Depends(get_current_registered_user),
        db: AsyncSession = Depends(get_db),
        format_type: str = Query("ip:port:user:pass", description="Формат вывода")
):
    """
    Скачивание списка прокси в виде текстового файла.

    Генерирует и возвращает список прокси в указанном формате
    как текстовый файл для загрузки.

    - **Требования**: Зарегистрированный пользователь, владелец покупки
    - **Форматы вывода**:
      - "ip:port:user:pass" (по умолчанию)
      - "user:pass@ip:port"
      - "ip:port"
      - "https://user:pass@ip:port" (ИСПРАВЛЕНО: HTTPS вместо HTTP)

    **Использование:**
    Подходит для импорта в программы для работы с прокси,
    браузеры или другие приложения.

    **Ошибки:**
    - 400: Неверный формат или недоступная покупка
    - 404: Покупка не найдена
    """
    try:
        # Получаем детали прокси
        proxy_details = await proxy_service.get_proxy_details(
            db,
            purchase_id=purchase_id,
            user_id=current_user.id
        )

        if not proxy_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proxy purchase not found"
            )

        # Генерируем список в нужном формате
        proxy_list = proxy_details.get("proxy_list", [])
        username = proxy_details.get("credentials", {}).get("username", "")
        password = proxy_details.get("credentials", {}).get("password", "")

        # Форматируем прокси согласно запрошенному формату
        formatted_proxies = []
        for proxy in proxy_list:
            ip = proxy.get("ip", "")
            port = proxy.get("port", "")

            if format_type == "ip:port:user:pass":
                formatted_proxies.append(f"{ip}:{port}:{username}:{password}")
            elif format_type == "user:pass@ip:port":
                formatted_proxies.append(f"{username}:{password}@{ip}:{port}")
            elif format_type == "ip:port":
                formatted_proxies.append(f"{ip}:{port}")
            elif format_type == "https://user:pass@ip:port":  # ИСПРАВЛЕНО: HTTPS
                formatted_proxies.append(f"https://{username}:{password}@{ip}:{port}")
            else:
                # По умолчанию
                formatted_proxies.append(f"{ip}:{port}:{username}:{password}")

        proxy_text = "\n".join(formatted_proxies)

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


@router.post("/{purchase_id}/extend",
             response_model=ProxyExtensionResponse,  # ИСПРАВЛЕНО: правильная схема
             summary="Продлить прокси",
             description="Продление срока действия прокси подписки")
async def extend_proxies(
        purchase_id: int,
        extension_request: ProxyExtensionRequest,  # ИСПРАВЛЕНО: правильная схема
        current_user: User = Depends(get_current_registered_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Продление прокси подписки.

    Позволяет продлить срок действия активных прокси на указанное
    количество дней. Продление возможно только для активных подписок.

    - **Требования**: Зарегистрированный пользователь, владелец покупки
    - **Условия**: Прокси должны быть активными
    - **Оплата**: Списание с баланса пользователя

    **Параметры продления:**
    - Минимум: 1 день
    - Максимум: 365 дней
    - Стоимость: Рассчитывается пропорционально

    **Логика продления:**
    - Если прокси еще активны: продление от текущей даты истечения
    - Если прокси истекли: продление от текущего момента

    **Ошибки:**
    - 400: Невозможно продлить (неактивные прокси, недостаток средств)
    - 404: Покупка не найдена
    """
    try:
        extension_result = await proxy_service.extend_proxy_subscription(
            db,
            purchase_id=purchase_id,
            user_id=current_user.id,
            days=extension_request.days
        )

        logger.info(f"Extended proxies for purchase {purchase_id} by {extension_request.days} days")
        return ProxyExtensionResponse(**extension_result)  # ИСПРАВЛЕНО: используем схему

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


@router.get("/expiring",
            response_model=List[ProxyPurchaseResponse],
            summary="Истекающие прокси",
            description="Получение списка прокси, которые скоро истекают")
async def get_expiring_proxies(
        current_user: User = Depends(get_current_registered_user),
        db: AsyncSession = Depends(get_db),
        days_ahead: int = Query(7, ge=1, le=30, description="За сколько дней до истечения показывать")
):
    """
    Получение прокси, которые скоро истекают.

    Возвращает список прокси подписок, срок действия которых
    истекает в ближайшее время. Полезно для напоминаний о продлении.

    - **Требования**: Зарегистрированный пользователь
    - **Период**: От 1 до 30 дней вперед (по умолчанию 7)
    - **Фильтр**: Только активные прокси близкие к истечению

    **Информация для каждого прокси:**
    - Данные о продукте
    - Текущий статус
    - Дата истечения
    - Количество оставшихся дней
    - Возможность продления

    **Использование:**
    Для уведомлений пользователей о необходимости продления
    и предотвращения неожиданного отключения сервиса.
    """
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


@router.get("/stats",
            response_model=ProxyStatsResponse,
            summary="Статистика прокси",
            description="Получение статистики использования прокси пользователя")
async def get_proxy_stats(
        current_user: User = Depends(get_current_registered_user),
        db: AsyncSession = Depends(get_db),
        days: int = Query(30, ge=1, le=365, description="Период для статистики в днях")
):
    """
    Получение статистики по прокси пользователя.

    Возвращает агрегированную статистику использования прокси
    за указанный период.

    - **Требования**: Зарегистрированный пользователь
    - **Период**: От 1 до 365 дней (по умолчанию 30)

    **Статистика включает:**
    - Общее количество покупок
    - Количество активных прокси
    - Общий объем использованного трафика
    - Разбивка по продуктам и провайдерам
    - Средние показатели производительности

    **Применение:**
    - Анализ использования сервиса
    - Планирование дальнейших покупок
    - Мониторинг эффективности
    """
    try:
        stats = await proxy_service.get_proxy_statistics(
            db,
            user_id=current_user.id,
            days=days
        )

        logger.info(f"Retrieved proxy stats for user {current_user.id}")
        return ProxyStatsResponse(**stats)  # ИСПРАВЛЕНО: используем схему

    except Exception as e:
        logger.error(f"Error getting proxy stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get proxy statistics"
        )


@router.post("/{purchase_id}/deactivate",
             response_model=MessageResponse,
             summary="Деактивировать прокси",
             description="Принудительная деактивация прокси подписки")
async def deactivate_proxy(
        purchase_id: int,
        current_user: User = Depends(get_current_registered_user),
        db: AsyncSession = Depends(get_db),
        reason: Optional[str] = Query(None, max_length=500, description="Причина деактивации")
):
    """
    Деактивация прокси подписки.

    Позволяет пользователю принудительно деактивировать свои прокси
    до истечения срока действия. Полезно при проблемах с качеством
    или изменении потребностей.

    - **Требования**: Зарегистрированный пользователь, владелец покупки
    - **Результат**: Немедленная деактивация всех прокси в покупке
    - **Возврат средств**: Не предусмотрен при добровольной деактивации

    **Внимание:**
    Деактивированные прокси нельзя восстановить.
    Возврат средств осуществляется только через поддержку.

    **Ошибки:**
    - 400: Нельзя деактивировать (уже неактивны)
    - 404: Покупка не найдена или нет доступа
    """
    try:
        success = await proxy_service.deactivate_proxy(
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

        return MessageResponse(message="Proxy deactivated successfully")

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
