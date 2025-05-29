import pytest
from decimal import Decimal

from app.models.models import ProxyProduct, ProxyType, ProxyCategory, SessionType, ProviderType
from app.services.cart_service import cart_service


@pytest.mark.unit
@pytest.mark.asyncio
class TestCartService:

    async def test_cart_business_rules_validation(self, db_session):
        """Тест валидации бизнес-правил корзины"""
        # Создаем продукт с обязательным proxy_category
        product = ProxyProduct(
            name="Test Product",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.DATACENTER,
            session_type=SessionType.ROTATING,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("1.50"),
            duration_days=30,
            min_quantity=1,
            max_quantity=100,
            stock_available=50,
            is_active=True
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # Тест валидации - должен пройти
        validation_data = {
            'proxy_product_id': product.id,
            'quantity': 5
        }

        result = await cart_service.business_rules.validate(validation_data, db_session)
        assert result is True
