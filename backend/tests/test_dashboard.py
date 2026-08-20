import datetime as dt
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.core.config import settings


@pytest.mark.asyncio
async def test_dashboard_summary_kpis_and_aggregations():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register User
        user_email = f"dashboard_user_{uuid.uuid4().hex[:8]}@example.com"
        await client.post(
            f"{settings.API_V1_STR}/auth/register",
            json={"email": user_email, "password": "Password123!", "full_name": "Dashboard User"},
        )
        login_res = await client.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"email": user_email, "password": "Password123!"},
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Get Categories
        cats_res = await client.get(f"{settings.API_V1_STR}/categories", headers=headers)
        categories = cats_res.json()
        cat_1 = categories[0]["id"]
        cat_2 = categories[1]["id"]
        now = dt.datetime.now()
        today = now.strftime("%Y-%m-%d")

        # 3. Create Expenses
        # Expense 1 in Category 1, Checking Account
        await client.post(
            f"{settings.API_V1_STR}/expenses",
            headers=headers,
            json={
                "amount": 100.00,
                "description": "Category 1 Expense",
                "category_id": cat_1,
                "account": "Checking",
                "date": today,
            },
        )
        # Expense 2 in Category 2, Credit Card
        await client.post(
            f"{settings.API_V1_STR}/expenses",
            headers=headers,
            json={
                "amount": 200.00,
                "description": "Category 2 Expense",
                "category_id": cat_2,
                "account": "Credit Card",
                "date": today,
            },
        )

        # 4. Create Budget for Category 1 ($500)
        await client.post(
            f"{settings.API_V1_STR}/budgets",
            headers=headers,
            json={
                "category_id": cat_1,
                "amount": 500.00,
                "month": now.month,
                "year": now.year,
            },
        )

        # 5. Fetch Dashboard Summary
        dash_res = await client.get(
            f"{settings.API_V1_STR}/dashboard/summary?month={now.month}&year={now.year}",
            headers=headers,
        )
        assert dash_res.status_code == 200
        data = dash_res.json()

        # Verify KPIs
        kpis = data["kpis"]
        assert float(kpis["total_spent_this_month"]) == 300.00
        assert kpis["transaction_count"] == 2
        assert float(kpis["total_budget_allocated"]) == 500.00
        assert float(kpis["total_budget_spent"]) == 300.00

        # Verify Category Breakdown
        cat_stats = data["category_breakdown"]
        assert len(cat_stats) == 2
        # Highest spent category should be first (Category 2 with $200)
        assert float(cat_stats[0]["total_amount"]) == 200.00
        assert cat_stats[0]["percentage_of_total"] == 66.67
        assert float(cat_stats[1]["total_amount"]) == 100.00
        assert cat_stats[1]["percentage_of_total"] == 33.33

        # Verify Account Breakdown
        acc_stats = data["account_breakdown"]
        assert len(acc_stats) == 2

        # Verify Daily Trends
        daily = data["daily_trends"]
        assert len(daily) >= 1
        assert float(daily[0]["amount"]) == 300.00

        # Verify Recent Expenses
        recent = data["recent_expenses"]
        assert len(recent) == 2
