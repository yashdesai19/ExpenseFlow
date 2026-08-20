import datetime as dt
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.core.config import settings


@pytest.mark.asyncio
async def test_financial_spending_reports_and_trends():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register User
        user_email = f"report_user_{uuid.uuid4().hex[:8]}@example.com"
        await client.post(
            f"{settings.API_V1_STR}/auth/register",
            json={"email": user_email, "password": "Password123!", "full_name": "Report User"},
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
        cat_id = categories[0]["id"]
        today = dt.date.today()

        # 3. Create Expenses
        await client.post(
            f"{settings.API_V1_STR}/expenses",
            headers=headers,
            json={
                "amount": 150.00,
                "description": "Weekly Grocery",
                "category_id": cat_id,
                "account": "Debit Card",
                "date": today.strftime("%Y-%m-%d"),
            },
        )

        # 4. Fetch Spending Report
        start_date = today.replace(day=1).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")

        rep_res = await client.get(
            f"{settings.API_V1_STR}/reports/spending?start_date={start_date}&end_date={end_date}",
            headers=headers,
        )
        assert rep_res.status_code == 200
        rep_data = rep_res.json()

        assert float(rep_data["total_spent"]) == 150.00
        assert rep_data["transaction_count"] == 1
        assert float(rep_data["daily_average"]) > 0
        assert len(rep_data["category_breakdown"]) == 1
        assert len(rep_data["account_breakdown"]) == 1

        # 5. Fetch Multi-Month Trends
        trends_res = await client.get(
            f"{settings.API_V1_STR}/reports/monthly-trends?months=6",
            headers=headers,
        )
        assert trends_res.status_code == 200
        trends_data = trends_res.json()
        assert len(trends_data["items"]) == 6
        assert trends_data["items"][-1]["month"] == today.month
