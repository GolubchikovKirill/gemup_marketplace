"""
Тесты производительности с различными сценариями нагрузки
"""

import asyncio
import time

import aiohttp


class PerformanceTest:
    """Тесты производительности"""

    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url

    async def ramp_up_test(self, max_users: int = 100, ramp_duration: int = 60):
        """Тест с постепенным увеличением нагрузки"""
        print(f"📈 Ramp-up test: 0 → {max_users} users over {ramp_duration}s")

        start_time = time.time()
        users_per_second = max_users / ramp_duration

        tasks = []

        for second in range(ramp_duration):
            current_users = int(second * users_per_second)

            # Добавляем новых пользователей
            for _ in range(int(users_per_second)):
                task = self.simulate_user_session()
                tasks.append(task)

            await asyncio.sleep(1)

            if second % 10 == 0:
                print(f"   Current users: {current_users}")

        # Ждем завершения всех задач
        await asyncio.gather(*tasks, return_exceptions=True)

        print(f"✅ Ramp-up test completed in {time.time() - start_time:.2f}s")

    async def spike_test(self, normal_users: int = 10, spike_users: int = 100):
        """Тест с резким скачком нагрузки"""
        print(f"⚡ Spike test: {normal_users} → {spike_users} → {normal_users} users")

        # Нормальная нагрузка
        normal_tasks = [self.simulate_user_session() for _ in range(normal_users)]
        await asyncio.sleep(10)

        # Резкий скачок
        spike_tasks = [self.simulate_user_session() for _ in range(spike_users)]
        await asyncio.sleep(30)

        # Возврат к нормальной нагрузке
        await asyncio.gather(*normal_tasks, *spike_tasks, return_exceptions=True)

        print("✅ Spike test completed")

    async def simulate_user_session(self):
        """Симуляция пользовательской сессии"""
        async with aiohttp.ClientSession() as session:
            # Типичный путь пользователя
            endpoints = [
                "/api/v1/products/",
                "/api/v1/products/1",
                "/api/v1/products/categories/stats",
                "/api/v1/products/meta/countries"
            ]

            for endpoint in endpoints:
                try:
                    async with session.get(f"{self.base_url}{endpoint}") as response:
                        await response.text()
                except Exception:
                    pass

                # Пауза между запросами
                await asyncio.sleep(0.5)


async def run_performance_tests():
    """Запуск всех тестов производительности"""
    perf_test = PerformanceTest()

    print("🚀 Starting performance tests...")

    # Тест с постепенным увеличением нагрузки
    await perf_test.ramp_up_test(max_users=50, ramp_duration=30)

    # Пауза между тестами
    await asyncio.sleep(10)

    # Тест с резким скачком
    await perf_test.spike_test(normal_users=5, spike_users=50)

    print("\n✅ All performance tests completed!")


if __name__ == "__main__":
    asyncio.run(run_performance_tests())
