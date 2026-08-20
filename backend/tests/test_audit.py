import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.core.config import settings


@pytest.mark.asyncio
async def test_audit_logs_tracking():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register User
        user_email = f"audit_user_{uuid.uuid4().hex[:8]}@example.com"
        await client.post(
            f"{settings.API_V1_STR}/auth/register",
            json={"email": user_email, "password": "Password123!", "full_name": "Audit Test User"},
        )
        login_res = await client.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"email": user_email, "password": "Password123!"},
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Get User's First Category
        cats_res = await client.get(f"{settings.API_V1_STR}/categories", headers=headers)
        category_id = cats_res.json()[0]["id"]

        # 3. Create an Expense (triggers EXPENSE_CREATED audit)
        await client.post(
            f"{settings.API_V1_STR}/expenses",
            headers=headers,
            json={
                "amount": 55.00,
                "description": "Book purchase",
                "category_id": category_id,
                "account": "Credit Card",
                "date": "2026-08-19",
            },
        )

        # 4. Fetch Audit Logs
        logs_res = await client.get(f"{settings.API_V1_STR}/audit-logs?page=1&limit=10", headers=headers)
        assert logs_res.status_code == 200
        logs_data = logs_res.json()

        assert logs_data["total"] >= 3  # USER_REGISTERED, USER_LOGIN, EXPENSE_CREATED
        actions = [log["action"] for log in logs_data["items"]]
        assert "USER_REGISTERED" in actions
        assert "USER_LOGIN" in actions
        assert "EXPENSE_CREATED" in actions
