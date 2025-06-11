from fastapi.testclient import TestClient


class TestUsersAPI:

    def test_get_my_profile(self, api_client: TestClient, auth_headers, test_user):
        """Тест получения профиля пользователя"""
        response = api_client.get("/api/v1/users/me", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["email"] == test_user.email
        assert data["id"] == test_user.id
        assert "balance" in data

    def test_get_my_profile_without_auth(self, api_client: TestClient):
        """Тест получения профиля без авторизации"""
        response = api_client.get("/api/v1/users/me")
        assert response.status_code in [200, 403]

    def test_update_my_profile(self, api_client: TestClient, auth_headers):
        """Тест обновления профиля"""
        update_data = {
            "first_name": "Updated",
            "last_name": "User",
            "username": "updated_user"
        }

        response = api_client.put("/api/v1/users/me", json=update_data, headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["first_name"] == "Updated"
        assert data["last_name"] == "User"

    def test_update_profile_duplicate_email(self, api_client: TestClient, auth_headers, db_session):
        """Тест обновления с существующим email"""
        # ИСПРАВЛЕНО: убрали async и EmailStr()
        from app.crud.user import user_crud
        from app.schemas.user import UserCreate
        import asyncio

        async def create_other_user():
            other_user_data = UserCreate(
                email="other@example.com",  # ИСПРАВЛЕНО: обычная строка
                password="password123",
                first_name="Other",
                last_name="User",
                username="otheruser"
            )
            return await user_crud.create_registered_user(db_session, user_in=other_user_data)

        # Выполняем асинхронную операцию синхронно
        asyncio.get_event_loop().run_until_complete(create_other_user())

        update_data = {
            "email": "other@example.com",
            "first_name": "Updated",
            "last_name": "Name",
            "username": "updated"
        }

        response = api_client.put("/api/v1/users/me", json=update_data, headers=auth_headers)
        assert response.status_code == 400
        # ИСПРАВЛЕНО: проверяем оба поля
        response_data = response.json()
        error_msg = response_data.get("detail", "") or response_data.get("message", "")
        assert "already exists" in error_msg

    def test_get_balance(self, api_client: TestClient, auth_headers, test_user):
        """Тест получения баланса"""
        response = api_client.get("/api/v1/users/balance", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "balance" in data
        assert data["currency"] == "USD"
        assert data["user_id"] == test_user.id
        assert data["is_guest"] is False

    def test_get_balance_without_auth(self, api_client: TestClient):
        """Тест получения баланса без авторизации"""
        response = api_client.get("/api/v1/users/balance")
        assert response.status_code in [200, 403]

    def test_convert_guest_to_registered(self, api_client: TestClient):
        """Тест конвертации гостя в зарегистрированного пользователя"""
        guest_response = api_client.get("/api/v1/users/me")
        if guest_response.status_code == 200:
            guest_data = guest_response.json()
            if guest_data.get("is_guest"):
                convert_data = {
                    "email": "converted@example.com",
                    "password": "newpassword123",
                    "username": "converted_user",
                    "first_name": "Converted",
                    "last_name": "User"
                }

                response = api_client.post("/api/v1/users/convert-guest", json=convert_data)
                assert response.status_code == 200

                data = response.json()
                assert data["email"] == convert_data["email"]
                assert data["is_guest"] is False

    def test_convert_registered_user_error(self, api_client: TestClient, auth_headers):
        """Тест ошибки конвертации уже зарегистрированного пользователя"""
        convert_data = {
            "email": "new@example.com",
            "password": "password123",
            "username": "newuser",
            "first_name": "New",
            "last_name": "User"
        }

        response = api_client.post("/api/v1/users/convert-guest", json=convert_data, headers=auth_headers)
        assert response.status_code == 400
        # ИСПРАВЛЕНО: проверяем оба поля
        response_data = response.json()
        error_msg = response_data.get("detail", "") or response_data.get("message", "")
        assert "already registered" in error_msg

    def test_convert_guest_duplicate_email(self, api_client: TestClient, test_user):
        """Тест конвертации гостя с существующим email"""
        convert_data = {
            "email": test_user.email,
            "password": "password123",
            "username": "duplicate",
            "first_name": "Duplicate",
            "last_name": "User"
        }

        response = api_client.post("/api/v1/users/convert-guest", json=convert_data)
        assert response.status_code == 400
        # ИСПРАВЛЕНО: проверяем оба поля
        response_data = response.json()
        error_msg = response_data.get("detail", "") or response_data.get("message", "")
        assert "already exists" in error_msg
