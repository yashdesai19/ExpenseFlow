import uuid
from decimal import Decimal
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.core.config import settings


@pytest.mark.asyncio
async def test_expense_crud_and_user_isolation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register User A
        user_a_email = f"user_a_{uuid.uuid4().hex[:8]}@example.com"
        await client.post(
            f"{settings.API_V1_STR}/auth/register",
            json={"email": user_a_email, "password": "Password123!", "full_name": "User Alpha"},
        )
        login_a = await client.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"email": user_a_email, "password": "Password123!"},
        )
        token_a = login_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # 2. Register User B
        user_b_email = f"user_b_{uuid.uuid4().hex[:8]}@example.com"
        await client.post(
            f"{settings.API_V1_STR}/auth/register",
            json={"email": user_b_email, "password": "Password123!", "full_name": "User Beta"},
        )
        login_b = await client.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"email": user_b_email, "password": "Password123!"},
        )
        token_b = login_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # 3. Get User A's categories
        cats_res = await client.get(f"{settings.API_V1_STR}/categories", headers=headers_a)
        category_id = cats_res.json()[0]["id"]

        # 4. User A creates an Expense
        expense_payload = {
            "amount": 75.50,
            "description": "Team Lunch at Bistro",
            "category_id": category_id,
            "account": "Corporate Credit Card",
            "date": "2026-08-19",
            "notes": "Quarterly project celebration",
        }
        create_res = await client.post(
            f"{settings.API_V1_STR}/expenses",
            headers=headers_a,
            json=expense_payload,
        )
        assert create_res.status_code == 201
        expense_a = create_res.json()
        assert float(expense_a["amount"]) == 75.50
        assert expense_a["description"] == "Team Lunch at Bistro"
        expense_id = expense_a["id"]

        # 5. User A lists expenses with pagination
        list_res = await client.get(
            f"{settings.API_V1_STR}/expenses?page=1&limit=10",
            headers=headers_a,
        )
        assert list_res.status_code == 200
        list_data = list_res.json()
        assert list_data["total"] >= 1
        assert float(list_data["total_amount"]) >= 75.50
        assert list_data["page"] == 1

        # 6. Filter by search query
        search_res = await client.get(
            f"{settings.API_V1_STR}/expenses?search=Bistro",
            headers=headers_a,
        )
        assert search_res.status_code == 200
        assert len(search_res.json()["items"]) == 1

        # 7. MULTI-TENANCY SECURITY TEST: User B tries to view or edit User A's expense
        unauth_get = await client.get(
            f"{settings.API_V1_STR}/expenses/{expense_id}",
            headers=headers_b,
        )
        assert unauth_get.status_code == 404  # Must be 404 (not accessible)

        unauth_del = await client.delete(
            f"{settings.API_V1_STR}/expenses/{expense_id}",
            headers=headers_b,
        )
        assert unauth_del.status_code == 404

        # 8. User A partially updates expense
        update_res = await client.patch(
            f"{settings.API_V1_STR}/expenses/{expense_id}",
            headers=headers_a,
            json={"amount": 80.00, "notes": "Updated note with tips included"},
        )
        assert update_res.status_code == 200
        assert float(update_res.json()["amount"]) == 80.00

        # 9. Verify category deletion is blocked while expenses are attached
        cat_del_res = await client.delete(
            f"{settings.API_V1_STR}/categories/{category_id}",
            headers=headers_a,
        )
        assert cat_del_res.status_code == 400
        assert "associated" in cat_del_res.json()["detail"]

        # 10. User A deletes expense
        del_res = await client.delete(
            f"{settings.API_V1_STR}/expenses/{expense_id}",
            headers=headers_a,
        )
        assert del_res.status_code == 200
