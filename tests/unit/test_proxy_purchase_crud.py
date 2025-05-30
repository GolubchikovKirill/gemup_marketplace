import pytest
from datetime import datetime, timedelta

from app.crud.proxy_purchase import proxy_purchase_crud


@pytest.mark.unit
@pytest.mark.asyncio  # ДОБАВЛЕНО: для всего класса
class TestProxyPurchaseCRUD:

    async def test_create_purchase(self, db_session, test_user):
        """Тест создания покупки прокси"""
        expires_at = datetime.now() + timedelta(days=30)

        purchase = await proxy_purchase_crud.create_purchase(
            db_session,
            user_id=test_user.id,
            proxy_product_id=1,
            order_id=1,
            proxy_list="1.2.3.4:8080\n5.6.7.8:8080",
            username="test_user",
            password="test_pass",
            expires_at=expires_at
        )

        assert purchase.user_id == test_user.id
        assert purchase.proxy_list == "1.2.3.4:8080\n5.6.7.8:8080"
        assert purchase.username == "test_user"
        assert purchase.is_active is True

    async def test_get_user_purchase(self, db_session, test_user):
        """Тест получения покупки пользователя"""
        expires_at = datetime.now() + timedelta(days=30)
        purchase = await proxy_purchase_crud.create_purchase(
            db_session,
            user_id=test_user.id,
            proxy_product_id=1,
            order_id=1,
            proxy_list="1.2.3.4:8080",
            expires_at=expires_at
        )

        found_purchase = await proxy_purchase_crud.get_user_purchase(
            db_session,
            purchase_id=purchase.id,
            user_id=test_user.id
        )

        assert found_purchase is not None
        assert found_purchase.id == purchase.id

    async def test_get_user_purchases(self, db_session, test_user):
        """Тест получения всех покупок пользователя"""
        expires_at = datetime.now() + timedelta(days=30)

        await proxy_purchase_crud.create_purchase(
            db_session,
            user_id=test_user.id,
            proxy_product_id=1,
            order_id=1,
            proxy_list="1.2.3.4:8080",
            expires_at=expires_at
        )

        await proxy_purchase_crud.create_purchase(
            db_session,
            user_id=test_user.id,
            proxy_product_id=2,
            order_id=2,
            proxy_list="5.6.7.8:8080",
            expires_at=expires_at
        )

        purchases = await proxy_purchase_crud.get_user_purchases(
            db_session,
            user_id=test_user.id,
            active_only=True
        )

        assert len(purchases) == 2

    async def test_get_user_purchases_inactive(self, db_session, test_user):
        """Тест получения неактивных покупок"""
        expires_at = datetime.now() + timedelta(days=30)
        purchase = await proxy_purchase_crud.create_purchase(
            db_session,
            user_id=test_user.id,
            proxy_product_id=1,
            order_id=1,
            proxy_list="1.2.3.4:8080",
            expires_at=expires_at
        )

        purchase.is_active = False
        await db_session.commit()

        active_purchases = await proxy_purchase_crud.get_user_purchases(
            db_session,
            user_id=test_user.id,
            active_only=True
        )

        all_purchases = await proxy_purchase_crud.get_user_purchases(
            db_session,
            user_id=test_user.id,
            active_only=False
        )

        assert len(active_purchases) == 0
        assert len(all_purchases) == 1

    async def test_get_expiring_purchases(self, db_session, test_user):
        """Тест получения истекающих покупок"""
        expires_soon = datetime.now() + timedelta(days=3)
        await proxy_purchase_crud.create_purchase(
            db_session,
            user_id=test_user.id,
            proxy_product_id=1,
            order_id=1,
            proxy_list="1.2.3.4:8080",
            expires_at=expires_soon
        )

        expires_later = datetime.now() + timedelta(days=30)
        await proxy_purchase_crud.create_purchase(
            db_session,
            user_id=test_user.id,
            proxy_product_id=1,
            order_id=2,
            proxy_list="5.6.7.8:8080",
            expires_at=expires_later
        )

        expiring = await proxy_purchase_crud.get_expiring_purchases(
            db_session,
            user_id=test_user.id,
            days_ahead=7
        )

        assert len(expiring) == 1
        assert expiring[0].expires_at == expires_soon

    async def test_create_purchase_with_list(self, db_session, test_user):
        """Тест создания покупки со списком прокси"""
        expires_at = datetime.now() + timedelta(days=30)
        proxy_list = ["1.2.3.4:8080", "5.6.7.8:8080"]

        purchase = await proxy_purchase_crud.create_purchase(
            db_session,
            user_id=test_user.id,
            proxy_product_id=1,
            order_id=1,
            proxy_list=proxy_list,
            expires_at=expires_at
        )

        assert purchase.proxy_list == "1.2.3.4:8080\n5.6.7.8:8080"
