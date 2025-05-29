import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest

from app.core.exceptions import BusinessLogicError
from app.models.models import (
    ProxyProduct, ProxyType, ProxyCategory, SessionType, ProviderType,
    Order, OrderStatus
)
from app.services.proxy_service import proxy_service, ProxyBusinessRules


@pytest.mark.unit
@pytest.mark.asyncio
class TestProxyService:

    async def test_proxy_business_rules_valid(self, db_session):
        """Тест валидации бизнес-правил - успешный случай"""
        validator = ProxyBusinessRules()

        result = await validator.validate({}, db_session)
        assert result is True

    @patch('app.services.proxy_service.proxy_711_api.purchase_proxies')
    async def test_activate_proxies_for_order_success(self, mock_purchase, db_session, test_user):
        """Тест успешной активации прокси для заказа"""
        unique_id = str(uuid.uuid4())[:8]

        # Создаем продукт с обязательным proxy_category
        product = ProxyProduct(
            name="Test Proxy Product",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.DATACENTER,
            session_type=SessionType.STICKY,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("2.00"),
            duration_days=30,
            min_quantity=1,
            max_quantity=100,
            stock_available=100,
            is_active=True
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # Создаем заказ с уникальным номером
        from app.models.models import OrderItem
        order = Order(
            order_number=f"ORD-PROXY-{unique_id}",
            user_id=test_user.id,
            total_amount=Decimal("4.00"),
            status=OrderStatus.PAID
        )
        db_session.add(order)
        await db_session.commit()
        await db_session.refresh(order)

        # Создаем элемент заказа
        order_item = OrderItem(
            order_id=order.id,
            proxy_product_id=product.id,
            quantity=2,
            unit_price=Decimal("2.00"),
            total_price=Decimal("4.00")
        )
        db_session.add(order_item)
        await db_session.commit()

        # Загружаем заказ с элементами
        await db_session.refresh(order)
        order.order_items = [order_item]

        # Мокаем ответ от 711 API
        mock_purchase.return_value = {
            "order_id": "711-order-123",
            "proxies": ["1.2.3.4:8080", "5.6.7.8:8080"],
            "username": "user123",
            "password": "pass123"
        }

        # Активируем прокси
        activated_proxies = await proxy_service.activate_proxies_for_order(db_session, order)

        assert len(activated_proxies) == 1
        assert activated_proxies[0].user_id == test_user.id
        assert activated_proxies[0].order_id == order.id

    async def test_get_user_proxies(self, db_session, test_user):
        """Тест получения прокси пользователя"""
        proxies = await proxy_service.get_user_proxies(db_session, test_user)
        assert isinstance(proxies, list)

    async def test_format_proxy_list_ip_port_user_pass(self):
        """Тест форматирования прокси в формате ip:port:user:pass"""
        proxy_list = "1.2.3.4:8080\n5.6.7.8:8080"
        username = "user123"
        password = "pass123"

        formatted = proxy_service._format_proxy_list(
            proxy_list, username, password, "ip:port:user:pass"
        )

        assert formatted[0] == "1.2.3.4:8080:user123:pass123"
        assert formatted[1] == "5.6.7.8:8080:user123:pass123"

    async def test_format_proxy_list_user_pass_at_ip_port(self):
        """Тест форматирования прокси в формате user:pass@ip:port"""
        proxy_list = "1.2.3.4:8080\n5.6.7.8:8080"
        username = "user123"
        password = "pass123"

        formatted = proxy_service._format_proxy_list(
            proxy_list, username, password, "user:pass@ip:port"
        )

        assert formatted[0] == "user123:pass123@1.2.3.4:8080"
        assert formatted[1] == "user123:pass123@5.6.7.8:8080"

    async def test_format_proxy_list_ip_port_only(self):
        """Тест форматирования прокси в формате ip:port"""
        proxy_list = "1.2.3.4:8080\n5.6.7.8:8080"
        username = "user123"
        password = "pass123"

        formatted = proxy_service._format_proxy_list(
            proxy_list, username, password, "ip:port"
        )

        assert formatted[0] == "1.2.3.4:8080"
        assert formatted[1] == "5.6.7.8:8080"

    async def test_generate_proxy_list_not_found(self, db_session, test_user):
        """Тест генерации списка для несуществующей покупки"""
        with pytest.raises(BusinessLogicError, match="Proxy purchase not found"):
            await proxy_service.generate_proxy_list(
                db_session,
                purchase_id=99999,
                user=test_user,
                format_type="ip:port:user:pass"
            )
