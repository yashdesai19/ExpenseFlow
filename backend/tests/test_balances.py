import uuid
from decimal import Decimal
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.core.config import settings


@pytest.mark.asyncio
async def test_balance_aggregation_and_simplification():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register 3 Users (A, B, C)
        users = []
        headers = []
        user_emails = []
        for name in ["UserA", "UserB", "UserC"]:
            email = f"{name.lower()}_{uuid.uuid4().hex[:6]}@example.com"
            await client.post(
                f"{settings.API_V1_STR}/auth/register",
                json={"email": email, "password": "Password123!", "full_name": name},
            )
            login = await client.post(
                f"{settings.API_V1_STR}/auth/login",
                json={"email": email, "password": "Password123!"},
            )
            data = login.json()
            users.append(data["user"])
            user_emails.append(email)
            headers.append({"Authorization": f"Bearer {data['access_token']}"})

        user_a, user_b, user_c = users
        headers_a, headers_b, headers_c = headers

        # Get User A's categories
        cats_res = await client.get(f"{settings.API_V1_STR}/categories", headers=headers_a)
        category_id = cats_res.json()[0]["id"]

        # 2. Create Group
        group_res = await client.post(
            f"{settings.API_V1_STR}/groups",
            headers=headers_a,
            json={"name": "Flatmates", "icon": "🏠"},
        )
        group_id = group_res.json()["id"]

        # Add User B and User C
        await client.post(f"{settings.API_V1_STR}/groups/{group_id}/members", headers=headers_a, json={"email": user_emails[1]})
        await client.post(f"{settings.API_V1_STR}/groups/{group_id}/members", headers=headers_a, json={"email": user_emails[2]})

        # 3. Post Expense: User A paid ₹3000 for A, B, C (equal split)
        await client.post(
            f"{settings.API_V1_STR}/groups/{group_id}/expenses",
            headers=headers_a,
            json={
                "category_id": category_id,
                "amount": 3000.00,
                "description": "Rent",
                "date": "2026-08-25",
                "split_method": "equal",
                "payments": [{"user_id": user_a["id"], "amount": 3000.00}],
                "participants": [
                    {"user_id": user_a["id"], "share_value": 1.0},
                    {"user_id": user_b["id"], "share_value": 1.0},
                    {"user_id": user_c["id"], "share_value": 1.0},
                ],
            },
        )

        # 4. Check balances
        res_bal1 = await client.get(f"{settings.API_V1_STR}/groups/{group_id}/balances", headers=headers_a)
        assert res_bal1.status_code == 200
        bal1 = res_bal1.json()
        assert bal1["total_expenses"] == "3000.00"
        
        balances_by_id = {b["user_id"]: b for b in bal1["balances"]}
        assert balances_by_id[user_a["id"]]["net_balance"] == "2000.00"
        assert balances_by_id[user_b["id"]]["net_balance"] == "-1000.00"
        assert balances_by_id[user_c["id"]]["net_balance"] == "-1000.00"

        # Simplified debts check
        debts = bal1["simplified_debts"]
        assert len(debts) == 2
        debts_map = {(d["from_user_id"], d["to_user_id"]): float(d["amount"]) for d in debts}
        assert debts_map[(user_b["id"], user_a["id"])] == 1000.00
        assert debts_map[(user_c["id"], user_a["id"])] == 1000.00

        # 5. Post another Expense: User B paid ₹3000 for A, B, C (equal split)
        # Net expectation:
        # A paid 3000, owes 2000 -> net +1000
        # B paid 3000, owes 2000 -> net +1000
        # C paid 0, owes 2000 -> net -2000
        await client.post(
            f"{settings.API_V1_STR}/groups/{group_id}/expenses",
            headers=headers_b,
            json={
                "category_id": category_id,
                "amount": 3000.00,
                "description": "Groceries",
                "date": "2026-08-25",
                "split_method": "equal",
                "payments": [{"user_id": user_b["id"], "amount": 3000.00}],
                "participants": [
                    {"user_id": user_a["id"], "share_value": 1.0},
                    {"user_id": user_b["id"], "share_value": 1.0},
                    {"user_id": user_c["id"], "share_value": 1.0},
                ],
            },
        )

        res_bal2 = await client.get(f"{settings.API_V1_STR}/groups/{group_id}/balances", headers=headers_a)
        assert res_bal2.status_code == 200
        bal2 = res_bal2.json()
        assert bal2["total_expenses"] == "6000.00"

        balances_by_id2 = {b["user_id"]: b for b in bal2["balances"]}
        assert balances_by_id2[user_a["id"]]["net_balance"] == "1000.00"
        assert balances_by_id2[user_b["id"]]["net_balance"] == "1000.00"
        assert balances_by_id2[user_c["id"]]["net_balance"] == "-2000.00"

        debts2 = bal2["simplified_debts"]
        assert len(debts2) == 2
        debts2_map = {(d["from_user_id"], d["to_user_id"]): float(d["amount"]) for d in debts2}
        assert debts2_map[(user_c["id"], user_a["id"])] == 1000.00
        assert debts2_map[(user_c["id"], user_b["id"])] == 1000.00
