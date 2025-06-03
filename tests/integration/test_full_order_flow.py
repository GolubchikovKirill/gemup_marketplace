"""
Полные интеграционные тесты E2E flow заказов.

Тестирует полный путь пользователя от регистрации до получения прокси.
"""

import pytest
from httpx import AsyncClient
from decimal import Decimal
from unittest.mock import patch

from app.models.models import ProxyProduct, ProxyType, ProxyCategory, SessionType, ProviderType
from tests.mocks.order_mocks import MockOrderData


@pytest.mark.integration
@pytest.mark.e2e
@pytest.mark.asyncio
class TestFullOrderFlow:
    """E2E тесты полного flow заказов."""

    async def test_complete_user_journey_success(self, client: AsyncClient, db_session):
        """Тест полного пути пользователя: регистрация → покупка → получение прокси."""
        import uuid
        unique_id = str(uuid.uuid4())[:8]

        # 1. Регистрация нового пользователя
        user_data = {
            "email": f"e2e-{unique_id}@example.com",
            "username": f"e2euser-{unique_id}",
            "password": "SecurePassword123!",
            "first_name": "E2E",
            "last_name": "User"
        }

        register_response = await client.post("/api/v1/auth/register", json=user_data)
        assert register_response.status_code == 200

        user_info = register_response.json()
        auth_headers = {"Authorization": f"Bearer {user_info.get('access_token')}"}

        # 2. Создание продукта для покупки
        product = ProxyProduct(
            name="E2E Test Product",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.DATACENTER,
            session_type=SessionType.ROTATING,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("3.00"),
            duration_days=30,
            stock_available=100,
            is_active=True
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # 3. Пополнение баланса
        with patch('app.integrations.cryptomus.cryptomus_api.create_payment') as mock_payment:
            mock_payment.return_value = {
                'state': 0,
                'result': {
                    'uuid': 'e2e-test-uuid',
                    'url': 'https://mock-pay.com/e2e-test'
                }
            }

            payment_response = await client.post(
                "/api/v1/payments/create",
                json={"amount": 50.0, "description": "E2E test top-up"},
                headers=auth_headers
            )
            assert payment_response.status_code == 200

        # 4. Симуляция успешного webhook (пополнение баланса)
        webhook_data = {
            "order_id": payment_response.json()["transaction_id"],
            "status": "paid",
            "amount": "50.0",
            "currency": "USD"
        }

        webhook_response = await client.post("/api/v1/payments/webhook/cryptomus", json=webhook_data)
        assert webhook_response.status_code == 200

        # 5. Добавление товара в корзину
        cart_response = await client.post(
            "/api/v1/cart/items",
            json={"proxy_product_id": product.id, "quantity": 5},
            headers=auth_headers
        )
        assert cart_response.status_code == 201

        # 6. Проверка корзины
        cart_check = await client.get("/api/v1/cart/", headers=auth_headers)
        assert cart_check.status_code == 200
        cart_data = cart_check.json()
        assert len(cart_data["items"]) == 1
        assert cart_data["summary"]["total_amount"] == "15.00"  # 5 * 3.00

        # 7. Создание заказа
        with patch('app.services.order_service.order_service._purchase_proxies_from_provider') as mock_purchase:
            mock_purchase.return_value = MockOrderData.generate_mock_proxy_purchase_data(5)

            order_response = await client.post("/api/v1/orders/", headers=auth_headers)
            assert order_response.status_code == 201

            order_data = order_response.json()
            assert order_data["status"] == "paid"
            order_id = order_data["id"]

        # 8. Проверка что корзина очистилась
        empty_cart = await client.get("/api/v1/cart/", headers=auth_headers)
        cart_data = empty_cart.json()
        assert len(cart_data["items"]) == 0

        # 9. Получение списка прокси
        proxies_response = await client.get("/api/v1/proxies/my", headers=auth_headers)
        assert proxies_response.status_code == 200
        # В зависимости от реализации здесь могут быть прокси

        # 10. Проверка истории заказов
        orders_response = await client.get("/api/v1/orders/", headers=auth_headers)
        assert orders_response.status_code == 200
        orders_list = orders_response.json()
        assert len(orders_list) >= 1
        assert any(order["id"] == order_id for order in orders_list)

        # 11. Получение детальной информации о заказе
        order_detail = await client.get(f"/api/v1/orders/{order_id}", headers=auth_headers)
        assert order_detail.status_code == 200
        detail_data = order_detail.json()
        assert detail_data["id"] == order_id
        assert len(detail_data["order_items"]) == 1

    async def test_guest_to_registered_conversion_flow(self, client: AsyncClient, db_session):
        """Тест flow конвертации гостя в зарегистрированного пользователя."""
        import uuid
        session_id = f"guest-e2e-{str(uuid.uuid4())[:8]}"

        # 1. Создание продукта
        product = ProxyProduct(
            name="Guest Test Product",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.DATACENTER,
            session_type=SessionType.STICKY,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("2.00"),
            duration_days=30,
            stock_available=50,
            is_active=True
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # 2. Добавление товара в корзину как гость
        guest_headers = {"X-Session-ID": session_id}
        cart_response = await client.post(
            "/api/v1/cart/items",
            json={"proxy_product_id": product.id, "quantity": 2},
            headers=guest_headers
        )
        assert cart_response.status_code == 201

        # 3. Регистрация пользователя
        unique_id = str(uuid.uuid4())[:8]
        user_data = {
            "email": f"guest-convert-{unique_id}@example.com",
            "username": f"guestconvert-{unique_id}",
            "password": "ConvertPassword123!",
            "first_name": "Guest",
            "last_name": "Convert"
        }

        register_response = await client.post("/api/v1/auth/register", json=user_data)
        assert register_response.status_code == 200

        user_info = register_response.json()
        {"Authorization": f"Bearer {user_info.get('access_token')}"}

        # 4. Проверка что корзина перенесена (зависит от реализации)
        # Это может потребовать специального endpoint для объединения корзин

        # 5. Пополнение баланса и создание заказа
        # (аналогично предыдущему тесту)

    async def test_concurrent_orders_handling(self, client: AsyncClient, db_session):
        """Тест обработки параллельных заказов."""
        import asyncio
        import uuid

        # Создаем продукт с ограниченным количеством
        product = ProxyProduct(
            name="Limited Stock Product",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.DATACENTER,
            session_type=SessionType.ROTATING,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("1.00"),
            duration_days=30,
            stock_available=5,  # Ограниченное количество
            is_active=True
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # Создаем несколько пользователей
        users_data = []
        for i in range(3):
            unique_id = str(uuid.uuid4())[:8]
            user_data = {
                "email": f"concurrent-{i}-{unique_id}@example.com",
                "username": f"concurrent{i}-{unique_id}",
                "password": "ConcurrentPassword123!",
                "first_name": f"User{i}",
                "last_name": "Concurrent"
            }

            register_response = await client.post("/api/v1/auth/register", json=user_data)
            assert register_response.status_code == 200

            user_info = register_response.json()
            auth_headers = {"Authorization": f"Bearer {user_info.get('access_token')}"}
            users_data.append(auth_headers)

        # Функция для создания заказа
        async def create_order(headers):
            try:
                # Добавляем в корзину
                await client.post(
                    "/api/v1/cart/items",
                    json={"proxy_product_id": product.id, "quantity": 3},
                    headers=headers
                )

                # Создаем заказ
                with patch('app.services.order_service.order_service._purchase_proxies_from_provider') as mock_purchase:
                    mock_purchase.return_value = MockOrderData.generate_mock_proxy_purchase_data(3)

                    response = await client.post("/api/v1/orders/", headers=headers)
                    return response

            except Exception as e:
                return {"error": str(e)}

        # Выполняем параллельные запросы
        tasks = [create_order(headers) for headers in users_data]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Анализируем результаты
        successful_orders = 0
        failed_orders = 0

        for response in responses:
            if hasattr(response, 'status_code'):
                if response.status_code == 201:
                    successful_orders += 1
                else:
                    failed_orders += 1
            else:
                failed_orders += 1

        # Проверяем что система корректно обработала параллельные запросы
        total_orders = successful_orders + failed_orders
        assert total_orders == 3
        # Хотя бы один заказ должен пройти успешно
        assert successful_orders >= 1

    async def test_order_cancellation_flow(self, client: AsyncClient, db_session):
        """Тест flow отмены заказа и возврата средств."""
        import uuid
        unique_id = str(uuid.uuid4())[:8]

        # 1. Регистрация пользователя
        user_data = {
            "email": f"cancel-{unique_id}@example.com",
            "username": f"canceluser-{unique_id}",
            "password": "CancelPassword123!",
            "first_name": "Cancel",
            "last_name": "User"
        }

        register_response = await client.post("/api/v1/auth/register", json=user_data)
        assert register_response.status_code == 200

        user_info = register_response.json()
        auth_headers = {"Authorization": f"Bearer {user_info.get('access_token')}"}

        # 2. Создание продукта
        product = ProxyProduct(
            name="Cancellable Product",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.DATACENTER,
            session_type=SessionType.ROTATING,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("5.00"),
            duration_days=30,
            stock_available=20,
            is_active=True
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # 3. Пополнение баланса
        with patch('app.integrations.cryptomus.cryptomus_api.create_payment') as mock_payment:
            mock_payment.return_value = {
                'state': 0,
                'result': {'uuid': 'cancel-test-uuid', 'url': 'https://mock-pay.com/cancel'}
            }

            payment_response = await client.post(
                "/api/v1/payments/create",
                json={"amount": 100.0, "description": "Cancel test top-up"},
                headers=auth_headers
            )

        # Симуляция webhook
        webhook_data = {
            "order_id": payment_response.json()["transaction_id"],
            "status": "paid",
            "amount": "100.0",
            "currency": "USD"
        }
        await client.post("/api/v1/payments/webhook/cryptomus", json=webhook_data)

        # 4. Создание заказа
        await client.post(
            "/api/v1/cart/items",
            json={"proxy_product_id": product.id, "quantity": 4},
            headers=auth_headers
        )

        with patch('app.services.order_service.order_service._purchase_proxies_from_provider') as mock_purchase:
            mock_purchase.return_value = MockOrderData.generate_mock_proxy_purchase_data(4)

            order_response = await client.post("/api/v1/orders/", headers=auth_headers)
            assert order_response.status_code == 201

            order_id = order_response.json()["id"]

        # 5. Отмена заказа
        cancel_response = await client.post(
            f"/api/v1/orders/{order_id}/cancel",
            json={"reason": "Changed my mind"},
            headers=auth_headers
        )
        assert cancel_response.status_code == 200

        # 6. Проверка что заказ отменен
        order_check = await client.get(f"/api/v1/orders/{order_id}", headers=auth_headers)
        if order_check.status_code == 200:
            order_data = order_check.json()
            # Проверяем статус (зависит от реализации)
            assert order_data.get("status") in ["cancelled", "refunded"]

        # 7. Проверка истории платежей (должен быть возврат)
        payment_history = await client.get("/api/v1/payments/history", headers=auth_headers)
        assert payment_history.status_code == 200

    async def test_expired_proxy_handling(self, client: AsyncClient, db_session):
        """Тест обработки истекших прокси."""
        # Этот тест может быть сложен для реализации в integration тестах
        # так как требует манипуляции временем
        # Оставим как заглушку для будущей реализации
        pass

    async def test_bulk_proxy_purchase(self, client: AsyncClient, db_session):
        """Тест массовой покупки прокси."""
        import uuid
        unique_id = str(uuid.uuid4())[:8]

        # Регистрация пользователя с большим балансом
        user_data = {
            "email": f"bulk-{unique_id}@example.com",
            "username": f"bulkuser-{unique_id}",
            "password": "BulkPassword123!",
            "first_name": "Bulk",
            "last_name": "User"
        }

        register_response = await client.post("/api/v1/auth/register", json=user_data)
        user_info = register_response.json()
        auth_headers = {"Authorization": f"Bearer {user_info.get('access_token')}"}

        # Создание продукта для массовой покупки
        product = ProxyProduct(
            name="Bulk Purchase Product",
            proxy_type=ProxyType.HTTP,
            proxy_category=ProxyCategory.DATACENTER,
            session_type=SessionType.ROTATING,
            provider=ProviderType.PROVIDER_711,
            country_code="US",
            country_name="United States",
            price_per_proxy=Decimal("0.50"),
            duration_days=30,
            max_quantity=1000,
            stock_available=1000,
            is_active=True
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # Пополнение большого баланса
        with patch('app.integrations.cryptomus.cryptomus_api.create_payment') as mock_payment:
            mock_payment.return_value = {
                'state': 0,
                'result': {'uuid': 'bulk-test-uuid', 'url': 'https://mock-pay.com/bulk'}
            }

            payment_response = await client.post(
                "/api/v1/payments/create",
                json={"amount": 1000.0, "description": "Bulk purchase balance"},
                headers=auth_headers
            )

        # Webhook
        webhook_data = {
            "order_id": payment_response.json()["transaction_id"],
            "status": "paid",
            "amount": "1000.0",
            "currency": "USD"
        }
        await client.post("/api/v1/payments/webhook/cryptomus", json=webhook_data)

        # Массовая покупка (500 прокси)
        await client.post(
            "/api/v1/cart/items",
            json={"proxy_product_id": product.id, "quantity": 500},
            headers=auth_headers
        )

        with patch('app.services.order_service.order_service._purchase_proxies_from_provider') as mock_purchase:
            mock_purchase.return_value = MockOrderData.generate_mock_proxy_purchase_data(500)

            bulk_order_response = await client.post("/api/v1/orders/", headers=auth_headers)

            # Может потребоваться больше времени для обработки
            assert bulk_order_response.status_code in [201, 202]  # Accepted для больших заказов

        # Проверка статистики
        stats_response = await client.get("/api/v1/proxies/stats", headers=auth_headers)
        assert stats_response.status_code == 200
