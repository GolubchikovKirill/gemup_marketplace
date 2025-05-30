import logging
import math
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.dependencies import get_current_registered_user
from app.models.models import ProxyType, ProxyCategory, SessionType, ProviderType
from app.schemas.base import MessageResponse
from app.schemas.proxy_product import (
    ProxyProductPublic,
    ProxyProductCreate,
    ProxyProductUpdate,
    ProductFilter as ProxyProductFilter,
    ProductListResponse,
    CountryResponse,
    CityResponse
)
from app.services.product_service import product_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("/", response_model=ProductListResponse)
async def get_products(
        page: int = Query(1, ge=1, description="Номер страницы"),
        size: int = Query(20, ge=1, le=100, description="Размер страницы"),
        proxy_type: Optional[ProxyType] = Query(None, description="Тип прокси"),
        proxy_category: Optional[ProxyCategory] = Query(None, description="Категория прокси"),
        session_type: Optional[SessionType] = Query(None, description="Тип сессии"),
        provider: Optional[ProviderType] = Query(None, description="Провайдер"),
        country_code: Optional[str] = Query(None, min_length=2, max_length=2, description="Код страны"),
        city: Optional[str] = Query(None, description="Город"),
        min_price: Optional[float] = Query(None, ge=0, description="Минимальная цена"),
        max_price: Optional[float] = Query(None, ge=0, description="Максимальная цена"),
        min_speed: Optional[int] = Query(None, ge=1, description="Минимальная скорость (Mbps)"),
        min_uptime: Optional[float] = Query(None, ge=0, le=100, description="Минимальный uptime (%)"),
        min_duration: Optional[int] = Query(None, ge=1, description="Минимальный срок действия"),
        max_duration: Optional[int] = Query(None, ge=1, description="Максимальный срок действия"),
        min_points_per_hour: Optional[int] = Query(None, ge=0, description="Минимум очков в час"),
        min_farm_efficiency: Optional[float] = Query(None, ge=0, le=100, description="Минимальная эффективность фарминга"),
        auto_claim_only: Optional[bool] = Query(None, description="Только с автоклеймом"),
        multi_account_only: Optional[bool] = Query(None, description="Только с поддержкой мульти-аккаунтов"),
        is_featured: Optional[bool] = Query(None, description="Только рекомендуемые"),
        search: Optional[str] = Query(None, description="Поиск по названию"),
        db: AsyncSession = Depends(get_db)
):
    """
    Получение списка продуктов с фильтрацией и пагинацией

    - **proxy_category**: residential, datacenter, isp, nodepay, grass
    - **min_points_per_hour**: минимум очков в час (для nodepay/grass)
    - **min_farm_efficiency**: минимальная эффективность фарминга (для nodepay/grass)
    - **auto_claim_only**: только с автоматическим клеймом (для nodepay/grass)
    - **multi_account_only**: только с поддержкой мульти-аккаунтов (для nodepay/grass)
    """
    try:
        # Создаем фильтр с новыми полями
        filters = ProxyProductFilter(
            proxy_type=proxy_type,
            proxy_category=proxy_category,
            session_type=session_type,
            provider=provider,
            country_code=country_code,
            city=city,
            featured_only=is_featured or False,
            min_price=min_price,
            max_price=max_price,
            min_speed=min_speed,
            min_uptime=min_uptime,
            min_duration=min_duration,
            max_duration=max_duration,
            min_points_per_hour=min_points_per_hour,
            min_farm_efficiency=min_farm_efficiency,
            auto_claim_only=auto_claim_only,
            multi_account_only=multi_account_only,
            search=search
        )

        # Получаем продукты
        products, total = await product_service.get_products_with_filters(
            db, filters, page, size
        )

        # Рассчитываем количество страниц
        pages = math.ceil(total / size) if total > 0 else 1

        return ProductListResponse(
            items=products,
            total=total,
            page=page,
            size=size,
            pages=pages
        )

    except Exception as e:
        logger.error(f"Error getting products: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get products"
        )



@router.get("/categories/stats")
async def get_categories_stats(db: AsyncSession = Depends(get_db)):
    """
    Получение статистики по категориям прокси
    """
    try:
        from app.crud.proxy_product import proxy_product_crud
        stats = await proxy_product_crud.get_categories_stats(db)
        return stats
    except Exception as e:
        logger.error(f"Error getting categories stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get categories stats"
        )


@router.get("/categories/{category}")
async def get_products_by_category(
        category: ProxyCategory,
        skip: int = 0,
        limit: int = 20,
        db: AsyncSession = Depends(get_db)
):
    """
    Получение продуктов по категории
    """
    try:
        from app.crud.proxy_product import proxy_product_crud
        products = await proxy_product_crud.get_by_filters(
            db, proxy_category=category, skip=skip, limit=limit
        )

        return {"category": category, "products": products}
    except Exception as e:
        logger.error(f"Error getting products by category: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get products by category"
        )


@router.get("/{product_id}", response_model=ProxyProductPublic)
async def get_product(
        product_id: int,
        db: AsyncSession = Depends(get_db)
):
    """
    Получение детальной информации о продукте
    """
    try:
        product = await product_service.get_product_by_id(db, product_id)

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )

        return product

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting product {product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get product"
        )


@router.post("/", response_model=ProxyProductPublic, status_code=status.HTTP_201_CREATED)
async def create_product(
        product_data: ProxyProductCreate,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_registered_user)
):
    """
    Создание нового продукта (только для администраторов)
    """
    try:
        # TODO: Добавить проверку прав администратора
        product = await product_service.create_product(db, product_data)
        logger.info(f"Product created by user {current_user.id}: {product.name}")
        return product

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating product: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create product"
        )


@router.put("/{product_id}", response_model=ProxyProductPublic)
async def update_product(
        product_id: int,
        product_data: ProxyProductUpdate,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_registered_user)
):
    """
    Обновление продукта (только для администраторов)
    """
    try:
        product = await product_service.update_product(db, product_id, product_data)

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )

        logger.info(f"Product {product_id} updated by user {current_user.id}")
        return product

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating product {product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update product"
        )


@router.delete("/{product_id}", response_model=MessageResponse)
async def delete_product(
        product_id: int,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_registered_user)
):
    """
    Удаление продукта (только для администраторов)
    """
    try:
        success = await product_service.delete_product(db, product_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )

        logger.info(f"Product {product_id} deleted by user {current_user.id}")
        return MessageResponse(message="Product successfully deleted")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting product {product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete product"
        )


@router.get("/meta/countries", response_model=List[CountryResponse])
async def get_countries(
        db: AsyncSession = Depends(get_db)
):
    """
    Получение списка доступных стран с городами
    """
    try:
        countries = await product_service.get_countries(db)
        return countries

    except Exception as e:
        logger.error(f"Error getting countries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get countries"
        )


@router.get("/meta/cities/{country_code}", response_model=List[CityResponse])
async def get_cities_by_country(
        country_code: str,
        db: AsyncSession = Depends(get_db)
):
    """
    Получение списка городов по коду страны
    """
    try:
        if len(country_code) != 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Country code must be 2 characters (ISO 3166-1 alpha-2)"
            )

        cities = await product_service.get_cities_by_country(db, country_code)
        return cities

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cities for {country_code}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get cities"
        )


@router.get("/{product_id}/availability")
async def check_product_availability(
        product_id: int,
        quantity: int = Query(..., ge=1, description="Требуемое количество"),
        db: AsyncSession = Depends(get_db)
):
    """
    Проверка доступности товара в требуемом количестве
    """
    try:
        is_available = await product_service.check_stock_availability(
            db, product_id, quantity
        )

        product = await product_service.get_product_by_id(db, product_id)

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )

        return {
            "product_id": product_id,
            "requested_quantity": quantity,
            "is_available": is_available,
            "stock_available": product.stock_available,
            "min_quantity": product.min_quantity,
            "max_quantity": product.max_quantity
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking availability for product {product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check availability"
        )
