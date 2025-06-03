"""
Роуты для управления продуктами прокси.

Обеспечивает API endpoints для получения каталога продуктов,
поиска, фильтрации и получения информации о доступности.
"""

import logging
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.models import ProxyCategory, ProxyType, ProviderType
from app.schemas.proxy_product import (
    ProxyProductResponse, ProductFilter, ProductListResponse,
    ProductsByCategoryResponse  # ИСПРАВЛЕНО: теперь схема существует
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
        sort: Optional[str] = Query("created_at_desc", description="Сортировка"),
        db: AsyncSession = Depends(get_db)
):
    """
    Получение списка продуктов с фильтрацией и пагинацией
    """
    try:
        # ИСПРАВЛЕНО: убрали параметры, которых нет в схеме
        product_filter = ProductFilter(
            search=search,
            proxy_category=proxy_category,
            proxy_type=proxy_type,
            provider=provider,
            country=country,
            min_price=min_price,
            max_price=max_price,
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
        availability = await product_service.check_product_availability(  # ИСПРАВЛЕНО: правильное имя метода
            db, product_id=product_id, quantity=quantity
        )

        return availability

    except Exception as e:
        logger.error(f"Error checking availability for product {product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check product availability"
        )


@router.get("/categories/stats", response_model=List[Dict[str, Any]])  # ИСПРАВЛЕНО: правильный response_model
async def get_categories_stats(db: AsyncSession = Depends(get_db)):
    """Получение статистики по категориям"""
    try:
        stats = await product_service.get_categories_with_stats(db)  # ИСПРАВЛЕНО: правильное имя метода
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
        products, total = await product_service.get_products_by_category(  # ИСПРАВЛЕНО: получаем total
            db, category=category, skip=(page - 1) * size, limit=size
        )

        return ProductsByCategoryResponse(
            category=category.value,
            products=products,
            page=page,
            size=size,
            total=total  # ИСПРАВЛЕНО: используем total из сервиса
        )
    except Exception as e:
        logger.error(f"Error getting products by category {category}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get products for category {category}"
        )


@router.get("/meta/countries", response_model=List[Dict[str, Any]])  # ИСПРАВЛЕНО: правильный response_model
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


@router.get("/featured", response_model=List[ProxyProductResponse])  # ДОБАВЛЕНО: новый endpoint
async def get_featured_products(
        category: Optional[ProxyCategory] = Query(None, description="Фильтр по категории"),
        limit: int = Query(5, ge=1, le=20, description="Количество продуктов"),
        db: AsyncSession = Depends(get_db)
):
    """Получение рекомендуемых продуктов"""
    try:
        products = await product_service.get_featured_products(db, category=category, limit=limit)
        return products
    except Exception as e:
        logger.error(f"Error getting featured products: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get featured products"
        )


@router.get("/search", response_model=List[ProxyProductResponse])  # ДОБАВЛЕНО: новый endpoint
async def search_products(
        q: str = Query(..., min_length=2, description="Поисковый запрос"),
        skip: int = Query(0, ge=0, description="Пропустить записей"),
        limit: int = Query(20, ge=1, le=100, description="Максимум записей"),
        db: AsyncSession = Depends(get_db)
):
    """Поиск продуктов по ключевому слову"""
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
