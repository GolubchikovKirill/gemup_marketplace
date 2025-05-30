import logging
from typing import List, Optional, Dict, Any, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.proxy_product import proxy_product_crud
from app.models.models import ProxyProduct, ProxyCategory
from app.schemas.proxy_product import ProxyProductCreate, ProxyProductUpdate, ProductFilter
from app.services.base import BaseService, BusinessRuleValidator

logger = logging.getLogger(__name__)


class ProductBusinessRules(BusinessRuleValidator):
    """Валидатор бизнес-правил для продуктов"""

    async def validate(self, data: dict, db: AsyncSession) -> bool:
        """Валидация правил продукта"""
        return True


class ProductService(BaseService[ProxyProduct, ProxyProductCreate, ProxyProductUpdate]):
    """Сервис для работы с продуктами"""

    def __init__(self):
        super().__init__(ProxyProduct)
        self.crud = proxy_product_crud
        self.business_rules = ProductBusinessRules()

    async def get_products_with_filter(
            self,
            db: AsyncSession,
            filter_params: ProductFilter,
            skip: int = 0,
            limit: int = 20
    ) -> Tuple[List[ProxyProduct], int]:
        """Получение продуктов с фильтрацией"""
        try:
            products = await self.crud.get_products_with_filter(
                db, filter_params=filter_params, skip=skip, limit=limit
            )
            total = await self.crud.count_products_with_filter(db, filter_params=filter_params)
            return products, total
        except Exception as e:
            logger.error(f"Error getting products with filter: {e}")
            return [], 0

    async def get_product_by_id(self, db: AsyncSession, product_id: int) -> Optional[ProxyProduct]:
        """Получение продукта по ID"""
        try:
            return await self.crud.get(db, obj_id=product_id)
        except Exception as e:
            logger.error(f"Error getting product by ID: {e}")
            return None

    async def check_availability(
            self,
            db: AsyncSession,
            product_id: int,
            quantity: int
    ) -> Dict[str, Any]:
        """Проверка доступности продукта"""
        try:
            product = await self.crud.get(db, obj_id=product_id)
            if not product:
                return {
                    "product_id": product_id,
                    "requested_quantity": quantity,
                    "is_available": False,
                    "stock_available": 0,
                    "message": "Product not found"
                }

            is_available = product.is_active and product.stock_available >= quantity

            return {
                "product_id": product_id,
                "requested_quantity": quantity,
                "is_available": is_available,
                "stock_available": product.stock_available,
                "message": "Available" if is_available else "Insufficient stock"
            }
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            return {
                "product_id": product_id,
                "requested_quantity": quantity,
                "is_available": False,
                "stock_available": 0,
                "message": "Error checking availability"
            }

    async def get_products_by_category(
            self,
            db: AsyncSession,
            category: ProxyCategory,
            skip: int = 0,
            limit: int = 20
    ) -> List[ProxyProduct]:
        """Получение продуктов по категории"""
        try:
            return await self.crud.get_products_by_category(
                db, category=category, skip=skip, limit=limit
            )
        except Exception as e:
            logger.error(f"Error getting products by category: {e}")
            return []

    async def get_categories_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """Получение статистики по категориям"""
        try:
            stats = {}
            for category in ProxyCategory:
                count = await self.crud.count_products_by_category(db, category)
                stats[category.value] = {
                    "count": count,
                    "category": category.value,
                    "name": category.value.replace('_', ' ').title()
                }
            return stats
        except Exception as e:
            logger.error(f"Error getting categories stats: {e}")
            return {}

    async def get_available_countries(self, db: AsyncSession) -> List[Dict[str, str]]:
        """Получение списка доступных стран"""
        try:
            countries = await self.crud.get_available_countries(db)
            return [
                {
                    "code": country.country_code,
                    "name": country.country_name
                }
                for country in countries
            ]
        except Exception as e:
            logger.error(f"Error getting available countries: {e}")
            return []

    # Реализация абстрактных методов BaseService
    async def create(self, db: AsyncSession, obj_in: ProxyProductCreate) -> ProxyProduct:
        return await self.crud.create(db, obj_in=obj_in)

    async def get(self, db: AsyncSession, obj_id: int) -> Optional[ProxyProduct]:
        return await self.crud.get(db, obj_id=obj_id)

    async def update(self, db: AsyncSession, db_obj: ProxyProduct, obj_in: ProxyProductUpdate) -> ProxyProduct:
        return await self.crud.update(db, db_obj=db_obj, obj_in=obj_in)

    async def delete(self, db: AsyncSession, obj_id: int) -> bool:
        await self.crud.remove(db, obj_id=obj_id)
        return True

    async def get_multi(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[ProxyProduct]:
        return await self.crud.get_multi(db, skip=skip, limit=limit)


product_service = ProductService()
