"""
Unit тесты для сервиса аутентификации.

Тестирует регистрацию, аутентификацию, управление токенами,
смену паролей и восстановление доступа.
"""

from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest

from app.core.auth import auth_handler
from app.core.exceptions import BusinessLogicError
from app.schemas.user import UserCreate, UserLogin
from app.services.auth_service import auth_service


@pytest.mark.unit
@pytest.mark.asyncio
class TestAuthService:
    """Тесты сервиса аутентификации."""

    async def test_register_user_success(self, db_session):
        """Тест успешной регистрации пользователя."""
        user_data = UserCreate(
            email="newuser@example.com",
            username="newuser123",
            password="SecurePassword123!",
            first_name="New",
            last_name="User"
        )

        with patch.object(auth_service.user_crud, 'get_by_email') as mock_get_email:
            mock_get_email.return_value = None  # Email не существует

            with patch.object(auth_service.user_crud, 'get_by_username') as mock_get_username:
                mock_get_username.return_value = None  # Username не существует

                with patch.object(auth_service.user_crud, 'create_registered_user') as mock_create:
                    mock_user = MagicMock()
                    mock_user.id = 1
                    mock_user.email = user_data.email
                    mock_user.username = user_data.username
                    mock_user.is_active = True
                    mock_create.return_value = mock_user

                    result = await auth_service.register_user(db_session, user_data)

        assert result is not None
        assert "user" in result
        assert "access_token" in result
        assert "refresh_token" in result
        mock_create.assert_called_once()

    async def test_register_user_email_exists(self, db_session, test_user):
        """Тест регистрации с существующим email."""
        user_data = UserCreate(
            email=test_user.email,  # Существующий email
            username="newusername",
            password="SecurePassword123!",
            first_name="New",
            last_name="User"
        )

        with patch.object(auth_service.user_crud, 'get_by_email') as mock_get_email:
            mock_get_email.return_value = test_user

            with pytest.raises(BusinessLogicError, match="Email already exists"):
                await auth_service.register_user(db_session, user_data)

    async def test_register_user_username_exists(self, db_session, test_user):
        """Тест регистрации с существующим username."""
        user_data = UserCreate(
            email="newemail@example.com",
            username=test_user.username,  # Существующий username
            password="SecurePassword123!",
            first_name="New",
            last_name="User"
        )

        with patch.object(auth_service.user_crud, 'get_by_email') as mock_get_email:
            mock_get_email.return_value = None

            with patch.object(auth_service.user_crud, 'get_by_username') as mock_get_username:
                mock_get_username.return_value = test_user

                with pytest.raises(BusinessLogicError, match="Username already exists"):
                    await auth_service.register_user(db_session, user_data)

    async def test_authenticate_user_success(self, db_session, test_user):
        """Тест успешной аутентификации."""
        login_data = UserLogin(
            email=test_user.email,
            password="testpassword123"
        )

        with patch.object(auth_service.user_crud, 'authenticate') as mock_auth:
            mock_auth.return_value = test_user

            with patch.object(auth_service.user_crud, 'update_last_login') as mock_update_login:
                result = await auth_service.authenticate_user(db_session, login_data)

        assert result is not None
        assert "user" in result
        assert "access_token" in result
        assert "refresh_token" in result
        mock_update_login.assert_called_once()

    async def test_authenticate_user_invalid_credentials(self, db_session):
        """Тест аутентификации с неверными данными."""
        login_data = UserLogin(
            email="wrong@example.com",
            password="wrongpassword"
        )

        with patch.object(auth_service.user_crud, 'authenticate') as mock_auth:
            mock_auth.return_value = None

            with pytest.raises(BusinessLogicError, match="Invalid credentials"):
                await auth_service.authenticate_user(db_session, login_data)

    async def test_authenticate_user_inactive(self, db_session, test_user):
        """Тест аутентификации неактивного пользователя."""
        test_user.is_active = False

        login_data = UserLogin(
            email=test_user.email,
            password="testpassword123"
        )

        with patch.object(auth_service.user_crud, 'authenticate') as mock_auth:
            mock_auth.return_value = test_user

            with pytest.raises(BusinessLogicError, match="Account is inactive"):
                await auth_service.authenticate_user(db_session, login_data)

    async def test_refresh_token_success(self, db_session, test_user):
        """Тест успешного обновления токена."""
        # Создаем валидный refresh token
        refresh_token = auth_handler.create_refresh_token(
            data={"sub": str(test_user.id), "type": "refresh"}
        )

        with patch.object(auth_service.user_crud, 'get') as mock_get:
            mock_get.return_value = test_user

            result = await auth_service.refresh_user_token(db_session, refresh_token)

        assert result is not None
        assert "access_token" in result
        assert "expires_in" in result

    async def test_refresh_token_invalid(self, db_session):
        """Тест обновления с невалидным токеном."""
        invalid_token = "invalid.token.here"

        with pytest.raises(BusinessLogicError, match="Invalid refresh token"):
            await auth_service.refresh_user_token(db_session, invalid_token)

    async def test_change_password_success(self, db_session, test_user):
        """Тест успешной смены пароля."""
        current_password = "testpassword123"
        new_password = "NewSecurePassword456!"

        with patch.object(auth_service.user_crud, 'authenticate') as mock_auth:
            mock_auth.return_value = test_user  # Текущий пароль верный

            with patch.object(auth_service.user_crud, 'update') as mock_update:
                mock_update.return_value = test_user

                result = await auth_service.change_password(
                    db_session, test_user, current_password, new_password
                )

        assert result is True
        mock_update.assert_called_once()

    async def test_change_password_wrong_current(self, db_session, test_user):
        """Тест смены пароля с неверным текущим паролем."""
        current_password = "wrongpassword"
        new_password = "NewSecurePassword456!"

        with patch.object(auth_service.user_crud, 'authenticate') as mock_auth:
            mock_auth.return_value = None  # Неверный текущий пароль

            with pytest.raises(BusinessLogicError, match="Current password is incorrect"):
                await auth_service.change_password(
                    db_session, test_user, current_password, new_password
                )

    async def test_generate_password_reset_token(self, db_session, test_user):
        """Тест генерации токена для сброса пароля."""
        with patch.object(auth_service.user_crud, 'get_by_email') as mock_get:
            mock_get.return_value = test_user

            with patch.object(auth_service.user_crud, 'update') as mock_update:
                mock_update.return_value = test_user

                result = await auth_service.generate_password_reset_token(
                    db_session, test_user.email
                )

        assert result is not None
        assert "reset_token" in result
        assert "expires_at" in result
        mock_update.assert_called_once()  # Сохранили токен в БД

    async def test_generate_password_reset_token_user_not_found(self, db_session):
        """Тест генерации токена для несуществующего пользователя."""
        with patch.object(auth_service.user_crud, 'get_by_email') as mock_get:
            mock_get.return_value = None

            with pytest.raises(BusinessLogicError, match="User not found"):
                await auth_service.generate_password_reset_token(
                    db_session, "nonexistent@example.com"
                )

    async def test_reset_password_with_token_success(self, db_session, test_user):
        """Тест успешного сброса пароля по токену."""
        reset_token = "valid_reset_token_123"
        new_password = "NewResetPassword789!"

        # Устанавливаем валидный токен сброса
        test_user.password_reset_token = reset_token
        test_user.password_reset_expires = datetime.now() + timedelta(hours=1)

        with patch.object(auth_service.user_crud, 'get_by_reset_token') as mock_get:
            mock_get.return_value = test_user

            with patch.object(auth_service.user_crud, 'update') as mock_update:
                mock_update.return_value = test_user

                result = await auth_service.reset_password_with_token(
                    db_session, reset_token, new_password
                )

        assert result is True
        mock_update.assert_called_once()

    async def test_reset_password_with_expired_token(self, db_session, test_user):
        """Тест сброса пароля с истекшим токеном."""
        reset_token = "expired_token_123"
        new_password = "NewResetPassword789!"

        # Устанавливаем истекший токен
        test_user.password_reset_token = reset_token
        test_user.password_reset_expires = datetime.now() - timedelta(hours=1)

        with patch.object(auth_service.user_crud, 'get_by_reset_token') as mock_get:
            mock_get.return_value = test_user

            with pytest.raises(BusinessLogicError, match="Reset token has expired"):
                await auth_service.reset_password_with_token(
                    db_session, reset_token, new_password
                )

    async def test_logout_user_success(self, db_session, test_user):
        """Тест успешного выхода пользователя."""
        access_token = auth_handler.create_access_token(
            data={"sub": str(test_user.id), "type": "access"}
        )

        with patch.object(auth_service, '_blacklist_token') as mock_blacklist:
            result = await auth_service.logout_user(db_session, access_token)

        assert result is True
        mock_blacklist.assert_called_once_with(access_token)

    async def test_validate_user_data_success(self):
        """Тест успешной валидации данных пользователя."""
        user_data = UserCreate(
            email="valid@example.com",
            username="validuser123",
            password="ValidPassword123!",
            first_name="Valid",
            last_name="User"
        )

        # Не должно вызывать исключений
        auth_service._validate_user_data(user_data)

    async def test_validate_user_data_weak_password(self):
        """Тест валидации со слабым паролем."""
        user_data = UserCreate(
            email="test@example.com",
            username="testuser",
            password="123",  # Слабый пароль
            first_name="Test",
            last_name="User"
        )

        with pytest.raises(BusinessLogicError, match="Password is too weak"):
            auth_service._validate_user_data(user_data)

    async def test_validate_user_data_invalid_email(self):
        """Тест валидации с невалидным email."""
        # Это будет обработано на уровне Pydantic схемы
        with pytest.raises(ValueError):
            UserCreate(
                email="invalid-email",  # Невалидный email
                username="testuser",
                password="ValidPassword123!",
                first_name="Test",
                last_name="User"
            )

    async def test_check_rate_limiting(self, db_session):
        """Тест проверки лимитов на попытки входа."""
        ip_address = "192.168.1.100"

        with patch.object(auth_service, '_get_failed_attempts') as mock_get_attempts:
            mock_get_attempts.return_value = 3  # Меньше лимита

            result = auth_service._check_rate_limiting(ip_address)
            assert result is True

        with patch.object(auth_service, '_get_failed_attempts') as mock_get_attempts:
            mock_get_attempts.return_value = 10  # Превышение лимита

            result = auth_service._check_rate_limiting(ip_address)
            assert result is False

    async def test_generate_tokens(self, test_user):
        """Тест генерации пары токенов."""
        tokens = auth_service._generate_tokens(test_user)

        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "token_type" in tokens
        assert "expires_in" in tokens
        assert tokens["token_type"] == "bearer"

    async def test_verify_email_success(self, db_session, test_user):
        """Тест успешной верификации email."""
        verification_token = "email_verification_token_123"
        test_user.email_verification_token = verification_token
        test_user.is_verified = False

        with patch.object(auth_service.user_crud, 'get_by_verification_token') as mock_get:
            mock_get.return_value = test_user

            with patch.object(auth_service.user_crud, 'update') as mock_update:
                mock_updated_user = MagicMock()
                mock_updated_user.is_verified = True
                mock_update.return_value = mock_updated_user

                result = await auth_service.verify_email(db_session, verification_token)

        assert result is True
        mock_update.assert_called_once()

    async def test_send_verification_email(self, db_session, test_user):
        """Тест отправки письма для верификации."""
        with patch.object(auth_service, '_generate_verification_token') as mock_gen_token:
            mock_gen_token.return_value = "verification_token_123"

            with patch.object(auth_service, '_send_email') as mock_send:
                mock_send.return_value = True

                result = await auth_service.send_verification_email(db_session, test_user)

        assert result is True
        mock_send.assert_called_once()

    async def test_convert_guest_to_registered(self, db_session, test_guest_user):
        """Тест конвертации гостевого пользователя в зарегистрированного."""
        user_data = UserCreate(
            email="converted@example.com",
            username="converteduser",
            password="ConvertedPassword123!",
            first_name="Converted",
            last_name="User"
        )

        with patch.object(auth_service.user_crud, 'convert_guest_to_registered') as mock_convert:
            mock_converted_user = MagicMock()
            mock_converted_user.id = test_guest_user.id
            mock_converted_user.email = user_data.email
            mock_converted_user.is_guest = False
            mock_convert.return_value = mock_converted_user

            result = await auth_service.convert_guest_to_registered(
                db_session, test_guest_user, user_data
            )

        assert result is not None
        assert "user" in result
        assert "access_token" in result
        mock_convert.assert_called_once()
