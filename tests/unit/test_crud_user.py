import pytest

from app.crud.user import user_crud
from app.schemas.user import UserCreate


@pytest.mark.unit
@pytest.mark.crud
class TestUserCRUD:

    @pytest.mark.asyncio
    async def test_create_user(self, db_session):
        """Тест создания пользователя"""
        import uuid
        unique_id = str(uuid.uuid4())[:8]

        user_data = UserCreate(
            email=f"newuser-{unique_id}@example.com",
            username=f"newuser-{unique_id}",
            password="password123",
            first_name="New",
            last_name="User"
        )

        user = await user_crud.create_registered_user(db_session, user_in=user_data)

        assert user.email == f"newuser-{unique_id}@example.com"
        assert user.username == f"newuser-{unique_id}"
        assert user.is_guest is None or user.is_guest == False
        assert user.is_active is None or user.is_active == True
        assert user.hashed_password != "password123"  # Пароль должен быть захеширован

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, db_session, test_user):
        """Тест получения пользователя по email"""
        found_user = await user_crud.get_by_email(db_session, email=test_user.email)

        assert found_user is not None
        assert found_user.id == test_user.id
        assert found_user.email == test_user.email

    @pytest.mark.asyncio
    async def test_authenticate_user(self, db_session, test_user):
        """Тест аутентификации пользователя"""
        authenticated_user = await user_crud.authenticate(
            db_session,
            email=test_user.email,
            password="testpassword123"
        )

        assert authenticated_user is not None
        assert authenticated_user.id == test_user.id

    @pytest.mark.asyncio
    async def test_authenticate_wrong_password(self, db_session, test_user):
        """Тест аутентификации с неверным паролем"""
        authenticated_user = await user_crud.authenticate(
            db_session,
            email=test_user.email,
            password="wrongpassword"
        )

        assert authenticated_user is None

    @pytest.mark.asyncio
    async def test_create_guest_user(self, db_session):
        """Тест создания гостевого пользователя"""
        import uuid
        session_id = f"guest-{str(uuid.uuid4())[:8]}"

        guest = await user_crud.create_guest_user(db_session, session_id=session_id)

        assert guest.is_guest == True
        assert guest.guest_session_id == session_id
        assert guest.guest_expires_at is not None
        assert guest.email is None

    @pytest.mark.asyncio
    async def test_convert_guest_to_registered(self, db_session, test_guest_user):
        """Тест конвертации гостевого пользователя"""
        import uuid
        unique_id = str(uuid.uuid4())[:8]

        user_data = UserCreate(
            email=f"converted-{unique_id}@example.com",
            username=f"converted-{unique_id}",
            password="password123",
            first_name="Converted",
            last_name="User"
        )

        converted_user = await user_crud.convert_guest_to_registered(
            db_session,
            guest_user=test_guest_user,
            user_data=user_data
        )

        assert converted_user.is_guest == False
        assert converted_user.email == f"converted-{unique_id}@example.com"
        assert converted_user.guest_session_id is None
        assert converted_user.id == test_guest_user.id  # Тот же пользователь
