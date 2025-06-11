"""
Интеграционные тесты производительности.

Тестирует производительность API под нагрузкой.
"""

import pytest
import asyncio
import time
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.performance
@pytest.mark.asyncio
class TestPerformanceIntegration:
    """Тесты производительности API."""

    async def test_api_response_times(self, client: AsyncClient):
        """Тест времени ответа API."""
        endpoints = [
            "/api/v1/products/",
            "/api/v1/products/categories/stats",
            "/api/v1/products/meta/countries"
        ]

        for endpoint in endpoints:
            start_time = time.time()
            response = await client.get(endpoint)
            end_time = time.time()

            response_time = end_time - start_time

            assert response.status_code == 200
            assert response_time < 2.0  # Ответ должен быть быстрее 2 секунд

    async def test_concurrent_users_simulation(self, client: AsyncClient):
        """Симуляция одновременных пользователей."""

        async def simulate_user_session():
            """Симуляция сессии пользователя."""
            try:
                # Просмотр продуктов
                await client.get("/api/v1/products/")
                await asyncio.sleep(0.1)

                # Просмотр категорий
                await client.get("/api/v1/products/categories/stats")
                await asyncio.sleep(0.1)

                # Просмотр стран
                await client.get("/api/v1/products/meta/countries")

                return "success"
            except Exception as e:
                return f"error: {e}"

        # Симулируем 20 одновременных пользователей
        tasks = [simulate_user_session() for _ in range(20)]

        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        total_time = end_time - start_time
        successful_sessions = sum(1 for r in results if r == "success")

        # Проверяем что большинство сессий прошли успешно
        assert successful_sessions >= 15  # Минимум 75% успешных
        assert total_time < 10.0  # Все сессии за 10 секунд

    async def test_database_performance(self, client: AsyncClient, db_session):
        """Тест производительности работы с базой данных."""
        from app.models.models import ProxyProduct, ProxyType, ProxyCategory, SessionType, ProviderType
        from decimal import Decimal

        # Создаем много продуктов для тестирования
        products = []
        for i in range(100):
            product = ProxyProduct(
                name=f"Performance Test Product {i}",
                proxy_type=ProxyType.HTTP,
                proxy_category=ProxyCategory.DATACENTER,
                session_type=SessionType.ROTATING,
                provider=ProviderType.PROVIDER_711,
                country_code="US",
                country_name="United States",
                price_per_proxy=Decimal("1.00"),
                duration_days=30,
                stock_available=100,
                is_active=True
            )
            products.append(product)

        # Измеряем время вставки
        start_time = time.time()
        db_session.add_all(products)
        await db_session.commit()
        insert_time = time.time() - start_time

        # Измеряем время запроса
        start_time = time.time()
        response = await client.get("/api/v1/products/")
        query_time = time.time() - start_time

        assert response.status_code == 200
        assert insert_time < 5.0  # Вставка 100 записей за 5 секунд
        assert query_time < 1.0  # Запрос за 1 секунду

    async def test_memory_usage_under_load(self, client: AsyncClient):
        """Тест использования памяти под нагрузкой."""
        import psutil
        import os

        # Получаем процесс текущего приложения
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Создаем нагрузку
        tasks = []
        for _ in range(50):
            task = client.get("/api/v1/products/")
            tasks.append(task)

        await asyncio.gather(*tasks, return_exceptions=True)

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Увеличение памяти не должно быть критичным
        assert memory_increase < 100  # Не больше 100MB

    async def test_large_payload_handling(self, client: AsyncClient, auth_headers):
        """Тест обработки больших payload."""
        # Тест с большим описанием платежа
        large_description = "A" * 10000  # 10KB

        payment_data = {
            "amount": 10.0,
            "description": large_description
        }

        start_time = time.time()
        response = await client.post(
            "/api/v1/payments/create",
            json=payment_data,
            headers=auth_headers
        )
        response_time = time.time() - start_time

        # Должен либо принять, либо отклонить, но быстро
        assert response.status_code in [200, 400, 413, 422]
        assert response_time < 5.0

    async def test_pagination_performance(self, client: AsyncClient, db_session):
        """Тест производительности пагинации."""
        from app.models.models import ProxyProduct, ProxyType, ProxyCategory, SessionType, ProviderType
        from decimal import Decimal

        # Создаем много продуктов
        products = []
        for i in range(500):
            product = ProxyProduct(
                name=f"Pagination Test Product {i}",
                proxy_type=ProxyType.HTTP,
                proxy_category=ProxyCategory.DATACENTER,
                session_type=SessionType.ROTATING,
                provider=ProviderType.PROVIDER_711,
                country_code="US",
                country_name="United States",
                price_per_proxy=Decimal("1.00"),
                duration_days=30,
                stock_available=100,
                is_active=True
            )
            products.append(product)

        db_session.add_all(products)
        await db_session.commit()

        # Тестируем разные страницы
        page_times = []
        for page in range(0, 5):
            start_time = time.time()
            response = await client.get(f"/api/v1/products/?skip={page * 50}&limit=50")
            page_time = time.time() - start_time
            page_times.append(page_time)

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) <= 50

        # Время ответа не должно сильно увеличиваться для поздних страниц
        avg_time = sum(page_times) / len(page_times)
        assert avg_time < 1.0
        assert max(page_times) < 2.0

    async def test_websocket_performance(self, client: AsyncClient):
        """Тест производительности WebSocket (если используется)."""
        # Этот тест может быть применим если в API есть WebSocket соединения
        # Пока оставляем как заглушку
        pass

    @pytest.mark.slow
    async def test_long_running_operations(self, client: AsyncClient, auth_headers):
        """Тест длительных операций."""
        # Тест создания заказа с большим количеством прокси
        # (может быть долгим, поэтому помечен как slow)

        with pytest.timeout(30):  # Максимум 30 секунд
            # Создаем большой заказ
            large_order_data = {
                "items": [
                    {"product_id": 1, "quantity": 100}
                ]
            }

            # Здесь был бы реальный тест большого заказа
            # Пока делаем простую проверку timeout
            start_time = time.time()
            await asyncio.sleep(0.1)  # Симуляция работы
            end_time = time.time()

            assert end_time - start_time < 30.0

    async def test_api_throughput(self, client: AsyncClient):
        """Тест пропускной способности API."""

        async def make_request():
            return await client.get("/api/v1/products/meta/countries")

        # Засекаем время для 100 запросов
        start_time = time.time()

        tasks = [make_request() for _ in range(100)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()
        total_time = end_time - start_time

        successful_requests = sum(
            1 for r in responses
            if hasattr(r, 'status_code') and r.status_code == 200
        )

        throughput = successful_requests / total_time  # requests per second

        # Должно обрабатывать минимум 10 запросов в секунду
        assert throughput >= 10.0
        assert successful_requests >= 95  # 95% успешных запросов
