import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.auth
class TestAuthRoutes:

    async def test_register_user(self, client: AsyncClient):
        """Тест регистрации пользователя"""
        user_data = {
            "email": "register@example.com",
            "username": "registeruser",
            "password": "password123",
            "first_name": "Register",
            "last_name": "User"
        }

        response = await client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "register@example.com"
        assert data["username"] == "registeruser"
        assert "id" in data

    async def test_register_duplicate_email(self, client: AsyncClient, test_user):
        """Тест регистрации с дублирующимся email"""
        user_data = {
            "email": test_user.email,
            "username": "newusername",
            "password": "password123",
            "first_name": "New",
            "last_name": "User"
        }

        response = await client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    async def test_login_success(self, client: AsyncClient, test_user):
        """Тест успешной авторизации"""
        login_data = {
            "username": test_user.email,
            "password": "testpassword123"
        }

        response = await client.post("/api/v1/auth/login", data=login_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == test_user.email

    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        """Тест авторизации с неверным паролем"""
        login_data = {
            "username": test_user.email,
            "password": "wrongpassword"
        }

        response = await client.post("/api/v1/auth/login", data=login_data)

        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    async def test_get_current_user(self, client: AsyncClient, auth_headers):
        """Тест получения информации о текущем пользователе"""
        response = await client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert "username" in data

    async def test_get_current_user_unauthorized(self, client: AsyncClient):
        """Тест получения информации без авторизации"""
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 403
