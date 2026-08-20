import datetime as dt
import uuid
from decimal import Decimal
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.core.config import settings


@pytest.mark.asyncio
async def test_budget_lifecycle_and_utilization_tracking():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register User
        user_email = f"budget_user_{uuid.uuid4().hex[:8]}@example.com"
        await client.post(
            f"{settings.API_V1_STR}/auth/register",
            json={"email": user_email, "password": "Password123!", "full_name": "Budget User"},
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
        now = dt.datetime.now()

        # 3. Create a $500 Budget
        budget_payload = {
            "category_id": category_id,
            "amount": 500.00,
            "month": now.month,
            "year": now.year,
        }
        create_res = await client.post(
            f"{settings.API_V1_STR}/budgets",
            headers=headers,
            json=budget_payload,
        )
        assert create_res.status_code == 201
        budget = create_res.json()
        assert float(budget["amount"]) == 500.00
        assert float(budget["spent_amount"]) == 0.00
        assert float(budget["remaining_amount"]) == 500.00
        assert budget["status"] == "UNDER_BUDGET"
        budget_id = budget["id"]

        # 4. Attempt Duplicate Budget for same period -> 409 Conflict
        dup_res = await client.post(
            f"{settings.API_V1_STR}/budgets",
            headers=headers,
            json=budget_payload,
        )
        assert dup_res.status_code == 409

        # 5. Log an Expense of $450 in this category
        exp_payload = {
            "amount": 450.00,
            "description": "Large grocery restock",
            "category_id": category_id,
            "account": "Credit Card",
            "date": now.strftime("%Y-%m-%d"),
        }
        await client.post(f"{settings.API_V1_STR}/expenses", headers=headers, json=exp_payload)

        # 6. Check Budget Utilization -> 90% spent -> WARNING_80_PERCENT
        get_res = await client.get(f"{settings.API_V1_STR}/budgets/{budget_id}", headers=headers)
        assert get_res.status_code == 200
        b_warn = get_res.json()
        assert float(b_warn["spent_amount"]) == 450.00
        assert float(b_warn["remaining_amount"]) == 50.00
        assert b_warn["percentage_used"] == 90.0
        assert b_warn["status"] == "WARNING_80_PERCENT"

        # 7. Log another $100 expense -> Total $550 spent -> EXCEEDED
        exp_payload_2 = {
            "amount": 100.00,
            "description": "Extra snacks",
            "category_id": category_id,
            "account": "Cash",
            "date": now.strftime("%Y-%m-%d"),
        }
        await client.post(f"{settings.API_V1_STR}/expenses", headers=headers, json=exp_payload_2)

        get_res_2 = await client.get(f"{settings.API_V1_STR}/budgets/{budget_id}", headers=headers)
        b_exceed = get_res_2.json()
        assert float(b_exceed["spent_amount"]) == 550.00
        assert float(b_exceed["remaining_amount"]) == -50.00
        assert b_exceed["percentage_used"] == 110.0
        assert b_exceed["status"] == "EXCEEDED"

        # 8. Delete Budget
        del_res = await client.delete(f"{settings.API_V1_STR}/budgets/{budget_id}", headers=headers)
        assert del_res.status_code == 200
