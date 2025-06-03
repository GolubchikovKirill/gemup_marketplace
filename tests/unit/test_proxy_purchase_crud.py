"""
Unit тесты для CRUD операций покупок прокси.

Тестирует создание, получение, обновление и поиск покупок прокси,
управление статусами и проверку сроков действия.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.crud.proxy_purchase import proxy_purchase_crud


@pytest.mark.unit
@pytest.mark.asyncio
class TestProxyPurchaseCRUD:
    """Тесты CRUD операций покупок прокси."""

    async def test_create_purchase_success(self, db_session, test_user, test_proxy_product, test_order):
        """Тест успешного создания покупки прокси."""
        expires_at = datetime.now() + timedelta(days=30)

        purchase = await proxy_purchase_crud.create_purchase(
            db_session,
            user_id=test_user.id,
            proxy_product_id=test_proxy_product.id,
            order_id=test_order.id,
            proxy_list="192.168.1.1:8080:user:pass\n192.168.1.2:8080:user:pass",
            username="testuser",
            password="testpass",
            expires_at=expires_at,
            provider_order_id="711_order_123"
        )

        assert purchase.user_id == test_user.id
        assert purchase.proxy_product_id == test_proxy_product.id
        assert purchase.order_id == test_order.id
        assert "192.168.1.1:8080" in purchase.proxy_list
        assert purchase.username == "testuser"
        assert purchase.password == "testpass"
        assert purchase.is_active is True
        assert purchase.provider_order_id == "711_order_123"
        assert purchase.expires_at > datetime.now()

    async def test_create_purchase_with_proxy_list_array(self, db_session, test_user, test_proxy_product, test_order):
        """Тест создания покупки со списком прокси как массивом."""
        expires_at = datetime.now() + timedelta(days=30)
        proxy_list = [
            "203.0.113.1:8080:user:pass",
            "203.0.113.2:8080:user:pass",
            "203.0.113.3:8080:user:pass"
        ]

        purchase = await proxy_purchase_crud.create_purchase(
            db_session,
            user_id=test_user.id,
            proxy_product_id=test_proxy_product.id,
            order_id=test_order.id,
            proxy_list=proxy_list,
            expires_at=expires_at
        )

        expected_proxy_string = "\n".join(proxy_list)
        assert purchase.proxy_list == expected_proxy_string
        assert purchase.is_active is True

    async def test_get_purchase_by_id(self, db_session, test_proxy_purchase):
        """Тест получения покупки по ID."""
        found_purchase = await proxy_purchase_crud.get(db_session, obj_id=test_proxy_purchase.id)

        assert found_purchase is not None
        assert found_purchase.id == test_proxy_purchase.id
        assert found_purchase.user_id == test_proxy_purchase.user_id

    async def test_get_purchase_by_id_not_found(self, db_session):
        """Тест получения несуществующей покупки."""
        found_purchase = await proxy_purchase_crud.get(db_session, obj_id=99999)

        assert found_purchase is None

    async def test_get_user_purchase(self, db_session, test_user, test_proxy_purchase):
        """Тест получения покупки пользователя с проверкой доступа."""
        found_purchase = await proxy_purchase_crud.get_user_purchase(
            db_session,
            purchase_id=test_proxy_purchase.id,
            user_id=test_user.id
        )

        assert found_purchase is not None
        assert found_purchase.id == test_proxy_purchase.id
        assert found_purchase.user_id == test_user.id

    async def test_get_user_purchase_wrong_user(self, db_session, test_proxy_purchase):
        """Тест получения покупки другого пользователя."""
        found_purchase = await proxy_purchase_crud.get_user_purchase(
            db_session,
            purchase_id=test_proxy_purchase.id,
            user_id=99999  # Чужой пользователь
        )

        assert found_purchase is None

    async def test_get_user_purchases_all(self, db_session, test_user, test_proxy_product, test_order):
        """Тест получения всех покупок пользователя."""
        # Создаем несколько покупок
        purchases_data = [
            {"expires_at": datetime.now() + timedelta(days=30), "is_active": True},
            {"expires_at": datetime.now() + timedelta(days=15), "is_active": True},
            {"expires_at": datetime.now() - timedelta(days=5), "is_active": False}
        ]

        created_purchases = []
        for i, data in enumerate(purchases_data):
            purchase = await proxy_purchase_crud.create_purchase(
                db_session,
                user_id=test_user.id,
                proxy_product_id=test_proxy_product.id,
                order_id=test_order.id,
                proxy_list=f"192.168.1.{i + 1}:8080:user:pass",
                expires_at=data["expires_at"]
            )

            if not data["is_active"]:
                purchase.is_active = False
                await db_session.commit()

            created_purchases.append(purchase)

        # Получаем все покупки
        all_purchases = await proxy_purchase_crud.get_user_purchases(
            db_session,
            user_id=test_user.id,
            active_only=False
        )

        # Получаем только активные
        active_purchases = await proxy_purchase_crud.get_user_purchases(
            db_session,
            user_id=test_user.id,
            active_only=True
        )

        assert len(all_purchases) >= 3
        assert len(active_purchases) == 2  # Только активные

    async def test_get_user_purchases_with_pagination(self, db_session, test_user, test_proxy_product, test_order):
        """Тест получения покупок с пагинацией."""
        # Создаем 5 покупок
        for i in range(5):
            await proxy_purchase_crud.create_purchase(
                db_session,
                user_id=test_user.id,
                proxy_product_id=test_proxy_product.id,
                order_id=test_order.id,
                proxy_list=f"192.168.2.{i + 1}:8080:user:pass",
                expires_at=datetime.now() + timedelta(days=30)
            )

        # Тестируем пагинацию
        first_page = await proxy_purchase_crud.get_user_purchases(
            db_session,
            user_id=test_user.id,
            skip=0,
            limit=3
        )

        second_page = await proxy_purchase_crud.get_user_purchases(
            db_session,
            user_id=test_user.id,
            skip=3,
            limit=3
        )

        assert len(first_page) == 3
        assert len(second_page) >= 2

        # Проверяем что покупки не дублируются
        first_page_ids = {p.id for p in first_page}
        second_page_ids = {p.id for p in second_page}
        assert first_page_ids.isdisjoint(second_page_ids)

    async def test_get_expiring_purchases(self, db_session, test_user, test_proxy_product, test_order):
        """Тест получения истекающих покупок."""
        # Создаем покупки с разными сроками истечения
        purchases_data = [
            {"days": 3, "should_expire": True},  # Истекает через 3 дня
            {"days": 30, "should_expire": False},  # Истекает через 30 дней
            {"days": 1, "should_expire": True},  # Истекает завтра
            {"days": 10, "should_expire": False}  # Истекает через 10 дней
        ]

        for i, data in enumerate(purchases_data):
            await proxy_purchase_crud.create_purchase(
                db_session,
                user_id=test_user.id,
                proxy_product_id=test_proxy_product.id,
                order_id=test_order.id,
                proxy_list=f"192.168.3.{i + 1}:8080:user:pass",
                expires_at=datetime.now() + timedelta(days=data["days"])
            )

        # Получаем покупки, истекающие в ближайшие 7 дней
        expiring_purchases = await proxy_purchase_crud.get_expiring_purchases(
            db_session,
            user_id=test_user.id,
            days_ahead=7
        )

        # Должно быть 2 покупки (истекающие через 3 дня и 1 день)
        assert len(expiring_purchases) == 2

        # Проверяем что все найденные покупки действительно истекают в ближайшие 7 дней
        for purchase in expiring_purchases:
            days_until_expiry = (purchase.expires_at - datetime.now()).days
            assert days_until_expiry <= 7

    async def test_update_purchase(self, db_session, test_proxy_purchase):
        """Тест обновления покупки прокси."""
        new_expires_at = datetime.now() + timedelta(days=60)

        updated_purchase = await proxy_purchase_crud.update(
            db_session,
            db_obj=test_proxy_purchase,
            obj_in={
                "expires_at": new_expires_at,
                "traffic_used_gb": Decimal("5.5")
            }
        )

        assert updated_purchase.expires_at == new_expires_at
        assert updated_purchase.traffic_used_gb == Decimal("5.5")

    async def test_deactivate_purchase(self, db_session, test_proxy_purchase):
        """Тест деактивации покупки."""
        assert test_proxy_purchase.is_active is True

        await proxy_purchase_crud.deactivate_purchase(
            db_session,
            purchase_id=test_proxy_purchase.id
        )

        await db_session.refresh(test_proxy_purchase)
        assert test_proxy_purchase.is_active is False

    async def test_extend_purchase(self, db_session, test_proxy_purchase):
        """Тест продления покупки."""
        original_expires_at = test_proxy_purchase.expires_at
        days_to_extend = 15

        extended_purchase = await proxy_purchase_crud.extend_purchase(
            db_session,
            purchase_id=test_proxy_purchase.id,
            days=days_to_extend
        )

        expected_new_date = original_expires_at + timedelta(days=days_to_extend)
        assert extended_purchase.expires_at == expected_new_date

    async def test_get_purchase_by_provider_order_id(self, db_session, test_proxy_purchase):
        """Тест получения покупки по ID заказа провайдера."""
        if test_proxy_purchase.provider_order_id:
            found_purchase = await proxy_purchase_crud.get_by_provider_order_id(
                db_session,
                provider_order_id=test_proxy_purchase.provider_order_id
            )

            assert found_purchase is not None
            assert found_purchase.id == test_proxy_purchase.id

    async def test_update_traffic_usage(self, db_session, test_proxy_purchase):
        """Тест обновления использованного трафика."""
        traffic_to_add = Decimal("2.5")

        updated_purchase = await proxy_purchase_crud.update_traffic_usage(
            db_session,
            purchase_id=test_proxy_purchase.id,
            traffic_gb=traffic_to_add
        )

        expected_total = test_proxy_purchase.traffic_used_gb + traffic_to_add
        assert updated_purchase.traffic_used_gb == expected_total

    async def test_get_active_purchases_by_product(self, db_session, test_user, test_proxy_product):
        """Тест получения активных покупок по продукту."""
        # Создаем покупки для разных продуктов
        purchases = []
        for i in range(3):
            purchase = await proxy_purchase_crud.create_purchase(
                db_session,
                user_id=test_user.id,
                proxy_product_id=test_proxy_product.id,
                order_id=1,  # Используем фиксированный order_id для теста
                proxy_list=f"192.168.4.{i + 1}:8080:user:pass",
                expires_at=datetime.now() + timedelta(days=30)
            )
            purchases.append(purchase)

        # Деактивируем одну покупку
        purchases[0].is_active = False
        await db_session.commit()

        active_purchases = await proxy_purchase_crud.get_active_purchases_by_product(
            db_session,
            product_id=test_proxy_product.id
        )

        # Должно быть 2 активные покупки
        assert len(active_purchases) == 2
        assert all(p.is_active for p in active_purchases)
        assert all(p.proxy_product_id == test_proxy_product.id for p in active_purchases)

    async def test_count_user_purchases(self, db_session, test_user, test_proxy_product, test_order):
        """Тест подсчета покупок пользователя."""
        # Создаем несколько покупок
        for i in range(4):
            await proxy_purchase_crud.create_purchase(
                db_session,
                user_id=test_user.id,
                proxy_product_id=test_proxy_product.id,
                order_id=test_order.id,
                proxy_list=f"192.168.5.{i + 1}:8080:user:pass",
                expires_at=datetime.now() + timedelta(days=30)
            )

        total_count = await proxy_purchase_crud.count_user_purchases(
            db_session,
            user_id=test_user.id
        )

        active_count = await proxy_purchase_crud.count_user_purchases(
            db_session,
            user_id=test_user.id,
            active_only=True
        )

        assert total_count >= 4
        assert active_count >= 4

    async def test_get_purchases_by_order(self, db_session, test_order, test_user, test_proxy_product):
        """Тест получения покупок по заказу."""
        # Создаем покупки для конкретного заказа
        for i in range(2):
            await proxy_purchase_crud.create_purchase(
                db_session,
                user_id=test_user.id,
                proxy_product_id=test_proxy_product.id,
                order_id=test_order.id,
                proxy_list=f"192.168.6.{i + 1}:8080:user:pass",
                expires_at=datetime.now() + timedelta(days=30)
            )

        purchases = await proxy_purchase_crud.get_purchases_by_order(
            db_session,
            order_id=test_order.id
        )

        assert len(purchases) >= 2
        assert all(p.order_id == test_order.id for p in purchases)

    async def test_delete_purchase(self, db_session, test_proxy_purchase):
        """Тест удаления покупки."""
        purchase_id = test_proxy_purchase.id

        result = await proxy_purchase_crud.delete(db_session, obj_id=purchase_id)
        assert result is not None

        # Проверяем что покупка удалена
        deleted_purchase = await proxy_purchase_crud.get(db_session, obj_id=purchase_id)
        assert deleted_purchase is None

    async def test_bulk_update_expiration(self, db_session, test_user, test_proxy_product, test_order):
        """Тест массового обновления сроков истечения."""
        # Создаем покупки с одинаковой датой истечения
        original_date = datetime.now() + timedelta(days=5)
        purchase_ids = []

        for i in range(3):
            purchase = await proxy_purchase_crud.create_purchase(
                db_session,
                user_id=test_user.id,
                proxy_product_id=test_proxy_product.id,
                order_id=test_order.id,
                proxy_list=f"192.168.7.{i + 1}:8080:user:pass",
                expires_at=original_date
            )
            purchase_ids.append(purchase.id)

        # Массово продлеваем на 30 дней
        new_date = original_date + timedelta(days=30)
        await proxy_purchase_crud.bulk_update_expiration(
            db_session,
            purchase_ids=purchase_ids,
            new_expires_at=new_date
        )

        # Проверяем что все покупки обновились
        for purchase_id in purchase_ids:
            purchase = await proxy_purchase_crud.get(db_session, obj_id=purchase_id)
            assert purchase.expires_at == new_date
