import datetime as dt
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.core.config import settings


@pytest.mark.asyncio
async def test_recurring_expense_generation_lifecycle():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register User
        user_email = f"recur_user_{uuid.uuid4().hex[:8]}@example.com"
        await client.post(
            f"{settings.API_V1_STR}/auth/register",
            json={"email": user_email, "password": "Password123!", "full_name": "Recurring User"},
        )
        login_res = await client.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"email": user_email, "password": "Password123!"},
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Get Categories
        cats_res = await client.get(f"{settings.API_V1_STR}/categories", headers=headers)
        category_id = cats_res.json()[0]["id"]
        today = dt.date.today()

        # 3. Create Monthly Recurring Schedule ($19.99 for Netflix)
        create_res = await client.post(
            f"{settings.API_V1_STR}/recurring",
            headers=headers,
            json={
                "amount": 19.99,
                "description": "Netflix Subscription",
                "category_id": category_id,
                "account": "Credit Card",
                "frequency": "MONTHLY",
                "start_date": today.strftime("%Y-%m-%d"),
                "next_due_date": today.strftime("%Y-%m-%d"),
            },
        )
        assert create_res.status_code == 201
        recurring_schedule = create_res.json()
        assert float(recurring_schedule["amount"]) == 19.99
        schedule_id = recurring_schedule["id"]

        # 4. Trigger Batch Processing of Due Expenses
        proc_res = await client.post(
            f"{settings.API_V1_STR}/recurring/process",
            headers=headers,
        )
        assert proc_res.status_code == 200
        proc_data = proc_res.json()
        assert proc_data["generated_expenses_count"] >= 1
        generated_expense_id = proc_data["generated_expense_ids"][0]

        # 5. Verify the generated expense exists in general expense list
        exp_res = await client.get(
            f"{settings.API_V1_STR}/expenses/{generated_expense_id}",
            headers=headers,
        )
        assert exp_res.status_code == 200
        exp_data = exp_res.json()
        assert float(exp_data["amount"]) == 19.99
        assert "Netflix Subscription" in exp_data["description"]
        assert exp_data["recurring_expense_id"] == schedule_id

        # 6. Verify Schedule next_due_date advanced to next month
        sched_res = await client.get(
            f"{settings.API_V1_STR}/recurring/{schedule_id}",
            headers=headers,
        )
        assert sched_res.status_code == 200
        updated_sched = sched_res.json()
        # Next due date should be > today
        assert updated_sched["next_due_date"] > today.strftime("%Y-%m-%d")

        # 7. Delete recurring schedule
        del_res = await client.delete(
            f"{settings.API_V1_STR}/recurring/{schedule_id}",
            headers=headers,
        )
        assert del_res.status_code == 200
