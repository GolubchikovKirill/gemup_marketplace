import logging
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.models import ProxyCategory, ProxyType, ProviderType
from app.schemas.proxy_product import (
    ProxyProductResponse, ProductFilter, ProductListResponse,
    ProductsByCategoryResponse
)
from app.services.product_service import product_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/products", tags=["Products"])


@router.get("/", response_model=ProductListResponse)
async def get_products(
        page: int = Query(1, ge=1, description="Номер страницы"),
        size: int = Query(20, ge=1, le=100, description="Размер страницы"),
        search: Optional[str] = Query(None, description="Поиск по названию"),
        proxy_category: Optional[ProxyCategory] = Query(None, description="Категория прокси"),
        proxy_type: Optional[ProxyType] = Query(None, description="Тип прокси"),
        provider: Optional[ProviderType] = Query(None, description="Провайдер"),
        country: Optional[str] = Query(None, description="Код страны"),
        min_price: Optional[float] = Query(None, ge=0, description="Минимальная цена"),
        max_price: Optional[float] = Query(None, ge=0, description="Максимальная цена"),
        min_points_per_hour: Optional[int] = Query(None, ge=0, description="Минимум поинтов в час"),
        auto_claim_only: Optional[bool] = Query(None, description="Только с автоклеймом"),
        min_farm_efficiency: Optional[float] = Query(None, ge=0, description="Минимальная эффективность фарминга"),
        multi_account_only: Optional[bool] = Query(None, description="Только с поддержкой мультиаккаунтов"),
        sort: Optional[str] = Query("created_at_desc", description="Сортировка"),
        db: AsyncSession = Depends(get_db)
):
    """
    Получение списка продуктов с фильтрацией и пагинацией
    """
    try:
        # Создаем фильтр с ВСЕМИ параметрами
        product_filter = ProductFilter(
            search=search,
            proxy_category=proxy_category,
            proxy_type=proxy_type,
            provider=provider,
            country=country,
            min_price=min_price,
            max_price=max_price,
            min_points_per_hour=min_points_per_hour,
            auto_claim_only=auto_claim_only,
            min_farm_efficiency=min_farm_efficiency,  # ДОБАВЛЕНО
            multi_account_only=multi_account_only,    # ДОБАВЛЕНО
            sort=sort
        )

        # Получаем продукты
        products, total = await product_service.get_products_with_filter(
            db, filter_params=product_filter, skip=(page - 1) * size, limit=size
        )

        return ProductListResponse(
            items=products,
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size
        )

    except Exception as e:
        logger.error(f"Error getting products: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get products"
        )


@router.get("/{product_id}", response_model=ProxyProductResponse)
async def get_product(
        product_id: int,
        db: AsyncSession = Depends(get_db)
):
    """
    Получение продукта по ID
    """
    try:
        product = await product_service.get_product_by_id(db, product_id=product_id)

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


@router.get("/{product_id}/availability")
async def check_product_availability(
        product_id: int,
        quantity: int = Query(..., ge=1, description="Требуемое количество"),
        db: AsyncSession = Depends(get_db)
):
    """
    Проверка доступности продукта
    """
    try:
        availability = await product_service.check_availability(
            db, product_id=product_id, quantity=quantity
        )

        return availability

    except Exception as e:
        logger.error(f"Error checking availability for product {product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check product availability"
        )


@router.get("/categories/stats", response_model=Dict[str, Any])
async def get_categories_stats(db: AsyncSession = Depends(get_db)):
    """Получение статистики по категориям"""
    try:
        stats = await product_service.get_categories_stats(db)
        return stats
    except Exception as e:
        logger.error(f"Error getting categories stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get categories statistics"
        )


@router.get("/categories/{category}", response_model=ProductsByCategoryResponse)
async def get_products_by_category(
        category: ProxyCategory,
        page: int = Query(1, ge=1, description="Номер страницы"),
        size: int = Query(20, ge=1, le=100, description="Размер страницы"),
        db: AsyncSession = Depends(get_db)
):
    """Получение продуктов по категории"""
    try:
        products = await product_service.get_products_by_category(
            db, category=category, skip=(page - 1) * size, limit=size
        )

        return ProductsByCategoryResponse(
            category=category.value,
            products=products,
            page=page,
            size=size,
            total=len(products)
        )
    except Exception as e:
        logger.error(f"Error getting products by category {category}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get products for category {category}"
        )


@router.get("/meta/countries", response_model=List[Dict[str, str]])
async def get_countries(db: AsyncSession = Depends(get_db)):
    """
    Получение списка доступных стран
    """
    try:
        countries = await product_service.get_available_countries(db)
        return countries

    except Exception as e:
        logger.error(f"Error getting countries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get countries"
        )
