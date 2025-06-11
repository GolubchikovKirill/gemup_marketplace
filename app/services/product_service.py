"""
Сервис для управления продуктами прокси.

Обеспечивает функциональность поиска, фильтрации и получения
информации о продуктах прокси-сервисов.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessLogicError
from app.crud.proxy_product import proxy_product_crud
from app.models.models import ProxyProduct, ProxyCategory, ProviderType
from app.schemas.proxy_product import (
    ProxyProductCreate, ProxyProductUpdate, ProductFilter,
    ProductAvailabilityRequest
)
from app.services.base import BaseService, BusinessRuleValidator

logger = logging.getLogger(__name__)


class ProductBusinessRules(BusinessRuleValidator):
    """Валидатор бизнес-правил для продуктов."""

    async def validate(self, data: Dict[str, Any], db: AsyncSession) -> bool:
        """
        Валидация бизнес-правил для продуктов.

        Args:
            data: Данные для валидации (product_id, quantity, filters)
            db: Сессия базы данных

        Returns:
            bool: Результат валидации

        Raises:
            BusinessLogicError: При нарушении бизнес-правил
        """
        try:
            # Валидация фильтров поиска
            if "filter" in data:
                filter_data = data["filter"]

                # Проверка ценовых диапазонов
                min_price = filter_data.get("min_price")
                max_price = filter_data.get("max_price")

                if min_price is not None and min_price < 0:
                    raise BusinessLogicError("Minimum price cannot be negative")

                if max_price is not None and max_price < 0:
                    raise BusinessLogicError("Maximum price cannot be negative")

                if min_price is not None and max_price is not None and min_price > max_price:
                    raise BusinessLogicError("Minimum price cannot be greater than maximum price")

                # Проверка лимитов количества
                if "limit" in filter_data:
                    limit = filter_data["limit"]
                    if limit <= 0 or limit > 100:
                        raise BusinessLogicError("Limit must be between 1 and 100")

            # Валидация параметров продукта
            if "product_id" in data:
                product_id = data["product_id"]
                if not isinstance(product_id, int) or product_id <= 0:
                    raise BusinessLogicError("Product ID must be a positive integer")

            if "quantity" in data:
                quantity = data["quantity"]
                if not isinstance(quantity, int) or quantity <= 0:
                    raise BusinessLogicError("Quantity must be a positive integer")
                if quantity > 10000:
                    raise BusinessLogicError("Quantity cannot exceed 10,000")

            logger.debug("Product business rules validation passed")
            return True

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error during product business rules validation: {e}")
            raise BusinessLogicError(f"Validation failed: {str(e)}")


def _get_country_flag_emoji(country_code: str) -> str:
    """
    Получение emoji флага страны по коду.

    Args:
        country_code: Код страны (ISO 3166-1 alpha-2)

    Returns:
        str: Emoji флага или пустая строка
    """
    try:
        if len(country_code) != 2:
            return ""

        # Преобразуем код страны в emoji флага
        return "".join(chr(ord(c) + 127397) for c in country_code.upper())
    except Exception:
        return ""


class ProductService(BaseService[ProxyProduct, ProxyProductCreate, ProxyProductUpdate]):
    """
    Сервис для управления продуктами прокси.

    Предоставляет функциональность для поиска, фильтрации
    и получения информации о продуктах прокси-сервисов.
    Включает кэширование, валидацию и интеграцию с провайдерами.
    """

    def __init__(self):
        super().__init__(ProxyProduct)
        self.crud = proxy_product_crud
        self.business_rules = ProductBusinessRules()
        self.cache_ttl = 300  # 5 минут кэша для списков продуктов

    async def get_products_with_filter(
        self,
        db: AsyncSession,
        *,
        filter_params: ProductFilter,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[ProxyProduct], int]:
        """
        Получение продуктов с применением фильтров.

        Args:
            db: Сессия базы данных
            filter_params: Параметры фильтрации
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            Tuple[List[ProxyProduct], int]: Список продуктов и общее количество

        Raises:
            BusinessLogicError: При ошибках валидации фильтров
        """
        try:
            # Валидация фильтров
            filter_dict = filter_params.model_dump() if hasattr(filter_params, 'model_dump') else filter_params.model_dump()
            validation_data = {"filter": filter_dict, "limit": limit}
            await self.business_rules.validate(validation_data, db)

            # Получение продуктов с фильтрацией
            products = await self.crud.get_products_with_filter(
                db, filter_params=filter_params, skip=skip, limit=limit
            )

            # Подсчет общего количества
            total = await self.crud.count_products_with_filter(db, filter_params=filter_params)

            logger.info(f"Retrieved {len(products)} products with filters, total: {total}")
            return products, total

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error getting products with filter: {e}")
            raise BusinessLogicError(f"Failed to get products: {str(e)}")

    async def get_product_by_id(
        self,
        db: AsyncSession,
        *,
        product_id: int,
        check_availability: bool = True
    ) -> Optional[ProxyProduct]:
        """
        Получение продукта по идентификатору.

        Args:
            db: Сессия базы данных
            product_id: Идентификатор продукта
            check_availability: Проверять ли доступность продукта

        Returns:
            Optional[ProxyProduct]: Продукт или None

        Raises:
            BusinessLogicError: При некорректном ID продукта
        """
        try:
            validation_data = {"product_id": product_id}
            await self.business_rules.validate(validation_data, db)

            product = await self.crud.get(db, id=product_id)

            if product and check_availability and not product.is_active:
                logger.warning(f"Requested inactive product: {product_id}")
                return None

            return product

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error getting product by ID {product_id}: {e}")
            return None

    async def check_product_availability(
        self,
        db: AsyncSession,
        *,
        product_id: int,
        quantity: int
    ) -> Dict[str, Any]:
        """
        Проверка доступности продукта в указанном количестве.

        Args:
            db: Сессия базы данных
            product_id: Идентификатор продукта
            quantity: Требуемое количество

        Returns:
            Dict[str, Any]: Информация о доступности

        Raises:
            BusinessLogicError: При ошибках валидации
        """
        try:
            validation_data = {"product_id": product_id, "quantity": quantity}
            await self.business_rules.validate(validation_data, db)

            # Используем CRUD метод для проверки доступности
            availability_request = ProductAvailabilityRequest(
                product_id=product_id,
                quantity=quantity
            )

            return await self.crud.check_product_availability(
                db, availability_request=availability_request
            )

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error checking product availability: {e}")
            return {
                "product_id": product_id,
                "requested_quantity": quantity,
                "is_available": False,
                "stock_available": 0,
                "max_quantity": 0,
                "price_per_unit": "0.00000000",
                "total_price": "0.00000000",
                "currency": "USD",
                "message": "Error checking availability"
            }

    async def get_products_by_category(
        self,
        db: AsyncSession,
        *,
        category: ProxyCategory,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[ProxyProduct], int]:
        """
        Получение продуктов по категории.

        Args:
            db: Сессия базы данных
            category: Категория прокси
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            Tuple[List[ProxyProduct], int]: Список продуктов и общее количество
        """
        try:
            products = await self.crud.get_products_by_category(
                db, category=category, skip=skip, limit=limit
            )

            total = await self.crud.count_products_by_category(db, category=category)

            return products, total

        except Exception as e:
            logger.error(f"Error getting products by category {category}: {e}")
            return [], 0

    async def get_categories_with_stats(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """
        Получение категорий с статистикой продуктов.

        Args:
            db: Сессия базы данных

        Returns:
            List[Dict[str, Any]]: Список категорий со статистикой
        """
        try:
            categories_data = []

            for category in ProxyCategory:
                count = await self.crud.count_products_by_category(db, category=category)

                # Получаем несколько продуктов для демонстрации
                sample_products = await self.crud.get_products_by_category(
                    db, category=category, skip=0, limit=3
                )

                # Рассчитываем ценовой диапазон
                price_range = {"min": None, "max": None}
                avg_price = "0.00"
                if sample_products:
                    prices = [p.price_per_proxy for p in sample_products]
                    price_range = {"min": str(min(prices)), "max": str(max(prices))}
                    avg_price = str(sum(prices) / len(prices))

                categories_data.append({
                    "category": category,
                    "category_name": category.value.replace('_', ' ').title(),
                    "products_count": count,
                    "price_range": price_range,
                    "avg_price": avg_price,
                    "sample_products": [
                        {
                            "id": p.id,
                            "name": p.name,
                            "price_per_proxy": str(p.price_per_proxy),
                            "country_name": p.country_name,
                            "is_featured": p.is_featured
                        }
                        for p in sample_products[:2]  # Показываем только 2 примера
                    ]
                })

            # Сортируем по количеству продуктов
            categories_data.sort(key=lambda x: x["products_count"], reverse=True)

            return categories_data

        except Exception as e:
            logger.error(f"Error getting categories with stats: {e}")
            return []

    async def get_available_countries(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """
        Получение списка доступных стран для прокси.

        Args:
            db: Сессия базы данных

        Returns:
            List[Dict[str, Any]]: Список стран с дополнительной информацией
        """
        try:
            countries = await self.crud.get_available_countries(db)

            countries_data = []
            for country in countries:
                countries_data.append({
                    "code": country.country_code,
                    "name": country.country_name,
                    "products_count": country.products_count,
                    "flag_emoji": _get_country_flag_emoji(country.country_code),
                    "price_range": None  # Можно добавить расчет ценового диапазона
                })

            # Сортируем по количеству продуктов
            countries_data.sort(key=lambda x: x["products_count"], reverse=True)

            return countries_data

        except Exception as e:
            logger.error(f"Error getting available countries: {e}")
            return []

    async def get_featured_products(
        self,
        db: AsyncSession,
        *,
        category: Optional[ProxyCategory] = None,
        limit: int = 5
    ) -> List[ProxyProduct]:
        """
        Получение рекомендуемых продуктов.

        Args:
            db: Сессия базы данных
            category: Фильтр по категории (опционально)
            limit: Максимальное количество продуктов

        Returns:
            List[ProxyProduct]: Список рекомендуемых продуктов
        """
        try:
            return await self.crud.get_featured_products(db, limit=limit, category=category)

        except Exception as e:
            logger.error(f"Error getting featured products: {e}")
            return []

    async def search_products(
        self,
        db: AsyncSession,
        *,
        search_term: str,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[ProxyProduct], str]:
        """
        Поиск продуктов по ключевому слову.

        Args:
            db: Сессия базы данных
            search_term: Поисковый запрос
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            Tuple[List[ProxyProduct], str]: Результаты поиска и обработанный термин

        Raises:
            BusinessLogicError: При некорректном поисковом запросе
        """
        try:
            # Валидация поискового запроса
            if not search_term or len(search_term.strip()) < 2:
                raise BusinessLogicError("Search term must be at least 2 characters long")

            if len(search_term) > 100:
                raise BusinessLogicError("Search term is too long")

            processed_term = search_term.strip().lower()

            products = await self.crud.search_products(
                db, search_term=processed_term, skip=skip, limit=limit
            )

            return products, processed_term

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error searching products: {e}")
            return [], search_term

    async def get_products_by_provider(
        self,
        db: AsyncSession,
        *,
        provider: ProviderType,
        skip: int = 0,
        limit: int = 20
    ) -> List[ProxyProduct]:
        """
        Получение продуктов по провайдеру.

        Args:
            db: Сессия базы данных
            provider: Провайдер прокси
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            List[ProxyProduct]: Список продуктов провайдера
        """
        try:
            return await self.crud.get_products_by_provider(
                db, provider=provider, skip=skip, limit=limit
            )

        except Exception as e:
            logger.error(f"Error getting products by provider {provider}: {e}")
            return []

    async def get_product_recommendations(
        self,
        db: AsyncSession,
        *,
        product_id: int,
        limit: int = 5
    ) -> List[ProxyProduct]:
        """
        Получение рекомендованных продуктов на основе выбранного.

        Args:
            db: Сессия базы данных
            product_id: ID продукта для рекомендаций
            limit: Максимальное количество рекомендаций

        Returns:
            List[ProxyProduct]: Список рекомендованных продуктов
        """
        try:
            base_product = await self.crud.get(db, id=product_id)
            if not base_product:
                return []

            # Ищем похожие продукты по категории и стране
            filter_params = ProductFilter(
                proxy_category=base_product.proxy_category,
                country_code=base_product.country_code
            )

            similar_products = await self.crud.get_products_with_filter(
                db, filter_params=filter_params, skip=0, limit=limit + 1
            )

            # Исключаем исходный продукт
            recommendations = [p for p in similar_products if p.id != product_id][:limit]

            return recommendations

        except Exception as e:
            logger.error(f"Error getting product recommendations: {e}")
            return []

    async def get_product_statistics(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Получение общей статистики продуктов.

        Args:
            db: Сессия базы данных

        Returns:
            Dict[str, Any]: Статистика продуктов
        """
        try:
            return await self.crud.get_products_stats(db)

        except Exception as e:
            logger.error(f"Error getting product statistics: {e}")
            return {
                "total_products": 0,
                "active_products": 0,
                "featured_products": 0,
                "total_stock": 0,
                "average_price": "0.00",
                "countries_available": 0,
                "categories_breakdown": {},
                "providers_breakdown": {}
            }

    async def update_product_stock(
        self,
        db: AsyncSession,
        *,
        product_id: int,
        stock_change: int
    ) -> Optional[ProxyProduct]:
        """
        Обновление остатков продукта.

        Args:
            db: Сессия базы данных
            product_id: ID продукта
            stock_change: Изменение остатка

        Returns:
            Optional[ProxyProduct]: Обновленный продукт или None

        Raises:
            BusinessLogicError: При некорректных параметрах
        """
        try:
            validation_data = {"product_id": product_id}
            await self.business_rules.validate(validation_data, db)

            return await self.crud.update_stock(
                db, product_id=product_id, stock_change=stock_change
            )

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error updating product stock: {e}")
            return None

    # Реализация абстрактных методов BaseService
    async def create(self, db: AsyncSession, *, obj_in: ProxyProductCreate) -> ProxyProduct:
        return await self.crud.create(db, obj_in=obj_in)

    async def get(self, db: AsyncSession, *, id: int) -> Optional[ProxyProduct]:
        return await self.crud.get(db, id=id)

    async def update(self, db: AsyncSession, *, db_obj: ProxyProduct, obj_in: ProxyProductUpdate) -> ProxyProduct:
        return await self.crud.update(db, db_obj=db_obj, obj_in=obj_in)

    async def delete(self, db: AsyncSession, *, id: int) -> bool:
        result = await self.crud.delete(db, id=id)
        return result is not None

    async def get_multi(self, db: AsyncSession, *, skip: int = 0, limit: int = 100) -> List[ProxyProduct]:
        return await self.crud.get_multi(db, skip=skip, limit=limit)


product_service = ProductService()
