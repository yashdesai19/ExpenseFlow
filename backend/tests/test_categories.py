import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.core.config import settings


@pytest.mark.asyncio
async def test_categories_lifecycle():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register a test user
        user_email = f"cat_user_{uuid.uuid4().hex[:8]}@example.com"
        await client.post(
            f"{settings.API_V1_STR}/auth/register",
            json={"email": user_email, "password": "Password123!", "full_name": "Category User"},
        )
        login_res = await client.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"email": user_email, "password": "Password123!"},
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. List categories (should have 8 seeded categories)
        list_res = await client.get(f"{settings.API_V1_STR}/categories", headers=headers)
        assert list_res.status_code == 200
        categories = list_res.json()
        assert len(categories) >= 8

        # 3. Create a custom category
        create_res = await client.post(
            f"{settings.API_V1_STR}/categories",
            headers=headers,
            json={"name": "Gaming & Tech", "color": "#8B5CF6", "icon": "gamepad"},
        )
        assert create_res.status_code == 201
        new_cat = create_res.json()
        assert new_cat["name"] == "Gaming & Tech"
        cat_id = new_cat["id"]

        # 4. Duplicate custom category returns 409 Conflict
        dup_res = await client.post(
            f"{settings.API_V1_STR}/categories",
            headers=headers,
            json={"name": "Gaming & Tech", "color": "#8B5CF6", "icon": "gamepad"},
        )
        assert dup_res.status_code == 409

        # 5. Update custom category
        update_res = await client.patch(
            f"{settings.API_V1_STR}/categories/{cat_id}",
            headers=headers,
            json={"name": "Gaming & Gadgets", "color": "#EC4899"},
        )
        assert update_res.status_code == 200
        assert update_res.json()["name"] == "Gaming & Gadgets"

        # 6. Delete custom category
        del_res = await client.delete(f"{settings.API_V1_STR}/categories/{cat_id}", headers=headers)
        assert del_res.status_code == 200

        # Verify deleted
        get_res = await client.get(f"{settings.API_V1_STR}/categories/{cat_id}", headers=headers)
        assert get_res.status_code == 404
