import pytest

from app.crud.user import user_crud
from app.schemas.user import UserCreate


@pytest.mark.unit
@pytest.mark.crud
class TestUserCRUD:

    async def test_create_user(self, db_session):
        """Тест создания пользователя"""
        user_data = UserCreate(
            email="newuser@example.com",
            username="newuser",
            password="password123",
            first_name="New",
            last_name="User"
        )

        user = await user_crud.create_registered_user(db_session, user_in=user_data)

        assert user.email == "newuser@example.com"
        assert user.username == "newuser"
        assert user.is_guest is False
        assert user.is_active is True
        assert user.hashed_password != "password123"  # Пароль должен быть захеширован

    async def test_get_user_by_email(self, db_session, test_user):
        """Тест получения пользователя по email"""
        found_user = await user_crud.get_by_email(db_session, email=test_user.email)

        assert found_user is not None
        assert found_user.id == test_user.id
        assert found_user.email == test_user.email

    async def test_authenticate_user(self, db_session, test_user):
        """Тест аутентификации пользователя"""
        authenticated_user = await user_crud.authenticate(
            db_session,
            email=test_user.email,
            password="testpassword123"
        )

        assert authenticated_user is not None
        assert authenticated_user.id == test_user.id

    async def test_authenticate_wrong_password(self, db_session, test_user):
        """Тест аутентификации с неверным паролем"""
        authenticated_user = await user_crud.authenticate(
            db_session,
            email=test_user.email,
            password="wrongpassword"
        )

        assert authenticated_user is None

    async def test_create_guest_user(self, db_session):
        """Тест создания гостевого пользователя"""
        guest = await user_crud.create_guest_user(db_session, session_id="guest-123")

        assert guest.is_guest is True
        assert guest.guest_session_id == "guest-123"
        assert guest.guest_expires_at is not None
        assert guest.email is None

    async def test_convert_guest_to_registered(self, db_session, test_guest_user):
        """Тест конвертации гостевого пользователя"""
        user_data = UserCreate(
            email="converted@example.com",
            username="converted",
            password="password123",
            first_name="Converted",
            last_name="User"
        )

        converted_user = await user_crud.convert_guest_to_registered(
            db_session,
            guest_user=test_guest_user,
            user_data=user_data
        )

        assert converted_user.is_guest is False
        assert converted_user.email == "converted@example.com"
        assert converted_user.guest_session_id is None
        assert converted_user.id == test_guest_user.id  # Тот же пользователь
