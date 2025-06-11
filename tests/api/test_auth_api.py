import uuid

from fastapi.testclient import TestClient


class TestAuthAPI:

    def test_register_success(self, api_client: TestClient):
        """Тест успешной регистрации"""
        unique_id = str(uuid.uuid4())[:8]
        user_data = {
            "email": f"newuser-{unique_id}@example.com",
            "password": "newpassword123",
            "username": f"newuser-{unique_id}",
            "first_name": "New",
            "last_name": "User"
        }

        response = api_client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 200

        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["username"] == user_data["username"]
        assert "id" in data

    def test_register_duplicate_email(self, api_client: TestClient, test_user):
        """Тест регистрации с существующим email"""
        user_data = {
            "email": test_user.email,
            "password": "password123",
            "username": "different",
            "first_name": "Different",
            "last_name": "User"
        }

        response = api_client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 400
        # ИСПРАВЛЕНО: проверяем правильную структуру ответа
        response_data = response.json()
        assert "already exists" in (response_data.get("detail", "") or response_data.get("message", ""))

    def test_login_form_success(self, api_client: TestClient, test_user):
        """Тест успешного логина через форму"""
        login_data = {
            "username": test_user.email,
            "password": "testpassword123"
        }

        response = api_client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == test_user.email

    def test_login_json_success(self, api_client: TestClient, test_user):
        """Тест успешного логина через JSON"""
        login_data = {
            "email": test_user.email,
            "password": "testpassword123"
        }

        response = api_client.post("/api/v1/auth/login/json", json=login_data)
        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self, api_client: TestClient):
        """Тест логина с неверными данными"""
        login_data = {
            "username": "wrong@example.com",
            "password": "wrongpassword"
        }

        response = api_client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 401
        # ИСПРАВЛЕНО: проверяем правильную структуру ответа
        response_data = response.json()
        assert "Incorrect email or password" in (response_data.get("detail", "") or response_data.get("message", ""))

    def test_get_current_user(self, api_client: TestClient, auth_headers):
        """Тест получения информации о текущем пользователе"""
        response = api_client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "email" in data
        assert "id" in data

    def test_refresh_token(self, api_client: TestClient, auth_headers):
        """Тест обновления токена"""
        response = api_client.post("/api/v1/auth/refresh", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_logout(self, api_client: TestClient, auth_headers):
        """Тест выхода из системы"""
        response = api_client.post("/api/v1/auth/logout", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "Successfully logged out" in data["message"]

    def test_unauthorized_access(self, api_client: TestClient):
        """Тест доступа без авторизации"""
        response = api_client.get("/api/v1/auth/me")
        assert response.status_code == 403
        response_data = response.json()
        assert "Not authenticated" in (response_data.get("detail", "") or response_data.get("message", ""))
