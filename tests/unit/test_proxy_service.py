"""
Unit тесты для сервиса прокси.

Тестирует получение пользовательских прокси, генерацию списков,
продление подписок, статистику и интеграцию с провайдерами.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest

from app.core.exceptions import BusinessLogicError
from app.services.proxy_service import proxy_service


@pytest.mark.unit
@pytest.mark.asyncio
class TestProxyService:
    """Тесты сервиса прокси."""

    async def test_get_user_proxies_empty(self, db_session, test_user):
        """Тест получения пустого списка прокси пользователя."""
        with patch.object(proxy_service.crud, 'get_user_purchases') as mock_get:
            mock_get.return_value = []

            proxies = await proxy_service.get_user_proxies(
                db_session, user_id=test_user.id
            )

        assert isinstance(proxies, list)
        assert len(proxies) == 0

    async def test_get_user_proxies_with_data(self, db_session, test_user, test_proxy_purchase):
        """Тест получения списка прокси с данными."""
        with patch.object(proxy_service.crud, 'get_user_purchases') as mock_get:
            mock_get.return_value = [test_proxy_purchase]

            proxies = await proxy_service.get_user_proxies(
                db_session, user_id=test_user.id
            )

        assert len(proxies) == 1
        assert proxies[0].id == test_proxy_purchase.id

    async def test_get_user_proxies_active_only(self, db_session, test_user):
        """Тест получения только активных прокси."""
        # Создаем мок данные - активный и неактивный прокси
        active_proxy = MagicMock()
        active_proxy.id = 1
        active_proxy.is_active = True
        active_proxy.expires_at = datetime.now() + timedelta(days=10)

        inactive_proxy = MagicMock()
        inactive_proxy.id = 2
        inactive_proxy.is_active = False
        inactive_proxy.expires_at = datetime.now() - timedelta(days=1)

        with patch.object(proxy_service.crud, 'get_user_purchases') as mock_get:
            # При active_only=True возвращаем только активный
            mock_get.return_value = [active_proxy]

            active_proxies = await proxy_service.get_user_proxies(
                db_session, user_id=test_user.id, active_only=True
            )

            # При active_only=False возвращаем все
            mock_get.return_value = [active_proxy, inactive_proxy]

            all_proxies = await proxy_service.get_user_proxies(
                db_session, user_id=test_user.id, active_only=False
            )

        assert len(active_proxies) == 1
        assert active_proxies[0].is_active is True

        assert len(all_proxies) == 2

    async def test_get_user_proxies_with_pagination(self, db_session, test_user):
        """Тест получения прокси с пагинацией."""
        # Создаем мок список прокси
        mock_proxies = []
        for i in range(10):
            proxy = MagicMock()
            proxy.id = i + 1
            proxy.is_active = True
            mock_proxies.append(proxy)

        with patch.object(proxy_service.crud, 'get_user_purchases') as mock_get:
            # Имитируем пагинацию
            mock_get.return_value = mock_proxies[0:5]  # Первые 5

            first_page = await proxy_service.get_user_proxies(
                db_session, user_id=test_user.id, skip=0, limit=5
            )

            mock_get.return_value = mock_proxies[5:10]  # Следующие 5

            second_page = await proxy_service.get_user_proxies(
                db_session, user_id=test_user.id, skip=5, limit=5
            )

        assert len(first_page) == 5
        assert len(second_page) == 5
        assert first_page[0].id != second_page[0].id

    async def test_get_proxy_details_success(self, db_session, test_user, test_proxy_purchase):
        """Тест получения детальной информации о прокси."""
        with patch.object(proxy_service.crud, 'get_user_purchase') as mock_get:
            mock_get.return_value = test_proxy_purchase

            with patch.object(proxy_service, '_format_proxy_details') as mock_format:
                expected_details = {
                    "id": test_proxy_purchase.id,
                    "proxy_list": ["192.168.1.1:8080", "192.168.1.2:8080"],
                    "credentials": {"username": "testuser", "password": "testpass"},
                    "status": {"is_active": True, "expires_at": "2024-12-31T23:59:59"},
                    "usage": {"traffic_used_gb": "0.00"},
                    "metadata": {}
                }
                mock_format.return_value = expected_details

                details = await proxy_service.get_proxy_details(
                    db_session, purchase_id=test_proxy_purchase.id, user_id=test_user.id
                )

        assert details is not None
        assert details["id"] == test_proxy_purchase.id
        assert "proxy_list" in details
        assert "credentials" in details

    async def test_get_proxy_details_not_found(self, db_session, test_user):
        """Тест получения деталей несуществующего прокси."""
        with patch.object(proxy_service.crud, 'get_user_purchase') as mock_get:
            mock_get.return_value = None

            details = await proxy_service.get_proxy_details(
                db_session, purchase_id=99999, user_id=test_user.id
            )

        assert details is None

    async def test_get_proxy_details_access_denied(self, db_session, test_proxy_purchase):
        """Тест получения деталей прокси другого пользователя."""
        with patch.object(proxy_service.crud, 'get_user_purchase') as mock_get:
            mock_get.return_value = None  # Нет доступа

            with pytest.raises(BusinessLogicError, match="Access denied"):
                await proxy_service.get_proxy_details(
                    db_session, purchase_id=test_proxy_purchase.id, user_id=99999
                )

    async def test_generate_proxy_list_success(self, db_session, test_user, test_proxy_purchase):
        """Тест генерации списка прокси."""
        with patch.object(proxy_service.crud, 'get_user_purchase') as mock_get:
            mock_get.return_value = test_proxy_purchase

            result = await proxy_service.generate_proxy_list(
                db_session,
                purchase_id=test_proxy_purchase.id,
                user_id=test_user.id,
                format_type="ip:port:user:pass"
            )

        assert result is not None
        assert "purchase_id" in result
        assert "proxy_count" in result
        assert "format" in result
        assert "proxies" in result
        assert result["format"] == "ip:port:user:pass"

    async def test_generate_proxy_list_different_formats(self, db_session, test_user, test_proxy_purchase):
        """Тест генерации списков в разных форматах."""
        formats_to_test = [
            "ip:port:user:pass",
            "user:pass@ip:port",
            "ip:port",
            "https://user:pass@ip:port"
        ]

        with patch.object(proxy_service.crud, 'get_user_purchase') as mock_get:
            mock_get.return_value = test_proxy_purchase

            for format_type in formats_to_test:
                result = await proxy_service.generate_proxy_list(
                    db_session,
                    purchase_id=test_proxy_purchase.id,
                    user_id=test_user.id,
                    format_type=format_type
                )

                assert result["format"] == format_type
                assert len(result["proxies"]) > 0

    async def test_extend_proxy_subscription_success(self, db_session, test_user, test_proxy_purchase):
        """Тест успешного продления подписки прокси."""
        test_user.balance = Decimal("50.00")  # Достаточно средств

        with patch.object(proxy_service.crud, 'get_user_purchase') as mock_get:
            mock_get.return_value = test_proxy_purchase

            with patch.object(proxy_service.crud, 'extend_purchase') as mock_extend:
                extended_purchase = MagicMock()
                extended_purchase.expires_at = datetime.now() + timedelta(days=45)
                mock_extend.return_value = extended_purchase

                with patch.object(proxy_service, '_calculate_extension_cost') as mock_cost:
                    mock_cost.return_value = Decimal("15.00")

                    result = await proxy_service.extend_proxy_subscription(
                        db_session,
                        purchase_id=test_proxy_purchase.id,
                        user_id=test_user.id,
                        days=15
                    )

        assert result is not None
        assert "purchase_id" in result
        assert "extended_days" in result
        assert "new_expires_at" in result
        assert "cost" in result

    async def test_extend_proxy_subscription_insufficient_balance(self, db_session, test_user, test_proxy_purchase):
        """Тест продления при недостаточном балансе."""
        test_user.balance = Decimal("5.00")  # Недостаточно средств

        with patch.object(proxy_service.crud, 'get_user_purchase') as mock_get:
            mock_get.return_value = test_proxy_purchase

            with patch.object(proxy_service, '_calculate_extension_cost') as mock_cost:
                mock_cost.return_value = Decimal("20.00")  # Больше чем баланс

                with pytest.raises(BusinessLogicError, match="Insufficient balance"):
                    await proxy_service.extend_proxy_subscription(
                        db_session,
                        purchase_id=test_proxy_purchase.id,
                        user_id=test_user.id,
                        days=30
                    )

    async def test_extend_proxy_subscription_expired(self, db_session, test_user):
        """Тест продления истекшего прокси."""
        expired_purchase = MagicMock()
        expired_purchase.id = 1
        expired_purchase.is_active = False
        expired_purchase.expires_at = datetime.now() - timedelta(days=5)

        with patch.object(proxy_service.crud, 'get_user_purchase') as mock_get:
            mock_get.return_value = expired_purchase

            with pytest.raises(BusinessLogicError, match="Cannot extend expired or inactive proxy"):
                await proxy_service.extend_proxy_subscription(
                    db_session,
                    purchase_id=expired_purchase.id,
                    user_id=test_user.id,
                    days=30
                )

    async def test_get_expiring_proxies(self, db_session, test_user):
        """Тест получения истекающих прокси."""
        # Создаем мок истекающих прокси
        expiring_proxies = []
        for i in range(3):
            proxy = MagicMock()
            proxy.id = i + 1
            proxy.expires_at = datetime.now() + timedelta(days=i + 1)  # 1, 2, 3 дня
            proxy.is_active = True
            expiring_proxies.append(proxy)

        with patch.object(proxy_service.crud, 'get_expiring_purchases') as mock_get:
            mock_get.return_value = expiring_proxies

            result = await proxy_service.get_expiring_proxies(
                db_session, user_id=test_user.id, days_ahead=7
            )

        assert len(result) == 3
        mock_get.assert_called_once_with(db_session, user_id=test_user.id, days_ahead=7)

    async def test_get_proxy_statistics(self, db_session, test_user):
        """Тест получения статистики прокси пользователя."""
        with patch.object(proxy_service.crud, 'get_user_purchases') as mock_get_purchases:
            # Мок данные для статистики
            mock_purchases = []
            for i in range(5):
                purchase = MagicMock()
                purchase.id = i + 1
                purchase.is_active = i < 3  # 3 активных, 2 неактивных
                purchase.traffic_used_gb = Decimal(f"{i * 2}.5")
                purchase.created_at = datetime.now() - timedelta(days=i * 10)
                mock_purchases.append(purchase)

            mock_get_purchases.return_value = mock_purchases

            stats = await proxy_service.get_proxy_statistics(
                db_session, user_id=test_user.id, days=30
            )

        assert stats is not None
        assert "total_purchases" in stats
        assert "active_purchases" in stats
        assert "total_traffic_used_gb" in stats
        assert "period_days" in stats
        assert stats["total_purchases"] == 5
        assert stats["active_purchases"] == 3

    async def test_deactivate_proxy_success(self, db_session, test_user, test_proxy_purchase):
        """Тест успешной деактивации прокси."""
        with patch.object(proxy_service.crud, 'get_user_purchase') as mock_get:
            mock_get.return_value = test_proxy_purchase

            with patch.object(proxy_service.crud, 'deactivate_purchase') as mock_deactivate:
                mock_deactivate.return_value = True

                result = await proxy_service.deactivate_proxy(
                    db_session,
                    purchase_id=test_proxy_purchase.id,
                    user_id=test_user.id,
                    reason="User request"
                )

        assert result is True
        mock_deactivate.assert_called_once()

    async def test_deactivate_proxy_not_found(self, db_session, test_user):
        """Тест деактивации несуществующего прокси."""
        with patch.object(proxy_service.crud, 'get_user_purchase') as mock_get:
            mock_get.return_value = None

            result = await proxy_service.deactivate_proxy(
                db_session,
                purchase_id=99999,
                user_id=test_user.id
            )

        assert result is False

    async def test_deactivate_proxy_already_inactive(self, db_session, test_user):
        """Тест деактивации уже неактивного прокси."""
        inactive_purchase = MagicMock()
        inactive_purchase.id = 1
        inactive_purchase.is_active = False

        with patch.object(proxy_service.crud, 'get_user_purchase') as mock_get:
            mock_get.return_value = inactive_purchase

            with pytest.raises(BusinessLogicError, match="Proxy is already inactive"):
                await proxy_service.deactivate_proxy(
                    db_session,
                    purchase_id=inactive_purchase.id,
                    user_id=test_user.id
                )

    @patch('app.integrations.proxy_711.proxy_711_api.get_proxy_status')
    async def test_sync_proxy_status_with_provider(self, mock_get_status, db_session, test_proxy_purchase):
        """Тест синхронизации статуса прокси с провайдером."""
        mock_get_status.return_value = {
            "order_id": "711_order_123",
            "status": "active",
            "expires_at": "2024-12-31T23:59:59Z",
            "traffic_used": "5.2 GB"
        }

        with patch.object(proxy_service.crud, 'get') as mock_get:
            mock_get.return_value = test_proxy_purchase

            with patch.object(proxy_service.crud, 'update') as mock_update:
                mock_update.return_value = test_proxy_purchase

                result = await proxy_service.sync_proxy_status_with_provider(
                    db_session, purchase_id=test_proxy_purchase.id
                )

        assert result is not None
        mock_get_status.assert_called_once()

    async def test_calculate_extension_cost(self, test_proxy_product):
        """Тест расчета стоимости продления."""
        # Создаем мок покупки
        purchase = MagicMock()
        purchase.proxy_product = test_proxy_product

        days_to_extend = 15

        cost = proxy_service._calculate_extension_cost(purchase, days_to_extend)

        # Стоимость должна быть пропорциональна
        expected_daily_cost = test_proxy_product.price_per_proxy / test_proxy_product.duration_days
        expected_total = expected_daily_cost * days_to_extend

        assert cost == expected_total

    async def test_format_proxy_details(self, test_proxy_purchase):
        """Тест форматирования деталей прокси."""
        details = proxy_service._format_proxy_details(test_proxy_purchase)

        assert isinstance(details, dict)
        assert "id" in details
        assert "proxy_list" in details
        assert "credentials" in details
        assert "status" in details
        assert "usage" in details
        assert "metadata" in details

    async def test_parse_proxy_list_string(self):
        """Тест парсинга строки списка прокси."""
        proxy_string = "192.168.1.1:8080:user:pass\n192.168.1.2:8080:user:pass\n192.168.1.3:8080:user:pass"

        parsed_proxies = proxy_service._parse_proxy_list(proxy_string)

        assert len(parsed_proxies) == 3
        assert all("ip" in proxy for proxy in parsed_proxies)
        assert all("port" in proxy for proxy in parsed_proxies)

    async def test_validate_extension_params(self):
        """Тест валидации параметров продления."""
        # Валидные параметры
        proxy_service._validate_extension_params(days=30)

        # Невалидные параметры
        with pytest.raises(ValueError, match="Days must be positive"):
            proxy_service._validate_extension_params(days=0)

        with pytest.raises(ValueError, match="Cannot extend for more than"):
            proxy_service._validate_extension_params(days=500)

    async def test_check_proxy_health(self, db_session, test_proxy_purchase):
        """Тест проверки работоспособности прокси."""
        with patch.object(proxy_service, '_test_proxy_connection') as mock_test:
            mock_test.return_value = {
                "working_proxies": 2,
                "total_proxies": 2,
                "average_response_time": 150.5,
                "failed_proxies": []
            }

            health_result = await proxy_service.check_proxy_health(
                db_session, purchase_id=test_proxy_purchase.id
            )

        assert health_result is not None
        assert health_result["working_proxies"] == 2
        assert health_result["success_rate"] == 100.0

    async def test_bulk_deactivate_expired_proxies(self, db_session):
        """Тест массовой деактивации истекших прокси."""
        with patch.object(proxy_service.crud, 'get_expired_purchases') as mock_get_expired:
            expired_purchases = [MagicMock() for _ in range(3)]
            mock_get_expired.return_value = expired_purchases

            with patch.object(proxy_service.crud, 'bulk_deactivate') as mock_bulk_deactivate:
                mock_bulk_deactivate.return_value = 3

                deactivated_count = await proxy_service.bulk_deactivate_expired_proxies(db_session)

        assert deactivated_count == 3

    async def test_get_proxy_usage_logs(self, db_session, test_proxy_purchase):
        """Тест получения логов использования прокси."""
        with patch.object(proxy_service, '_get_usage_logs_from_provider') as mock_get_logs:
            mock_logs = [
                {
                    "timestamp": "2024-01-15T10:30:00Z",
                    "traffic_mb": 150.5,
                    "success": True
                }
            ]
            mock_get_logs.return_value = mock_logs

            logs = await proxy_service.get_proxy_usage_logs(
                db_session, purchase_id=test_proxy_purchase.id
            )

        assert len(logs) == 1
        assert logs[0]["traffic_mb"] == 150.5
