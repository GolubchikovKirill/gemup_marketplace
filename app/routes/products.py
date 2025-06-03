"""
Роуты для управления продуктами прокси.

Обеспечивает API endpoints для получения каталога продуктов,
поиска, фильтрации и получения информации о доступности.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.models import ProxyCategory, ProxyType, ProviderType
from app.schemas.proxy_product import (
    ProxyProductResponse, ProductFilter, ProductListResponse,
    ProductsByCategoryResponse, CountryResponse, CategoryStatsResponse,
    ProductAvailabilityResponse, ProductStatsResponse
)
from app.services.product_service import product_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/products", tags=["Products"])


@router.get("/", response_model=ProductListResponse)
async def get_products(
    page: int = Query(1, ge=1, description="Номер страницы"),
    per_page: int = Query(20, ge=1, le=100, description="Размер страницы"),
    search: Optional[str] = Query(None, description="Поиск по названию"),
    proxy_category: Optional[ProxyCategory] = Query(None, description="Категория прокси"),
    proxy_type: Optional[ProxyType] = Query(None, description="Тип прокси"),
    provider: Optional[ProviderType] = Query(None, description="Провайдер"),
    country_code: Optional[str] = Query(None, description="Код страны"),
    min_price: Optional[float] = Query(None, ge=0, description="Минимальная цена"),
    max_price: Optional[float] = Query(None, ge=0, description="Максимальная цена"),
    sort: str = Query("created_at_desc", description="Сортировка"),
    in_stock_only: bool = Query(False, description="Только товары в наличии"),
    featured_only: bool = Query(False, description="Только рекомендуемые"),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение списка продуктов с фильтрацией и пагинацией.
    """
    try:
        product_filter = ProductFilter(
            search=search,
            proxy_category=proxy_category,
            proxy_type=proxy_type,
            provider=provider,
            country_code=country_code,
            min_price=min_price,
            max_price=max_price,
            sort=sort,
            in_stock_only=in_stock_only,
            featured_only=featured_only
        )

        # Получаем продукты
        products, total = await product_service.get_products_with_filter(
            db, filter_params=product_filter, skip=(page - 1) * per_page, limit=per_page
        )

        pages = (total + per_page - 1) // per_page if total > 0 else 0

        return ProductListResponse(
            items=products,
            total=total,
            page=page,
            per_page=per_page,
            pages=pages
        )

    except Exception as e:
        logger.error(f"Error getting products: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get products"
        )


@router.get("/stats", response_model=ProductStatsResponse)
async def get_products_statistics(db: AsyncSession = Depends(get_db)):
    """Получение общей статистики продуктов."""
    try:
        stats = await product_service.get_product_statistics(db)
        return ProductStatsResponse(**stats)
    except Exception as e:
        logger.error(f"Error getting product statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get product statistics"
        )


@router.get("/featured", response_model=List[ProxyProductResponse])
async def get_featured_products(
    category: Optional[ProxyCategory] = Query(None, description="Фильтр по категории"),
    limit: int = Query(5, ge=1, le=20, description="Количество продуктов"),
    db: AsyncSession = Depends(get_db)
):
    """Получение рекомендуемых продуктов."""
    try:
        products = await product_service.get_featured_products(
            db, category=category, limit=limit
        )
        return products
    except Exception as e:
        logger.error(f"Error getting featured products: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get featured products"
        )


@router.get("/search", response_model=List[ProxyProductResponse])
async def search_products(
    q: str = Query(..., min_length=2, description="Поисковый запрос"),
    skip: int = Query(0, ge=0, description="Пропустить записей"),
    limit: int = Query(20, ge=1, le=100, description="Максимум записей"),
    db: AsyncSession = Depends(get_db)
):
    """Поиск продуктов по ключевому слову."""
    try:
        products, processed_term = await product_service.search_products(
            db, search_term=q, skip=skip, limit=limit
        )
        return products
    except Exception as e:
        logger.error(f"Error searching products: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search products"
        )


@router.get("/categories/stats", response_model=List[CategoryStatsResponse])
async def get_categories_stats(db: AsyncSession = Depends(get_db)):
    """Получение статистики по категориям."""
    try:
        stats = await product_service.get_categories_with_stats(db)
        return [CategoryStatsResponse(**stat) for stat in stats]
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
    per_page: int = Query(20, ge=1, le=100, description="Размер страницы"),
    db: AsyncSession = Depends(get_db)
):
    """Получение продуктов по категории."""
    try:
        products, total = await product_service.get_products_by_category(
            db, category=category, skip=(page - 1) * per_page, limit=per_page
        )

        return ProductsByCategoryResponse(
            category=category,
            category_name=category.value.replace('_', ' ').title(),
            products=products,
            total=total,
            page=page,
            per_page=per_page
        )
    except Exception as e:
        logger.error(f"Error getting products by category {category}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get products for category {category}"
        )


@router.get("/countries", response_model=List[CountryResponse])
async def get_countries(db: AsyncSession = Depends(get_db)):
    """Получение списка доступных стран."""
    try:
        countries = await product_service.get_available_countries(db)
        return [CountryResponse(**country) for country in countries]
    except Exception as e:
        logger.error(f"Error getting countries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get countries"
        )


@router.get("/{product_id}", response_model=ProxyProductResponse)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получение продукта по ID."""
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


@router.get("/{product_id}/availability", response_model=ProductAvailabilityResponse)
async def check_product_availability(
    product_id: int,
    quantity: int = Query(..., ge=1, description="Требуемое количество"),
    db: AsyncSession = Depends(get_db)
):
    """Проверка доступности продукта."""
    try:
        availability = await product_service.check_product_availability(
            db, product_id=product_id, quantity=quantity
        )

        return ProductAvailabilityResponse(**availability)

    except Exception as e:
        logger.error(f"Error checking availability for product {product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check product availability"
        )


@router.get("/{product_id}/recommendations", response_model=List[ProxyProductResponse])
async def get_product_recommendations(
    product_id: int,
    limit: int = Query(5, ge=1, le=10, description="Количество рекомендаций"),
    db: AsyncSession = Depends(get_db)
):
    """Получение рекомендованных продуктов."""
    try:
        recommendations = await product_service.get_product_recommendations(
            db, product_id=product_id, limit=limit
        )
        return recommendations
    except Exception as e:
        logger.error(f"Error getting recommendations for product {product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get product recommendations"
        )
