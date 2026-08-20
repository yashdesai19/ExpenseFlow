import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.core.config import settings


@pytest.mark.asyncio
async def test_user_settings_preferences():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register User
        user_email = f"settings_user_{uuid.uuid4().hex[:8]}@example.com"
        await client.post(
            f"{settings.API_V1_STR}/auth/register",
            json={"email": user_email, "password": "Password123!", "full_name": "Settings User"},
        )
        login_res = await client.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"email": user_email, "password": "Password123!"},
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Get Default Settings
        get_res = await client.get(f"{settings.API_V1_STR}/settings", headers=headers)
        assert get_res.status_code == 200
        settings_data = get_res.json()
        assert settings_data["currency"] == "USD"
        assert settings_data["theme"] == "dark"
        assert settings_data["date_format"] == "YYYY-MM-DD"

        # 3. Update Settings
        update_res = await client.patch(
            f"{settings.API_V1_STR}/settings",
            headers=headers,
            json={
                "currency": "EUR",
                "theme": "light",
                "date_format": "DD/MM/YYYY",
                "email_notifications": False,
            },
        )
        assert update_res.status_code == 200
        updated_data = update_res.json()
        assert updated_data["currency"] == "EUR"
        assert updated_data["theme"] == "light"
        assert updated_data["date_format"] == "DD/MM/YYYY"
        assert updated_data["email_notifications"] is False
