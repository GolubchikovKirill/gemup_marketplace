import asyncio
import aiohttp
import time


async def test_api_performance():
    """Тест производительности API"""
    start_time = time.time()

    async with aiohttp.ClientSession() as session:
        tasks = []
        for _ in range(100):  # 100 одновременных запросов
            task = session.get('http://localhost:8000/api/v1/products/')
            tasks.append(task)

        responses = await asyncio.gather(*tasks)

    end_time = time.time()
    duration = end_time - start_time

    assert duration < 5.0  # Все запросы за 5 секунд
    assert all(r.status == 200 for r in responses)
