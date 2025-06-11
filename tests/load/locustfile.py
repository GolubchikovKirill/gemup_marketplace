"""
Нагрузочные тесты для Gemup Marketplace API
Запуск: locust -f tests/load/locustfile.py --host=http://web:8000
"""

import random
from locust import HttpUser, task, between


class WebsiteUser(HttpUser):
    """Пользователь сайта"""
    wait_time = between(1, 3)

    @task(5)
    def browse_products(self):
        """Просмотр каталога продуктов"""
        self.client.get("/api/v1/products/")

    @task(3)
    def get_categories_stats(self):
        """Получение статистики категорий"""
        self.client.get("/api/v1/products/categories/stats")

    @task(2)
    def get_countries(self):
        """Получение списка стран"""
        self.client.get("/api/v1/products/meta/countries")

    @task(2)
    def browse_category(self):
        """Просмотр категории"""
        categories = ["datacenter", "residential", "isp", "nodepay", "grass"]
        category = random.choice(categories)
        self.client.get(f"/api/v1/products/categories/{category}")

    @task(1)
    def view_product_details(self):
        """Просмотр деталей продукта"""
        # Пробуем получить продукт с ID 1-5
        product_id = random.randint(1, 5)
        self.client.get(f"/api/v1/products/{product_id}")


class GuestUser(HttpUser):
    """Гостевой пользователь"""
    weight = 3
    wait_time = between(2, 5)

    @task(5)
    def browse_products(self):
        """Просмотр продуктов"""
        self.client.get("/api/v1/products/")

    @task(2)
    def view_categories(self):
        """Просмотр категорий"""
        categories = ["datacenter", "residential", "isp"]
        category = random.choice(categories)
        self.client.get(f"/api/v1/products/categories/{category}")
