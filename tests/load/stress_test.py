"""
Стресс-тесты для критических эндпоинтов
Запуск: python tests/load/stress_test.py
"""

import asyncio
import statistics
import time
from typing import List, Dict

import aiohttp


class StressTest:
    """Стресс-тестирование API"""

    def __init__(self, base_url: str = "http://web:8000"):
        self.base_url = base_url
        self.results = []

    async def make_request(self, session: aiohttp.ClientSession, endpoint: str) -> Dict:
        """Выполнение одного запроса"""
        start_time = time.time()
        try:
            async with session.get(f"{self.base_url}{endpoint}") as response:
                end_time = time.time()
                return {
                    "endpoint": endpoint,
                    "status": response.status,
                    "response_time": end_time - start_time,
                    "success": response.status == 200
                }
        except Exception as e:
            end_time = time.time()
            return {
                "endpoint": endpoint,
                "status": 0,
                "response_time": end_time - start_time,
                "success": False,
                "error": str(e)
            }

    async def stress_test_endpoint(
            self,
            endpoint: str,
            concurrent_users: int = 50,
            duration: int = 30
    ) -> Dict:
        """Стресс-тест одного эндпоинта"""
        print(f"🔥 Stress testing {endpoint} with {concurrent_users} users for {duration}s")

        start_time = time.time()
        end_time = start_time + duration

        async with aiohttp.ClientSession() as session:
            while time.time() < end_time:
                tasks = []
                for _ in range(concurrent_users):
                    task = self.make_request(session, endpoint)
                    tasks.append(task)

                results = await asyncio.gather(*tasks)
                self.results.extend(results)

                # Небольшая пауза между волнами
                await asyncio.sleep(0.1)

        return self.analyze_results(endpoint)

    def analyze_results(self, endpoint: str) -> Dict:
        """Анализ результатов тестирования"""
        endpoint_results = [r for r in self.results if r["endpoint"] == endpoint]

        if not endpoint_results:
            return {"error": "No results found"}

        response_times = [r["response_time"] for r in endpoint_results]
        success_count = sum(1 for r in endpoint_results if r["success"])
        total_requests = len(endpoint_results)

        analysis = {
            "endpoint": endpoint,
            "total_requests": total_requests,
            "successful_requests": success_count,
            "failed_requests": total_requests - success_count,
            "success_rate": (success_count / total_requests) * 100,
            "avg_response_time": statistics.mean(response_times),
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "median_response_time": statistics.median(response_times),
            "p95_response_time": self.percentile(response_times, 95),
            "p99_response_time": self.percentile(response_times, 99),
            "requests_per_second": total_requests / sum(response_times) if response_times else 0
        }

        return analysis

    @staticmethod
    def percentile(data: List[float], percentile: int) -> float:
        """Вычисление перцентиля"""
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]

    def print_results(self, results: Dict):
        """Вывод результатов"""
        print(f"\n📊 Results for {results['endpoint']}:")
        print(f"   Total requests: {results['total_requests']}")
        print(f"   Success rate: {results['success_rate']:.2f}%")
        print(f"   Avg response time: {results['avg_response_time']:.3f}s")
        print(f"   P95 response time: {results['p95_response_time']:.3f}s")
        print(f"   P99 response time: {results['p99_response_time']:.3f}s")
        print(f"   Requests/sec: {results['requests_per_second']:.2f}")


async def main():
    """Запуск стресс-тестов"""
    stress_test = StressTest()

    # Критические эндпоинты для тестирования
    endpoints = [
        "/api/v1/products/",
        "/api/v1/products/categories/stats",
        "/api/v1/products/meta/countries",
    ]

    print("🚀 Starting stress tests...")

    for endpoint in endpoints:
        stress_test.results = []  # Очищаем результаты для каждого эндпоинта
        results = await stress_test.stress_test_endpoint(
            endpoint,
            concurrent_users=20,
            duration=15
        )
        stress_test.print_results(results)

        # Пауза между тестами
        await asyncio.sleep(2)

    print("\n✅ Stress tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
