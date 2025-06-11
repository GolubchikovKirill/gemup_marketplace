"""
Unit тесты для сервиса корзины.

Тестирует бизнес-логику добавления товаров в корзину,
расчета стоимости и валидации правил.
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import BusinessLogicError
from app.models.models import (
    ProxyProduct, ProxyType, ProxyCategory, SessionType, ProviderType,
    ShoppingCart
)
from app.services.cart_service import cart_service, CartBusinessRules


@pytest.mark.unit
@pytest.mark.asyncio
class TestCartBusinessRules:
    """Тесты валидации бизнес-правил корзины."""

    async def test_validate_success(self, db_session):
        """Тест успешной валидации."""
        # Создаем продукт
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

        rules = CartBusinessRules()
        validation_data = {
            'product_id': product.id,
            'quantity': 5
        }

        result = await rules.validate(validation_data, db_session)
        assert result is True

    async def test_validate_missing_product_id(self, db_session):
        """Тест валидации без product_id."""
        rules = CartBusinessRules()
        validation_data = {'quantity': 5}

        with pytest.raises(BusinessLogicError, match="Product ID is required"):
            await rules.validate(validation_data, db_session)

    async def test_validate_zero_quantity(self, db_session):
        """Тест валидации с нулевым количеством."""
        rules = CartBusinessRules()
        validation_data = {
            'product_id': 1,
            'quantity': 0
        }

        with pytest.raises(BusinessLogicError, match="Quantity must be positive"):
            await rules.validate(validation_data, db_session)

    async def test_validate_excessive_quantity(self, db_session):
        """Тест валидации с превышением максимального количества."""
        rules = CartBusinessRules()
        validation_data = {
            'product_id': 1,
            'quantity': 1001
        }

        with pytest.raises(BusinessLogicError, match="Quantity cannot exceed 1000"):
            await rules.validate(validation_data, db_session)

    async def test_validate_product_not_found(self, db_session):
        """Тест валидации с несуществующим продуктом."""
        rules = CartBusinessRules()
        validation_data = {
            'product_id': 99999,
            'quantity': 5
        }

        with pytest.raises(BusinessLogicError, match="Product not found"):
            await rules.validate(validation_data, db_session)

    async def test_validate_inactive_product(self, db_session):
        """Тест валидации с неактивным продуктом."""
        product = ProxyProduct(
            name="Inactive Product",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.DATACENTER,
            session_type=SessionType.ROTATING,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("1.50"),
            duration_days=30,
            stock_available=50,
            is_active=False  # Неактивный продукт
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        rules = CartBusinessRules()
        validation_data = {
            'product_id': product.id,
            'quantity': 5
        }

        with pytest.raises(BusinessLogicError, match="Product is not available"):
            await rules.validate(validation_data, db_session)

    async def test_validate_insufficient_stock(self, db_session):
        """Тест валидации с недостаточным количеством на складе."""
        product = ProxyProduct(
            name="Low Stock Product",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.DATACENTER,
            session_type=SessionType.ROTATING,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("1.50"),
            duration_days=30,
            stock_available=3,  # Мало на складе
            is_active=True
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        rules = CartBusinessRules()
        validation_data = {
            'product_id': product.id,
            'quantity': 5  # Больше чем на складе
        }

        with pytest.raises(BusinessLogicError, match="Only 3 items available"):
            await rules.validate(validation_data, db_session)


@pytest.mark.unit
@pytest.mark.asyncio
class TestCartService:
    """Тесты сервиса корзины."""

    async def test_get_user_cart_empty(self, db_session, test_user):
        """Тест получения пустой корзины."""
        cart_items = await cart_service.get_user_cart(
            db_session, user_id=test_user.id
        )

        assert isinstance(cart_items, list)
        assert len(cart_items) == 0

    async def test_get_user_cart_with_items(self, db_session, test_user, test_proxy_product):
        """Тест получения корзины с товарами."""
        # Добавляем товар в корзину
        cart_item = ShoppingCart(
            user_id=test_user.id,
            proxy_product_id=test_proxy_product.id,
            quantity=3,
            generation_params='{"format": "ip:port"}'
        )
        db_session.add(cart_item)
        await db_session.commit()

        cart_items = await cart_service.get_user_cart(
            db_session, user_id=test_user.id
        )

        assert len(cart_items) == 1
        assert cart_items[0].quantity == 3

    async def test_get_guest_cart(self, db_session, test_guest_user, test_proxy_product):
        """Тест получения гостевой корзины."""
        # Добавляем товар в гостевую корзину
        cart_item = ShoppingCart(
            guest_session_id=test_guest_user.guest_session_id,
            proxy_product_id=test_proxy_product.id,
            quantity=2
        )
        db_session.add(cart_item)
        await db_session.commit()

        cart_items = await cart_service.get_user_cart(
            db_session, session_id=test_guest_user.guest_session_id
        )

        assert len(cart_items) == 1
        assert cart_items[0].quantity == 2

    async def test_calculate_cart_total_empty(self, db_session, test_user):
        """Тест расчета итога пустой корзины."""
        total = await cart_service.calculate_cart_total(
            db_session, user_id=test_user.id
        )

        assert total["total_items"] == 0
        assert total["total_amount"] == "0.00"
        assert total["items"] == []

    async def test_calculate_cart_total_with_items(self, db_session, test_user, test_proxy_product):
        """Тест расчета итога корзины с товарами."""
        # Добавляем товар в корзину
        cart_item = ShoppingCart(
            user_id=test_user.id,
            proxy_product_id=test_proxy_product.id,
            quantity=5
        )
        db_session.add(cart_item)
        await db_session.commit()

        total = await cart_service.calculate_cart_total(
            db_session, user_id=test_user.id
        )

        expected_amount = str(test_proxy_product.price_per_proxy * 5)
        assert total["total_items"] == 5
        assert total["total_amount"] == expected_amount
        assert len(total["items"]) == 1

    @patch.object(cart_service, 'business_rules')
    async def test_add_item_to_cart_success(self, mock_rules, db_session, test_user, test_proxy_product):
        """Тест успешного добавления товара в корзину."""
        mock_rules.validate.return_value = True

        with patch.object(cart_service.crud, 'add_to_cart') as mock_add:
            mock_cart_item = MagicMock()
            mock_cart_item.id = 1
            mock_cart_item.proxy_product_id = test_proxy_product.id
            mock_cart_item.quantity = 3
            mock_add.return_value = mock_cart_item

            result = await cart_service.add_item_to_cart(
                db_session,
                product_id=test_proxy_product.id,
                quantity=3,
                user_id=test_user.id
            )

            assert result == mock_cart_item
            mock_rules.validate.assert_called_once()
            mock_add.assert_called_once()

    @patch.object(cart_service, 'business_rules')
    async def test_add_item_to_cart_validation_failure(self, mock_rules, db_session, test_user, test_proxy_product):
        """Тест добавления товара с ошибкой валидации."""
        mock_rules.validate.side_effect = BusinessLogicError("Invalid quantity")

        with pytest.raises(BusinessLogicError, match="Invalid quantity"):
            await cart_service.add_item_to_cart(
                db_session,
                product_id=test_proxy_product.id,
                quantity=1001,
                user_id=test_user.id
            )

    async def test_add_item_cart_limit_exceeded(self, db_session, test_user):
        """Тест превышения лимита товаров в корзине."""
        # Создаем много продуктов и добавляем их в корзину
        products = []
        for i in range(cart_service.max_cart_items + 1):
            product = ProxyProduct(
                name=f"Product {i}",
                proxy_type=ProxyType.HTTP,
                proxy_category=ProxyCategory.DATACENTER,
                session_type=SessionType.ROTATING,
                provider=ProviderType.PROVIDER_711,
                country_code="US",
                country_name="United States",
                price_per_proxy=Decimal("1.00"),
                duration_days=30,
                stock_available=10,
                is_active=True
            )
            db_session.add(product)
            products.append(product)

        await db_session.commit()

        # Добавляем максимальное количество товаров
        for i in range(cart_service.max_cart_items):
            await db_session.refresh(products[i])
            cart_item = ShoppingCart(
                user_id=test_user.id,
                proxy_product_id=products[i].id,
                quantity=1
            )
            db_session.add(cart_item)

        await db_session.commit()

        # Пытаемся добавить еще один товар
        await db_session.refresh(products[-1])
        with pytest.raises(BusinessLogicError, match="Cart cannot contain more than"):
            await cart_service.add_item_to_cart(
                db_session,
                product_id=products[-1].id,
                quantity=1,
                user_id=test_user.id
            )

    async def test_update_cart_item_quantity(self, db_session, test_user, test_proxy_product):
        """Тест обновления количества товара в корзине."""
        # Добавляем товар в корзину
        cart_item = ShoppingCart(
            user_id=test_user.id,
            proxy_product_id=test_proxy_product.id,
            quantity=2
        )
        db_session.add(cart_item)
        await db_session.commit()
        await db_session.refresh(cart_item)

        with patch.object(cart_service.crud, 'update_cart_item_quantity') as mock_update:
            mock_update.return_value = cart_item

            result = await cart_service.update_cart_item_quantity(
                db_session, cart_item.id, 5, test_user.id
            )

            assert result == cart_item
            mock_update.assert_called_once_with(
                db_session, cart_item_id=cart_item.id, new_quantity=5,
                user_id=test_user.id, session_id=None
            )

    async def test_remove_cart_item(self, db_session, test_user, test_proxy_product):
        """Тест удаления товара из корзины."""
        # Добавляем товар в корзину
        cart_item = ShoppingCart(
            user_id=test_user.id,
            proxy_product_id=test_proxy_product.id,
            quantity=1
        )
        db_session.add(cart_item)
        await db_session.commit()
        await db_session.refresh(cart_item)

        with patch.object(cart_service.crud, 'remove_cart_item') as mock_remove:
            mock_remove.return_value = True

            result = await cart_service.remove_cart_item(
                db_session, cart_item.id, test_user.id
            )

            assert result is True
            mock_remove.assert_called_once()

    async def test_clear_cart(self, db_session, test_user, test_proxy_product):
        """Тест очистки корзины."""
        # Добавляем товары в корзину
        for i in range(3):
            cart_item = ShoppingCart(
                user_id=test_user.id,
                proxy_product_id=test_proxy_product.id,
                quantity=1
            )
            db_session.add(cart_item)
        await db_session.commit()

        with patch.object(cart_service.crud, 'clear_user_cart') as mock_clear:
            mock_clear.return_value = True

            result = await cart_service.clear_cart(
                db_session, user_id=test_user.id
            )

            assert result is True
            mock_clear.assert_called_once_with(db_session, user_id=test_user.id)

    async def test_validate_cart_before_checkout_empty(self, db_session, test_user):
        """Тест валидации пустой корзины перед оформлением."""
        with pytest.raises(BusinessLogicError, match="Cart is empty"):
            await cart_service.validate_cart_before_checkout(
                db_session, user_id=test_user.id
            )

    async def test_validate_cart_before_checkout_success(self, db_session, test_user, test_proxy_product):
        """Тест успешной валидации корзины."""
        # Добавляем товар в корзину
        cart_item = ShoppingCart(
            user_id=test_user.id,
            proxy_product_id=test_proxy_product.id,
            quantity=2
        )
        db_session.add(cart_item)
        await db_session.commit()

        result = await cart_service.validate_cart_before_checkout(
            db_session, user_id=test_user.id
        )

        assert result["is_valid"] is True
        assert len(result["errors"]) == 0

    async def test_validate_cart_inactive_product(self, db_session, test_user):
        """Тест валидации корзины с неактивным продуктом."""
        # Создаем неактивный продукт
        product = ProxyProduct(
            name="Inactive Product",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.DATACENTER,
            session_type=SessionType.ROTATING,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("1.00"),
            duration_days=30,
            stock_available=10,
            is_active=False  # Неактивный
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # Добавляем в корзину
        cart_item = ShoppingCart(
            user_id=test_user.id,
            proxy_product_id=product.id,
            quantity=1
        )
        db_session.add(cart_item)
        await db_session.commit()

        result = await cart_service.validate_cart_before_checkout(
            db_session, user_id=test_user.id
        )

        assert result["is_valid"] is False
        assert len(result["errors"]) > 0
        assert "no longer available" in result["errors"][0]

    async def test_get_cart_summary(self, db_session, test_user, test_proxy_product):
        """Тест получения краткой сводки корзины."""
        # Добавляем товары в корзину
        cart_item = ShoppingCart(
            user_id=test_user.id,
            proxy_product_id=test_proxy_product.id,
            quantity=3
        )
        db_session.add(cart_item)
        await db_session.commit()

        summary = await cart_service.get_cart_summary(
            db_session, user_id=test_user.id
        )

        assert summary["items_count"] == 1
        assert summary["total_quantity"] == 3
        assert summary["currency"] == "USD"

    async def test_merge_guest_cart_to_user(self, db_session, test_user, test_guest_user, test_proxy_product):
        """Тест объединения гостевой корзины с пользователем."""
        # Добавляем товар в гостевую корзину
        cart_item = ShoppingCart(
            guest_session_id=test_guest_user.guest_session_id,
            proxy_product_id=test_proxy_product.id,
            quantity=2
        )
        db_session.add(cart_item)
        await db_session.commit()

        with patch.object(cart_service.crud, 'merge_guest_cart_to_user') as mock_merge:
            mock_merge.return_value = True

            result = await cart_service.merge_guest_cart_to_user(
                db_session,
                session_id=test_guest_user.guest_session_id,
                user_id=test_user.id
            )

            assert result is True
            mock_merge.assert_called_once()
