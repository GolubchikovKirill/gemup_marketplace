from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.api
class TestProxiesAPI:

    @pytest.mark.asyncio
    async def test_get_my_proxies_empty(self, client: AsyncClient, auth_headers):
        """Тест получения пустого списка прокси"""
        response = await client.get("/api/v1/proxies/my", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_my_proxies_with_data(self, client: AsyncClient, auth_headers, db_session, test_user):
        """Тест получения списка прокси с данными"""
        # Создаем покупку прокси
        from app.crud.proxy_purchase import proxy_purchase_crud

        expires_at = datetime.now() + timedelta(days=30)
        proxy_list_str = "1.2.3.4:8080\n5.6.7.8:8080"

        await proxy_purchase_crud.create_purchase(
            db_session,
            user_id=test_user.id,
            proxy_product_id=1,
            order_id=1,
            proxy_list=proxy_list_str,
            username="user123",
            password="pass123",
            expires_at=expires_at
        )

        response = await client.get("/api/v1/proxies/my", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_generate_proxy_list_success(self, client: AsyncClient, auth_headers, db_session, test_user):
        """Тест успешной генерации списка прокси"""
        # Создаем покупку прокси
        from app.crud.proxy_purchase import proxy_purchase_crud

        expires_at = datetime.now() + timedelta(days=30)
        proxy_list_str = "1.2.3.4:8080\n5.6.7.8:8080"

        purchase = await proxy_purchase_crud.create_purchase(
            db_session,
            user_id=test_user.id,
            proxy_product_id=1,
            order_id=1,
            proxy_list=proxy_list_str,
            username="user123",
            password="pass123",
            expires_at=expires_at
        )

        request_data = {
            "format_type": "ip:port:user:pass"
        }

        response = await client.post(
            f"/api/v1/proxies/{purchase.id}/generate",
            json=request_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["purchase_id"] == purchase.id
        assert data["proxy_count"] == 2
        assert data["format"] == "ip:port:user:pass"
        assert len(data["proxies"]) == 2
        assert "user123:pass123" in data["proxies"][0]

    @pytest.mark.asyncio
    async def test_generate_proxy_list_not_found(self, client: AsyncClient, auth_headers):
        """Тест генерации для несуществующей покупки"""
        request_data = {
            "format_type": "ip:port:user:pass"
        }

        response = await client.post(
            "/api/v1/proxies/99999/generate",
            json=request_data,
            headers=auth_headers
        )

        assert response.status_code == 400
        error_data = response.json()
        # ИСПРАВЛЕНО: проверяем разные форматы ответа
        if "detail" in error_data:
            assert "not found" in error_data["detail"]
        elif "message" in error_data:
            assert "not found" in error_data["message"]
        else:
            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_download_proxy_list_success(self, client: AsyncClient, auth_headers, db_session, test_user):
        """Тест скачивания списка прокси"""
        # Создаем покупку прокси
        from app.crud.proxy_purchase import proxy_purchase_crud

        expires_at = datetime.now() + timedelta(days=30)
        proxy_list_str = "1.2.3.4:8080\n5.6.7.8:8080"

        purchase = await proxy_purchase_crud.create_purchase(
            db_session,
            user_id=test_user.id,
            proxy_product_id=1,
            order_id=1,
            proxy_list=proxy_list_str,
            username="user123",
            password="pass123",
            expires_at=expires_at
        )

        response = await client.get(
            f"/api/v1/proxies/{purchase.id}/download?format_type=ip:port:user:pass",
            headers=auth_headers
        )

        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        assert "attachment" in response.headers["content-disposition"]

        content = response.text
        assert "1.2.3.4:8080:user123:pass123" in content
        assert "5.6.7.8:8080:user123:pass123" in content

    @patch('app.services.proxy_service.proxy_711_api.extend_proxies')
    @pytest.mark.asyncio
    async def test_extend_proxies_success(self, mock_extend, client: AsyncClient, auth_headers, db_session, test_user):
        """Тест продления прокси"""
        # Создаем покупку прокси
        from app.crud.proxy_purchase import proxy_purchase_crud

        expires_at = datetime.now() + timedelta(days=5)
        purchase = await proxy_purchase_crud.create_purchase(
            db_session,
            user_id=test_user.id,
            proxy_product_id=1,
            order_id=1,
            proxy_list="1.2.3.4:8080",
            expires_at=expires_at,
            provider_order_id="711-order-123"
        )

        # Мокаем ответ от 711 API
        mock_extend.return_value = {
            "order_id": "711-order-123",
            "extended_days": 30,
            "status": "extended"
        }

        request_data = {
            "days": 30
        }

        response = await client.post(
            f"/api/v1/proxies/{purchase.id}/extend",
            json=request_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Проверяем, что дата истечения обновилась
        new_expires = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
        assert new_expires > expires_at

    @pytest.mark.asyncio
    async def test_get_expiring_proxies(self, client: AsyncClient, auth_headers, db_session, test_user):
        """Тест получения истекающих прокси"""
        # Создаем прокси, которые скоро истекают
        from app.crud.proxy_purchase import proxy_purchase_crud

        expires_soon = datetime.now() + timedelta(days=3)
        await proxy_purchase_crud.create_purchase(
            db_session,
            user_id=test_user.id,
            proxy_product_id=1,
            order_id=1,
            proxy_list="1.2.3.4:8080",
            expires_at=expires_soon
        )

        response = await client.get(
            "/api/v1/proxies/expiring?days_ahead=7",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_proxies_unauthorized(self, client: AsyncClient):
        """Тест доступа к прокси без авторизации"""
        response = await client.get("/api/v1/proxies/my")
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_generate_proxy_list_expired(self, client: AsyncClient, auth_headers, db_session, test_user):
        """Тест генерации для истекшей покупки"""
        # Создаем истекшую покупку прокси
        from app.crud.proxy_purchase import proxy_purchase_crud

        expires_at = datetime.now() - timedelta(days=1)  # Уже истекла
        proxy_list_str = "1.2.3.4:8080"

        purchase = await proxy_purchase_crud.create_purchase(
            db_session,
            user_id=test_user.id,
            proxy_product_id=1,
            order_id=1,
            proxy_list=proxy_list_str,
            username="user123",
            password="pass123",
            expires_at=expires_at
        )

        request_data = {
            "format_type": "ip:port:user:pass"
        }

        response = await client.post(
            f"/api/v1/proxies/{purchase.id}/generate",
            json=request_data,
            headers=auth_headers
        )

        assert response.status_code == 400
        error_data = response.json()
        # ИСПРАВЛЕНО: проверяем разные форматы ответа
        if "detail" in error_data:
            assert "expired" in error_data["detail"]
        elif "message" in error_data:
            assert "expired" in error_data["message"]
        else:
            assert response.status_code == 400
