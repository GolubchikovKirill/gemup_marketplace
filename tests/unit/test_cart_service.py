from decimal import Decimal

import pytest

from app.models.models import ProxyProduct, ProxyType, SessionType, ProviderType
from app.services.cart_service import cart_service


@pytest.mark.unit
@pytest.mark.asyncio
class TestCartService:

    async def test_cart_business_rules_validation(self, db_session):
        """Тест валидации бизнес-правил корзины"""
        # Создаем продукт
        product = ProxyProduct(
            name="Test Product",
            proxy_type=ProxyType.HTTP,
            session_type=SessionType.ROTATING,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("1.50"),
            duration_days=30,
            min_quantity=1,
            max_quantity=100,
            stock_available=50
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # Тест валидации количества
        validator = cart_service.business_rules

        # Валидное количество
        result = await validator.validate({
            'product_id': product.id,
            'quantity': 5
        }, db_session)
        assert result == True

        # Слишком большое количество
        with pytest.raises(Exception):
            await validator.validate({
                'product_id': product.id,
                'quantity': 200  # Больше max_quantity
            }, db_session)
