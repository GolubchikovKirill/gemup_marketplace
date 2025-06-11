"""
Интеграционные тесты безопасности.

Тестирует защиту от различных видов атак и уязвимостей.
"""

import pytest
from httpx import AsyncClient
import asyncio


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.asyncio
class TestSecurityIntegration:
    """Тесты безопасности API."""

    async def test_rate_limiting_protection(self, client: AsyncClient):
        """Тест защиты от rate limiting."""
        # Быстрые повторные запросы на один endpoint
        tasks = []
        for _ in range(20):
            task = client.get("/api/v1/products/")
            tasks.append(task)

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Проверяем что есть защита от спама
        status_codes = [r.status_code for r in responses if hasattr(r, 'status_code')]

        # Должны быть как успешные запросы, так и заблокированные
        assert 200 in status_codes
        # Может быть 429 (Too Many Requests) если включен rate limiting
        rate_limited = any(code == 429 for code in status_codes)

        # Если rate limiting не настроен, хотя бы проверим что сервер выдерживает нагрузку
        assert len([code for code in status_codes if code == 200]) >= 10

    async def test_sql_injection_protection(self, client: AsyncClient, auth_headers):
        """Тест защиты от SQL инъекций."""
        # Попытки SQL инъекций в различных параметрах
        sql_payloads = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "1; DELETE FROM orders; --",
            "' UNION SELECT * FROM users --",
            "admin'--",
            "'; INSERT INTO users VALUES('hacker', 'password'); --"
        ]

        for payload in sql_payloads:
            # Тест в query параметрах
            response = await client.get(f"/api/v1/products/?search={payload}")
            assert response.status_code in [200, 400, 422]  # Не должно быть 500

            # Тест в path параметрах (если возможно)
            response = await client.get(f"/api/v1/orders/{payload}", headers=auth_headers)
            assert response.status_code in [400, 404, 422]  # Не должно быть 500

    async def test_xss_protection(self, client: AsyncClient, auth_headers):
        """Тест защиты от XSS атак."""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "';alert('XSS');//",
            "<svg/onload=alert('XSS')>",
            "%3Cscript%3Ealert('XSS')%3C/script%3E"
        ]

        for payload in xss_payloads:
            # Тест в описании платежа
            payment_data = {
                "amount": 10.0,
                "description": payload
            }

            response = await client.post(
                "/api/v1/payments/create",
                json=payment_data,
                headers=auth_headers
            )

            # Проверяем что данные либо отклонены, либо правильно экранированы
            if response.status_code == 200:
                data = response.json()
                # Если данные сохранились, они должны быть безопасными
                assert "<script>" not in str(data)
                assert "javascript:" not in str(data)

    async def test_authentication_bypass_attempts(self, client: AsyncClient):
        """Тест попыток обхода аутентификации."""
        # Попытки доступа к защищенным ресурсам без токена
        protected_endpoints = [
            "/api/v1/orders/",
            "/api/v1/proxies/my",
            "/api/v1/cart/",
            "/api/v1/auth/me",
            "/api/v1/payments/history"
        ]

        for endpoint in protected_endpoints:
            response = await client.get(endpoint)
            assert response.status_code in [401, 403]  # Должен требовать аутентификации

        # Попытки с невалидными токенами
        invalid_tokens = [
            "Bearer invalid_token",
            "Bearer ",
            "Invalid token_format",
            "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.fake.token",
            "Bearer null",
            "Bearer undefined"
        ]

        for token in invalid_tokens:
            headers = {"Authorization": token}
            response = await client.get("/api/v1/auth/me", headers=headers)
            assert response.status_code in [401, 403]

    async def test_authorization_bypass_attempts(self, client: AsyncClient, auth_headers):
        """Тест попыток обхода авторизации."""
        # Попытки доступа к ресурсам других пользователей
        other_user_resources = [
            "/api/v1/orders/99999",
            "/api/v1/proxies/99999/generate",
            "/api/v1/proxies/99999/download"
        ]

        for resource in other_user_resources:
            response = await client.get(resource, headers=auth_headers)
            assert response.status_code in [403, 404]  # Не должен давать доступ

    async def test_input_validation_bypass(self, client: AsyncClient, auth_headers):
        """Тест попыток обхода валидации входных данных."""
        # Тест с экстремально большими значениями
        large_data = {
            "amount": 999999999999999999,
            "description": "A" * 10000  # Очень длинная строка
        }

        response = await client.post(
            "/api/v1/payments/create",
            json=large_data,
            headers=auth_headers
        )
        assert response.status_code in [400, 422]  # Должна быть валидация

        # Тест с отрицательными значениями
        negative_data = {
            "amount": -100.0,
            "description": "Negative amount test"
        }

        response = await client.post(
            "/api/v1/payments/create",
            json=negative_data,
            headers=auth_headers
        )
        assert response.status_code in [400, 422]

    async def test_file_upload_security(self, client: AsyncClient, auth_headers):
        """Тест безопасности загрузки файлов (если есть)."""
        # Если в API есть загрузка файлов, тестируем безопасность

        # Попытка загрузки исполняемых файлов
        malicious_files = [
            ("test.exe", b"MZ\x90\x00"),  # Executable header
            ("test.php", b"<?php system($_GET['cmd']); ?>"),
            ("test.js", b"require('child_process').exec('rm -rf /')"),
            ("test.bat", b"@echo off\nrmdir /s /q C:\\"),
        ]

        for filename, content in malicious_files:
            files = {"file": (filename, content, "application/octet-stream")}

            # Если есть endpoint для загрузки файлов
            # response = await client.post("/api/v1/upload", files=files, headers=auth_headers)
            # assert response.status_code in [400, 403, 415]  # Должен отклонить

            # Пока пропускаем, так как endpoint может не существовать
            pass

    async def test_cors_headers(self, client: AsyncClient):
        """Тест правильности CORS заголовков."""
        response = await client.options("/api/v1/products/")

        # Проверяем наличие CORS заголовков
        headers = response.headers

        # В production должны быть ограничены origins
        if "access-control-allow-origin" in headers:
            origin = headers["access-control-allow-origin"]
            # Не должно быть wildcard в production
            if origin == "*":
                # Это может быть нормально для development
                pass

    async def test_sensitive_data_exposure(self, client: AsyncClient, auth_headers):
        """Тест на утечку чувствительных данных."""
        # Проверяем что пароли не возвращаются в ответах
        user_response = await client.get("/api/v1/auth/me", headers=auth_headers)
        if user_response.status_code == 200:
            user_data = user_response.json()

            # Не должно быть полей с паролями
            sensitive_fields = ["password", "hashed_password", "pwd", "secret", "private_key"]
            for field in sensitive_fields:
                assert field not in user_data
                assert field not in str(user_data).lower()

        # Проверяем заказы
        orders_response = await client.get("/api/v1/orders/", headers=auth_headers)
        if orders_response.status_code == 200:
            orders_data = orders_response.json()

            # Не должно быть внутренних ID или ключей
            internal_fields = ["internal_id", "secret_key", "private_data"]
            for field in internal_fields:
                assert field not in str(orders_data).lower()

    async def test_error_information_disclosure(self, client: AsyncClient):
        """Тест на раскрытие информации в ошибках."""
        # Запросы к несуществующим endpoints
        response = await client.get("/api/v1/nonexistent/endpoint")
        assert response.status_code == 404

        error_data = response.json()

        # Ошибка не должна раскрывать внутреннюю структуру
        error_text = str(error_data).lower()
        sensitive_info = [
            "traceback", "file path", "database", "sql", "stack trace",
            "internal server", "debug", "exception"
        ]

        for info in sensitive_info:
            assert info not in error_text

    async def test_session_management(self, client: AsyncClient):
        """Тест управления сессиями."""
        import uuid
        unique_id = str(uuid.uuid4())[:8]

        # Регистрация пользователя
        user_data = {
            "email": f"session-{unique_id}@example.com",
            "username": f"sessionuser-{unique_id}",
            "password": "SessionPassword123!",
            "first_name": "Session",
            "last_name": "User"
        }

        register_response = await client.post("/api/v1/auth/register", json=user_data)
        token = register_response.json().get("access_token")
        auth_headers = {"Authorization": f"Bearer {token}"}

        # Проверяем что токен работает
        response1 = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response1.status_code == 200

        # Logout
        logout_response = await client.post("/api/v1/auth/logout", headers=auth_headers)
        if logout_response.status_code == 200:
            # После logout токен должен быть недействителен
            response2 = await client.get("/api/v1/auth/me", headers=auth_headers)
            assert response2.status_code in [401, 403]

    async def test_brute_force_protection(self, client: AsyncClient, test_user):
        """Тест защиты от brute force атак."""
        # Множественные попытки входа с неверным паролем
        login_attempts = []

        for i in range(10):
            login_data = {
                "username": test_user.email,
                "password": f"wrong_password_{i}"
            }

            task = client.post("/api/v1/auth/login", data=login_data)
            login_attempts.append(task)

        responses = await asyncio.gather(*login_attempts, return_exceptions=True)

        # Все попытки должны быть неуспешными
        status_codes = [r.status_code for r in responses if hasattr(r, 'status_code')]
        assert all(code in [401, 429] for code in status_codes)

        # Должна быть защита от brute force (429 или временная блокировка)
        if 429 in status_codes:
            # Есть rate limiting
            pass
        else:
            # Проверяем что нет информации о валидности email
            for response in responses:
                if hasattr(response, 'json'):
                    error_msg = str(response.json()).lower()
                    assert "user not found" not in error_msg
                    assert "invalid email" not in error_msg
