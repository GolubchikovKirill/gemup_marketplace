"""
Unit тесты для CRUD операций с пользователями.

Тестирует создание, обновление, поиск и аутентификацию пользователей.
"""

import uuid
from datetime import datetime
from decimal import Decimal

import pytest

from app.crud.user import user_crud
from app.schemas.user import UserCreate, UserUpdate, GuestUserCreate


@pytest.mark.unit
@pytest.mark.asyncio
class TestUserCRUD:
    """Тесты CRUD операций пользователей."""

    async def test_create_registered_user_success(self, db_session):
        """Тест успешного создания зарегистрированного пользователя."""
        unique_id = str(uuid.uuid4())[:8]

        user_data = UserCreate(
            email=f"testuser-{unique_id}@example.com",
            username=f"testuser-{unique_id}",
            password="securepassword123",
            first_name="Test",
            last_name="User"
        )

        user = await user_crud.create_registered_user(db_session, user_in=user_data)

        assert user.email == f"testuser-{unique_id}@example.com"
        assert user.username == f"testuser-{unique_id}"
        assert user.first_name == "Test"
        assert user.last_name == "User"
        assert user.is_guest is False
        assert user.is_active is True
        assert user.hashed_password != "securepassword123"  # Должен быть захеширован
        assert user.balance == Decimal('0.00')

    async def test_create_user_duplicate_email(self, db_session, test_user):
        """Тест создания пользователя с существующим email."""
        user_data = UserCreate(
            email=test_user.email,  # Дублирующий email
            username="newusername",
            password="password123",
            first_name="New",
            last_name="User"
        )

        with pytest.raises(Exception):  # Должна быть ошибка уникальности
            await user_crud.create_registered_user(db_session, user_in=user_data)

    async def test_create_user_duplicate_username(self, db_session, test_user):
        """Тест создания пользователя с существующим username."""
        unique_id = str(uuid.uuid4())[:8]

        user_data = UserCreate(
            email=f"newemail-{unique_id}@example.com",
            username=test_user.username,  # Дублирующий username
            password="password123",
            first_name="New",
            last_name="User"
        )

        with pytest.raises(Exception):  # Должна быть ошибка уникальности
            await user_crud.create_registered_user(db_session, user_in=user_data)

    async def test_get_user_by_id(self, db_session, test_user):
        """Тест получения пользователя по ID."""
        found_user = await user_crud.get(db_session, obj_id=test_user.id)

        assert found_user is not None
        assert found_user.id == test_user.id
        assert found_user.email == test_user.email

    async def test_get_user_by_id_not_found(self, db_session):
        """Тест получения несуществующего пользователя."""
        found_user = await user_crud.get(db_session, obj_id=99999)

        assert found_user is None

    async def test_get_user_by_email(self, db_session, test_user):
        """Тест получения пользователя по email."""
        found_user = await user_crud.get_by_email(db_session, email=test_user.email)

        assert found_user is not None
        assert found_user.email == test_user.email
        assert found_user.id == test_user.id

    async def test_get_user_by_email_not_found(self, db_session):
        """Тест получения пользователя по несуществующему email."""
        found_user = await user_crud.get_by_email(db_session, email="nonexistent@example.com")

        assert found_user is None

    async def test_get_user_by_username(self, db_session, test_user):
        """Тест получения пользователя по username."""
        found_user = await user_crud.get_by_username(db_session, username=test_user.username)

        assert found_user is not None
        assert found_user.username == test_user.username
        assert found_user.id == test_user.id

    async def test_get_user_by_username_not_found(self, db_session):
        """Тест получения пользователя по несуществующему username."""
        found_user = await user_crud.get_by_username(db_session, username="nonexistent")

        assert found_user is None

    async def test_authenticate_user_success(self, db_session, test_user):
        """Тест успешной аутентификации пользователя."""
        authenticated_user = await user_crud.authenticate(
            db_session,
            email=test_user.email,
            password="testpassword123"  # Пароль из фикстуры
        )

        assert authenticated_user is not None
        assert authenticated_user.id == test_user.id
        assert authenticated_user.email == test_user.email

    async def test_authenticate_user_wrong_password(self, db_session, test_user):
        """Тест аутентификации с неверным паролем."""
        authenticated_user = await user_crud.authenticate(
            db_session,
            email=test_user.email,
            password="wrongpassword"
        )

        assert authenticated_user is None

    async def test_authenticate_user_not_found(self, db_session):
        """Тест аутентификации несуществующего пользователя."""
        authenticated_user = await user_crud.authenticate(
            db_session,
            email="nonexistent@example.com",
            password="anypassword"
        )

        assert authenticated_user is None

    async def test_update_user(self, db_session, test_user):
        """Тест обновления пользователя."""
        update_data = UserUpdate(
            first_name="Updated",
            last_name="Name"
        )

        updated_user = await user_crud.update(db_session, db_obj=test_user, obj_in=update_data)

        assert updated_user.first_name == "Updated"
        assert updated_user.last_name == "Name"
        assert updated_user.email == test_user.email  # Не изменилось

    async def test_update_user_password(self, db_session, test_user):
        """Тест обновления пароля пользователя."""
        old_password_hash = test_user.hashed_password

        update_data = UserUpdate(password="newpassword123")
        updated_user = await user_crud.update(db_session, db_obj=test_user, obj_in=update_data)

        assert updated_user.hashed_password != old_password_hash
        assert updated_user.hashed_password != "newpassword123"  # Должен быть захеширован

        # Проверяем что новый пароль работает
        authenticated = await user_crud.authenticate(
            db_session, email=test_user.email, password="newpassword123"
        )
        assert authenticated is not None

    async def test_update_balance(self, db_session, test_user):
        """Тест обновления баланса пользователя."""
        initial_balance = test_user.balance
        amount_to_add = Decimal("25.50")

        updated_user = await user_crud.update_balance(db_session, user=test_user, amount=amount_to_add)

        assert updated_user.balance == initial_balance + amount_to_add

    async def test_update_balance_negative(self, db_session, test_user):
        """Тест списания с баланса."""
        # Устанавливаем начальный баланс
        test_user.balance = Decimal("50.00")
        await db_session.commit()

        amount_to_subtract = Decimal("-20.00")
        updated_user = await user_crud.update_balance(db_session, user=test_user, amount=amount_to_subtract)

        assert updated_user.balance == Decimal("30.00")

    async def test_update_balance_insufficient_funds(self, db_session, test_user):
        """Тест списания больше чем есть на балансе."""
        # Устанавливаем малый баланс
        test_user.balance = Decimal("10.00")
        await db_session.commit()

        amount_to_subtract = Decimal("-50.00")

        # В зависимости от реализации, может быть ошибка или отрицательный баланс
        updated_user = await user_crud.update_balance(db_session, user=test_user, amount=amount_to_subtract)
        assert updated_user.balance == Decimal("-40.00")  # Или должна быть ошибка

    async def test_create_guest_user(self, db_session):
        """Тест создания гостевого пользователя."""
        session_id = f"guest-session-{str(uuid.uuid4())[:8]}"
        guest_data = GuestUserCreate(session_id=session_id)

        guest_user = await user_crud.create_guest_user(db_session, obj_in=guest_data)

        assert guest_user.is_guest is True
        assert guest_user.guest_session_id == session_id
        assert guest_user.guest_expires_at is not None
        assert guest_user.guest_expires_at > datetime.now()
        assert guest_user.email is None
        assert guest_user.username is None

    async def test_get_guest_by_session_id(self, db_session, test_guest_user):
        """Тест получения гостевого пользователя по session_id."""
        found_guest = await user_crud.get_guest_by_session_id(
            db_session, session_id=test_guest_user.guest_session_id
        )

        assert found_guest is not None
        assert found_guest.id == test_guest_user.id
        assert found_guest.guest_session_id == test_guest_user.guest_session_id

    async def test_get_guest_by_session_id_not_found(self, db_session):
        """Тест получения несуществующего гостя."""
        found_guest = await user_crud.get_guest_by_session_id(
            db_session, session_id="nonexistent-session"
        )

        assert found_guest is None

    async def test_convert_guest_to_registered(self, db_session, test_guest_user):
        """Тест конвертации гостевого пользователя в зарегистрированного."""
        unique_id = str(uuid.uuid4())[:8]

        user_data = UserCreate(
            email=f"converted-{unique_id}@example.com",
            username=f"converted-{unique_id}",
            password="password123",
            first_name="Converted",
            last_name="User"
        )

        original_balance = test_guest_user.balance

        converted_user = await user_crud.convert_guest_to_registered(
            db_session, guest_user=test_guest_user, user_data=user_data
        )

        assert converted_user.id == test_guest_user.id  # Тот же пользователь
        assert converted_user.is_guest is False
        assert converted_user.email == f"converted-{unique_id}@example.com"
        assert converted_user.username == f"converted-{unique_id}"
        assert converted_user.guest_session_id is None
        assert converted_user.guest_expires_at is None
        assert converted_user.balance == original_balance  # Баланс сохранился

    async def test_update_last_login(self, db_session, test_user):
        """Тест обновления времени последнего входа."""
        old_last_login = test_user.last_login

        await user_crud.update_last_login(db_session, user_id=test_user.id)
        await db_session.refresh(test_user)

        assert test_user.last_login != old_last_login
        assert test_user.last_login is not None
        # Проверяем что время недавнее (в пределах минуты)
        assert (datetime.now() - test_user.last_login).total_seconds() < 60

    async def test_deactivate_user(self, db_session, test_user):
        """Тест деактивации пользователя."""
        assert test_user.is_active is True

        await user_crud.deactivate_user(db_session, user_id=test_user.id)
        await db_session.refresh(test_user)

        assert test_user.is_active is False

    async def test_get_user_order_stats(self, db_session, test_user):
        """Тест получения статистики заказов пользователя."""
        stats = await user_crud.get_user_order_stats(db_session, user_id=test_user.id)

        assert isinstance(stats, dict)
        assert "total_orders" in stats
        assert "total_amount" in stats
        assert "last_order_date" in stats
        assert "average_amount" in stats

    async def test_get_user_proxy_stats(self, db_session, test_user):
        """Тест получения статистики прокси пользователя."""
        stats = await user_crud.get_user_proxy_stats(db_session, user_id=test_user.id)

        assert isinstance(stats, dict)
        assert "active_count" in stats
        assert "total_purchased" in stats

    async def test_get_multi_users(self, db_session, test_user):
        """Тест получения списка пользователей."""
        users = await user_crud.get_multi(db_session, skip=0, limit=10)

        assert isinstance(users, list)
        assert len(users) >= 1
        assert any(user.id == test_user.id for user in users)

    async def test_delete_user(self, db_session, test_user):
        """Тест удаления пользователя."""
        user_id = test_user.id

        result = await user_crud.delete(db_session, obj_id=user_id)
        assert result is not None

        # Проверяем что пользователь удален
        deleted_user = await user_crud.get(db_session, obj_id=user_id)
        assert deleted_user is None
