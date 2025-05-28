import pytest
from datetime import datetime, timedelta
from app.crud.proxy_purchase import proxy_purchase_crud
from app.models.models import ProxyPurchase


@pytest.mark.unit
@pytest.mark.asyncio
class TestProxyPurchaseCRUD:

    async def test_create_purchase(self, db_session, test_user):
        """Тест создания покупки прокси"""
        expires_at = datetime.now() + timedelta(days=30)
        proxy_list = ["1.2.3.4:8080", "5.6.7.8:8080"]

        purchase = await proxy_purchase_crud.create_purchase(
            db_session,
            user_id=test_user.id,
            proxy_product_id=1,
            order_id=1,
            proxy_list=proxy_list,
            username="user123",
            password="pass123",
            expires_at=expires_at,
            provider_order_id="711-order-123"
        )

        assert purchase.user_id == test_user.id
        assert purchase.username == "user123"
        assert purchase.password == "pass123"
        assert purchase.is_active is True
        assert "1.2.3.4:8080" in purchase.proxy_list

    async def test_get_user_purchases_active_only(self, db_session, test_user):
        """Тест получения только активных покупок"""
        # Создаем активную покупку
        active_expires = datetime.now() + timedelta(days=30)
        await proxy_purchase_crud.create_purchase(
            db_session,
            user_id=test_user.id,
            proxy_product_id=1,
            order_id=1,
            proxy_list=["1.2.3.4:8080"],
            expires_at=active_expires
        )

        # Создаем истекшую покупку
        expired_expires = datetime.now() - timedelta(days=1)
        expired_purchase = ProxyPurchase(
            user_id=test_user.id,
            proxy_product_id=1,
            order_id=2,
            proxy_list="5.6.7.8:8080",
            expires_at=expired_expires,
            is_active=True
        )
        db_session.add(expired_purchase)
        await db_session.commit()

        # Получаем только активные
        active_purchases = await proxy_purchase_crud.get_user_purchases(
            db_session,
            user_id=test_user.id,
            active_only=True
        )

        # Должна быть только одна активная покупка
        assert len(active_purchases) == 1
        assert active_purchases[0].expires_at > datetime.now()

    async def test_get_user_purchase(self, db_session, test_user):
        """Тест получения конкретной покупки пользователя"""
        expires_at = datetime.now() + timedelta(days=30)

        purchase = await proxy_purchase_crud.create_purchase(
            db_session,
            user_id=test_user.id,
            proxy_product_id=1,
            order_id=1,
            proxy_list=["1.2.3.4:8080"],
            expires_at=expires_at
        )

        # Получаем покупку
        found_purchase = await proxy_purchase_crud.get_user_purchase(
            db_session,
            purchase_id=purchase.id,
            user_id=test_user.id
        )

        assert found_purchase is not None
        assert found_purchase.id == purchase.id

    async def test_get_user_purchase_wrong_user(self, db_session, test_user, test_guest_user):
        """Тест получения покупки другого пользователя"""
        expires_at = datetime.now() + timedelta(days=30)

        purchase = await proxy_purchase_crud.create_purchase(
            db_session,
            user_id=test_user.id,
            proxy_product_id=1,
            order_id=1,
            proxy_list=["1.2.3.4:8080"],
            expires_at=expires_at
        )

        # Пытаемся получить покупку под другим пользователем
        found_purchase = await proxy_purchase_crud.get_user_purchase(
            db_session,
            purchase_id=purchase.id,
            user_id=test_guest_user.id
        )

        assert found_purchase is None

    async def test_update_expiry(self, db_session, test_user):
        """Тест обновления даты истечения"""
        expires_at = datetime.now() + timedelta(days=30)

        purchase = await proxy_purchase_crud.create_purchase(
            db_session,
            user_id=test_user.id,
            proxy_product_id=1,
            order_id=1,
            proxy_list=["1.2.3.4:8080"],
            expires_at=expires_at
        )

        # Обновляем дату истечения
        new_expires_at = expires_at + timedelta(days=30)
        updated_purchase = await proxy_purchase_crud.update_expiry(
            db_session,
            purchase=purchase,
            new_expires_at=new_expires_at
        )

        assert updated_purchase.expires_at == new_expires_at

    async def test_get_expiring_purchases(self, db_session, test_user):
        """Тест получения истекающих покупок"""
        # Создаем покупку, которая истекает через 3 дня
        expires_soon = datetime.now() + timedelta(days=3)
        await proxy_purchase_crud.create_purchase(
            db_session,
            user_id=test_user.id,
            proxy_product_id=1,
            order_id=1,
            proxy_list=["1.2.3.4:8080"],
            expires_at=expires_soon
        )

        # Создаем покупку, которая истекает через 30 дней
        expires_later = datetime.now() + timedelta(days=30)
        await proxy_purchase_crud.create_purchase(
            db_session,
            user_id=test_user.id,
            proxy_product_id=1,
            order_id=2,
            proxy_list=["5.6.7.8:8080"],
            expires_at=expires_later
        )

        # Получаем истекающие в течение 7 дней
        expiry_date = datetime.now() + timedelta(days=7)
        expiring = await proxy_purchase_crud.get_expiring_purchases(
            db_session,
            user_id=test_user.id,
            expiry_date=expiry_date
        )

        # Должна быть только одна истекающая покупка
        assert len(expiring) == 1
        assert expiring[0].expires_at == expires_soon
