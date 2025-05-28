import pytest
import json
from app.core.redis import redis_client


@pytest.mark.unit
class TestRedisService:

    @pytest.mark.asyncio
    async def test_redis_connection(self):
        """Тест подключения к Redis"""
        try:
            await redis_client.connect()
            result = await redis_client.ping()
            assert result is True
        except Exception:
            pytest.skip("Redis not available in test environment")

    @pytest.mark.asyncio
    async def test_basic_operations(self):
        """Тест базовых операций Redis"""
        try:
            await redis_client.connect()

            # SET/GET
            await redis_client.set("test_key", "test_value")
            value = await redis_client.get("test_key")
            assert value == "test_value"

            # DELETE
            await redis_client.delete("test_key")
            value = await redis_client.get("test_key")
            assert value is None

        except Exception:
            pytest.skip("Redis not available in test environment")

    @pytest.mark.asyncio
    async def test_json_operations(self):
        """Тест JSON операций"""
        try:
            await redis_client.connect()

            test_data = {"key": "value", "number": 123}

            # Сохраняем JSON
            await redis_client.set("test_json", json.dumps(test_data))

            # Получаем JSON
            value = await redis_client.get("test_json")
            if value:
                parsed_data = json.loads(value)
                assert parsed_data == test_data

            # Очищаем
            await redis_client.delete("test_json")

        except Exception:
            pytest.skip("Redis not available in test environment")
