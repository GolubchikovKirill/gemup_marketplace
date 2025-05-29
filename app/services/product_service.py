import logging
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.proxy_product import proxy_product_crud
from app.models.models import ProxyProduct
from app.schemas.proxy_product import ProductFilter, ProxyProductCreate, ProxyProductUpdate
from app.services.base import BaseService, BusinessRuleValidator

logger = logging.getLogger(__name__)


class ProductBusinessRules(BusinessRuleValidator):
    """Валидатор бизнес-правил для продуктов"""

    async def validate(self, data: dict, db: AsyncSession) -> bool:
        """Валидация правил продукта"""
        return True


class ProductService(BaseService[ProxyProduct, dict, dict]):
    """Сервис для работы с продуктами"""

    def __init__(self):
        super().__init__(ProxyProduct)
        self.crud = proxy_product_crud
        self.business_rules = ProductBusinessRules()

    async def get_products_with_filters(
            self,
            db: AsyncSession,
            filters: ProductFilter,
            page: int = 1,
            size: int = 20
    ) -> tuple[List[ProxyProduct], int]:
        """Получение продуктов с фильтрацией и пагинацией"""
        try:
            skip = (page - 1) * size
            limit = min(size, 100)

            # Получаем продукты с фильтрами
            products = await self.crud.get_by_filters(
                db,
                proxy_type=filters.proxy_type,
                proxy_category=filters.proxy_category,
                session_type=filters.session_type,
                provider=filters.provider,
                country_code=filters.country_code,
                city=filters.city,
                featured_only=filters.featured_only,
                min_speed=filters.min_speed,
                min_uptime=filters.min_uptime,
                # НОВЫЕ ФИЛЬТРЫ для фарминга
                min_points_per_hour=getattr(filters, 'min_points_per_hour', None),
                min_farm_efficiency=getattr(filters, 'min_farm_efficiency', None),
                auto_claim_only=getattr(filters, 'auto_claim_only', None),
                multi_account_only=getattr(filters, 'multi_account_only', None),
                skip=skip,
                limit=limit
            )

            # Применяем дополнительные фильтры
            filtered_products = []
            for product in products:
                # Фильтр по цене
                if filters.min_price and product.price_per_proxy < filters.min_price:
                    continue
                if filters.max_price and product.price_per_proxy > filters.max_price:
                    continue

                # Фильтр по сроку действия
                if filters.min_duration and product.duration_days < filters.min_duration:
                    continue
                if filters.max_duration and product.duration_days > filters.max_duration:
                    continue

                # Фильтр по поиску
                if filters.search:
                    search_term = filters.search.lower()
                    if (search_term not in product.name.lower() and
                            (product.description is None or search_term not in product.description.lower())):
                        continue

                filtered_products.append(product)

            # Получаем общее количество (упрощенно)
            total = len(filtered_products)

            logger.info(f"Retrieved {len(filtered_products)} products with filters")
            return filtered_products, total

        except Exception as e:
            logger.error(f"Error getting products with filters: {e}")
            return [], 0

    @staticmethod
    async def get_category_comparison(db: AsyncSession) -> Dict[str, Any]:
        """Сравнение характеристик категорий прокси"""

        comparison = {
            "residential": {
                "description": "Real ISP-assigned IPs from residential devices",
                "pros": ["Highest anonymity", "Lowest detection rate", "Global coverage"],
                "cons": ["Variable speed", "Higher cost per GB", "Less stable"],
                "best_for": ["Web scraping", "Geo-targeting", "Social media"],
                "avg_speed": "5-50 Mbps",
                "detection_rate": "< 1%",
                "pricing_model": "Per GB"
            },
            "datacenter": {
                "description": "High-speed IPs from data center servers",
                "pros": ["Highest speed", "Most stable", "Lowest cost"],
                "cons": ["Easier to detect", "Limited locations", "Higher block rate"],
                "best_for": ["High-speed tasks", "Automation", "Bulk operations"],
                "avg_speed": "100-1000 Mbps",
                "detection_rate": "5-15%",
                "pricing_model": "Per IP"
            },
            "isp": {
                "description": "Static residential IPs hosted on data centers",
                "pros": ["Residential appearance", "High speed", "Stable sessions"],
                "cons": ["Limited locations", "Higher cost", "Smaller IP pools"],
                "best_for": ["Account management", "E-commerce", "Long sessions"],
                "avg_speed": "50-200 Mbps",
                "detection_rate": "1-3%",
                "pricing_model": "Per IP"
            },
            # НОВЫЕ КАТЕГОРИИ
            "nodepay": {
                "description": "Specialized proxies for Nodepay farming and bandwidth sharing",
                "pros": ["Optimized for Nodepay", "Multi-account support", "Auto-claim features"],
                "cons": ["Platform-specific", "Limited to farming", "Requires setup"],
                "best_for": ["Nodepay farming", "Bandwidth monetization", "Passive income"],
                "avg_speed": "10-100 Mbps",
                "detection_rate": "< 2%",
                "pricing_model": "Per IP + Points/Hour",
                "special_features": ["Auto-claim", "Multi-account", "24/7 farming"]
            },
            "grass": {
                "description": "Optimized proxies for Grass network participation and data sharing",
                "pros": ["Grass-optimized", "High farming efficiency", "Stable connections"],
                "cons": ["Platform-specific", "Network dependent", "Setup complexity"],
                "best_for": ["Grass farming", "Data sharing", "Network participation"],
                "avg_speed": "20-150 Mbps",
                "detection_rate": "< 1%",
                "pricing_model": "Per IP + Efficiency Rate",
                "special_features": ["High efficiency", "Network diversity", "Automated farming"]
            }
        }

        return comparison

    # Остальные методы остаются без изменений...
    async def get_product_by_id(
            self,
            db: AsyncSession,
            product_id: int
    ) -> Optional[ProxyProduct]:
        """Получение продукта по ID"""
        try:
            product = await self.crud.get(db, obj_id=product_id)
            return product
        except Exception as e:
            logger.error(f"Error getting product {product_id}: {e}")
            return None

    async def create_product(
            self,
            db: AsyncSession,
            product_data: ProxyProductCreate
    ) -> ProxyProduct:
        """Создание нового продукта"""
        try:
            product = await self.crud.create(db, obj_in=product_data)
            logger.info(f"Product created: {product.name}")
            return product
        except Exception as e:
            logger.error(f"Error creating product: {e}")
            raise

    async def update_product(
            self,
            db: AsyncSession,
            product_id: int,
            product_data: ProxyProductUpdate
    ) -> Optional[ProxyProduct]:
        """Обновление продукта"""
        try:
            product = await self.crud.get(db, obj_id=product_id)
            if not product:
                return None

            updated_product = await self.crud.update(db, db_obj=product, obj_in=product_data)
            logger.info(f"Product updated: {product_id}")
            return updated_product
        except Exception as e:
            logger.error(f"Error updating product {product_id}: {e}")
            raise

    async def delete_product(
            self,
            db: AsyncSession,
            product_id: int
    ) -> bool:
        """Мягкое удаление продукта (деактивация)"""
        try:
            product = await self.crud.get(db, obj_id=product_id)
            if not product:
                return False

            # Мягкое удаление - деактивируем продукт
            product.is_active = False
            await db.commit()

            logger.info(f"Product deactivated: {product_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting product {product_id}: {e}")
            return False

    async def check_stock_availability(
            self,
            db: AsyncSession,
            product_id: int,
            quantity: int
    ) -> bool:
        """Проверка доступности товара"""
        try:
            product = await self.crud.get(db, obj_id=product_id)
            if not product or not product.is_active:
                return False

            return (product.stock_available >= quantity and
                    product.min_quantity <= quantity <= product.max_quantity)

        except Exception as e:
            logger.error(f"Error checking stock availability for product {product_id}: {e}")
            return False

    async def get_countries(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """Получение списка доступных стран"""
        try:
            countries_data = await self.crud.get_countries(db)

            # Группируем города по странам
            countries_dict = {}
            for country in countries_data:
                code = country["code"]
                name = country["name"]

                if code not in countries_dict:
                    countries_dict[code] = {
                        "code": code,
                        "name": name,
                        "cities": []
                    }

            # Получаем города для каждой страны
            for code in countries_dict.keys():
                cities = await self.crud.get_cities_by_country(db, country_code=code)
                countries_dict[code]["cities"] = cities

            return list(countries_dict.values())

        except Exception as e:
            logger.error(f"Error getting countries: {e}")
            return []

    async def get_cities_by_country(
            self,
            db: AsyncSession,
            country_code: str
    ) -> List[Dict[str, str]]:
        """Получение городов по стране"""
        try:
            cities = await self.crud.get_cities_by_country(db, country_code=country_code)

            # Получаем название страны
            countries = await self.crud.get_countries(db)
            country_name = "Unknown"
            for country in countries:
                if country["code"] == country_code:
                    country_name = country["name"]
                    break

            # Форматируем ответ
            result = []
            for city in cities:
                result.append({
                    "name": city,
                    "country_code": country_code,
                    "country_name": country_name
                })

            return result

        except Exception as e:
            logger.error(f"Error getting cities for country {country_code}: {e}")
            return []

    # Реализация абстрактных методов BaseService
    async def create(self, db: AsyncSession, obj_in: dict) -> ProxyProduct:
        return await self.crud.create(db, obj_in=obj_in)

    async def get(self, db: AsyncSession, obj_id: int) -> Optional[ProxyProduct]:
        return await self.get_product_by_id(db, obj_id)

    async def update(self, db: AsyncSession, db_obj: ProxyProduct, obj_in: dict) -> ProxyProduct:
        return await self.crud.update(db, db_obj=db_obj, obj_in=obj_in)

    async def delete(self, db: AsyncSession, obj_id: int) -> bool:
        await self.crud.remove(db, obj_id=obj_id)
        return True

    async def get_multi(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[ProxyProduct]:
        return await self.crud.get_multi(db, skip=skip, limit=limit)


# Создаем экземпляр сервиса
product_service = ProductService()
