import logging
from typing import List, Optional, Tuple

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ProductNotAvailableError, BusinessLogicError
from app.crud.proxy_product import proxy_product_crud
from app.models.models import ProxyProduct
from app.schemas.product import ProductCreate, ProductUpdate, ProductFilter

logger = logging.getLogger(__name__)


class ProductService:
    """Сервис для работы с продуктами"""

    def __init__(self):
        self.crud = proxy_product_crud

    @staticmethod
    async def get_products_with_filters(
            db: AsyncSession,
            filters: ProductFilter,
            page: int = 1,
            size: int = 20
    ) -> Tuple[List[ProxyProduct], int]:
        """Получение продуктов с фильтрами и пагинацией"""

        # Базовый запрос
        query = select(ProxyProduct)
        count_query = select(func.count(ProxyProduct.id))

        # Применяем фильтры
        conditions = []

        if filters.proxy_type:
            conditions.append(ProxyProduct.proxy_type == filters.proxy_type)

        if filters.session_type:
            conditions.append(ProxyProduct.session_type == filters.session_type)

        if filters.provider:
            conditions.append(ProxyProduct.provider == filters.provider)

        if filters.country_code:
            conditions.append(ProxyProduct.country_code == filters.country_code.upper())

        if filters.city:
            conditions.append(ProxyProduct.city.ilike(f"%{filters.city}%"))

        if filters.min_price:
            conditions.append(ProxyProduct.price_per_proxy >= filters.min_price)

        if filters.max_price:
            conditions.append(ProxyProduct.price_per_proxy <= filters.max_price)

        if filters.min_duration:
            conditions.append(ProxyProduct.duration_days >= filters.min_duration)

        if filters.max_duration:
            conditions.append(ProxyProduct.duration_days <= filters.max_duration)

        if filters.is_active is not None:
            conditions.append(ProxyProduct.is_active == filters.is_active)

        if filters.is_featured is not None:
            conditions.append(ProxyProduct.is_featured == filters.is_featured)

        if filters.search:
            search_term = f"%{filters.search}%"
            conditions.append(
                or_(
                    ProxyProduct.name.ilike(search_term),
                    ProxyProduct.description.ilike(search_term)
                )
            )

        # Применяем условия к запросам
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        # Добавляем сортировку
        query = query.order_by(
            ProxyProduct.is_featured.desc(),
            ProxyProduct.created_at.desc()
        )

        # Пагинация
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)

        # Выполняем запросы
        result = await db.execute(query)
        products = result.scalars().all()

        count_result = await db.execute(count_query)
        total = count_result.scalar()

        logger.info(f"Found {len(products)} products with filters: {filters}")

        return products, total

    async def get_product_by_id(
            self,
            db: AsyncSession,
            product_id: int
    ) -> Optional[ProxyProduct]:
        """Получение продукта по ID"""
        product = await self.crud.get(db, id=product_id)

        if not product:
            logger.warning(f"Product {product_id} not found")
            return None

        if not product.is_active:
            logger.warning(f"Product {product_id} is inactive")
            raise ProductNotAvailableError(f"Product {product_id} is not available")

        return product

    async def create_product(
            self,
            db: AsyncSession,
            product_data: ProductCreate
    ) -> ProxyProduct:
        """Создание нового продукта"""

        # Валидация бизнес-правил
        await self._validate_product_data(product_data)

        try:
            product = await self.crud.create(db, obj_in=product_data)
            logger.info(f"Created new product: {product.name} (ID: {product.id})")
            return product

        except Exception as e:
            logger.error(f"Error creating product: {e}")
            raise BusinessLogicError("Failed to create product")

    async def update_product(
            self,
            db: AsyncSession,
            product_id: int,
            product_data: ProductUpdate
    ) -> Optional[ProxyProduct]:
        """Обновление продукта"""

        product = await self.crud.get(db, id=product_id)
        if not product:
            return None

        try:
            updated_product = await self.crud.update(db, db_obj=product, obj_in=product_data)
            logger.info(f"Updated product: {product.name} (ID: {product.id})")
            return updated_product

        except Exception as e:
            logger.error(f"Error updating product {product_id}: {e}")
            raise BusinessLogicError("Failed to update product")

    async def delete_product(
            self,
            db: AsyncSession,
            product_id: int
    ) -> bool:
        """Удаление продукта (мягкое удаление)"""

        product = await self.crud.get(db, id=product_id)
        if not product:
            return False

        try:
            # Мягкое удаление - деактивация
            await self.crud.update(db, db_obj=product, obj_in={"is_active": False})
            logger.info(f"Deactivated product: {product.name} (ID: {product.id})")
            return True

        except Exception as e:
            logger.error(f"Error deactivating product {product_id}: {e}")
            raise BusinessLogicError("Failed to delete product")

    @staticmethod
    async def get_countries(db: AsyncSession) -> List[dict]:
        """Получение списка стран с городами"""

        query = select(
            ProxyProduct.country_code,
            ProxyProduct.country_name,
            func.array_agg(ProxyProduct.city.distinct()).label('cities')
        ).where(
            and_(
                ProxyProduct.is_active == True,
                ProxyProduct.city.isnot(None)
            )
        ).group_by(
            ProxyProduct.country_code,
            ProxyProduct.country_name
        ).order_by(ProxyProduct.country_name)

        result = await db.execute(query)
        countries = []

        for row in result:
            cities = [city for city in row.cities if city] if row.cities else []
            countries.append({
                "code": row.country_code,
                "name": row.country_name,
                "cities": sorted(cities)
            })

        return countries

    @staticmethod
    async def get_cities_by_country(
            db: AsyncSession,
            country_code: str
    ) -> List[dict]:
        """Получение городов по стране"""

        query = select(
            ProxyProduct.city,
            ProxyProduct.country_code,
            ProxyProduct.country_name
        ).where(
            and_(
                ProxyProduct.country_code == country_code.upper(),
                ProxyProduct.is_active == True,
                ProxyProduct.city.isnot(None)
            )
        ).distinct().order_by(ProxyProduct.city)

        result = await db.execute(query)
        cities = []

        for row in result:
            cities.append({
                "name": row.city,
                "country_code": row.country_code,
                "country_name": row.country_name
            })

        return cities

    async def check_stock_availability(
            self,
            db: AsyncSession,
            product_id: int,
            quantity: int
    ) -> bool:
        """Проверка доступности товара"""

        product = await self.crud.get(db, id=product_id)
        if not product:
            return False

        if not product.is_active:
            return False

        if product.stock_available < quantity:
            return False

        if quantity < product.min_quantity or quantity > product.max_quantity:
            return False

        return True

    @staticmethod
    async def _validate_product_data(product_data: ProductCreate) -> None:
        """Валидация данных продукта"""

        if product_data.min_quantity > product_data.max_quantity:
            raise BusinessLogicError("Minimum quantity cannot be greater than maximum quantity")

        if product_data.price_per_proxy <= 0:
            raise BusinessLogicError("Price must be greater than zero")

        if product_data.duration_days <= 0:
            raise BusinessLogicError("Duration must be greater than zero")


# Создаем экземпляр сервиса
product_service = ProductService()
