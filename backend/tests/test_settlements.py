import uuid
from decimal import Decimal
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.core.config import settings


@pytest.mark.asyncio
async def test_settlement_workflow_and_balance_reversal():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register 3 Users (Yash, Rahul, Amit)
        users = []
        headers = []
        user_emails = []
        for name in ["YashSettle", "RahulSettle", "AmitSettle"]:
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

        yash, rahul, amit = users
        yash_headers, rahul_headers, amit_headers = headers

        # Get category
        cats_res = await client.get(f"{settings.API_V1_STR}/categories", headers=yash_headers)
        category_id = cats_res.json()[0]["id"]

        # 2. Create Group
        group_res = await client.post(
            f"{settings.API_V1_STR}/groups",
            headers=yash_headers,
            json={"name": "Vacation Group", "icon": "✈️"},
        )
        group_id = group_res.json()["id"]

        # Add members
        await client.post(f"{settings.API_V1_STR}/groups/{group_id}/members", headers=yash_headers, json={"email": user_emails[1]})
        await client.post(f"{settings.API_V1_STR}/groups/{group_id}/members", headers=yash_headers, json={"email": user_emails[2]})

        # 3. Post shared expense: Yash paid ₹3000 for Yash, Rahul, Amit (Equal split)
        await client.post(
            f"{settings.API_V1_STR}/groups/{group_id}/expenses",
            headers=yash_headers,
            json={
                "category_id": category_id,
                "amount": 3000.00,
                "description": "Airbnb",
                "date": "2026-08-25",
                "split_method": "equal",
                "payments": [{"user_id": yash["id"], "amount": 3000.00}],
                "participants": [
                    {"user_id": yash["id"], "share_value": 1.0},
                    {"user_id": rahul["id"], "share_value": 1.0},
                    {"user_id": amit["id"], "share_value": 1.0},
                ],
            },
        )

        # Confirm balances: Yash gets +2000, Rahul owes 1000, Amit owes 1000
        bal1_res = await client.get(f"{settings.API_V1_STR}/groups/{group_id}/balances", headers=yash_headers)
        bal1 = {b["user_id"]: b for b in bal1_res.json()["balances"]}
        assert bal1[yash["id"]]["net_balance"] == "2000.00"
        assert bal1[rahul["id"]]["net_balance"] == "-1000.00"
        assert bal1[amit["id"]]["net_balance"] == "-1000.00"

        # 4. Rahul settles up with Yash by paying ₹1000
        settle_res = await client.post(
            f"{settings.API_V1_STR}/groups/{group_id}/settlements",
            headers=rahul_headers,
            json={
                "payer_id": rahul["id"],
                "receiver_id": yash["id"],
                "amount": 1000.00,
                "date": "2026-08-25",
                "notes": "Paid my share for Airbnb",
            },
        )
        assert settle_res.status_code == 201
        settlement = settle_res.json()
        assert settlement["amount"] == "1000.00"
        assert settlement["payer_id"] == rahul["id"]
        assert settlement["receiver_id"] == yash["id"]
        settlement_id = settlement["id"]

        # Confirm new balances: Rahul net balance should be 0.00, Yash gets +1000.00
        bal2_res = await client.get(f"{settings.API_V1_STR}/groups/{group_id}/balances", headers=yash_headers)
        bal2 = {b["user_id"]: b for b in bal2_res.json()["balances"]}
        assert float(bal2[rahul["id"]]["net_balance"]) == 0.00
        assert float(bal2[yash["id"]]["net_balance"]) == 1000.00
        assert float(bal2[amit["id"]]["net_balance"]) == -1000.00

        # 5. List settlements
        list_settle = await client.get(f"{settings.API_V1_STR}/groups/{group_id}/settlements", headers=yash_headers)
        assert list_settle.status_code == 200
        assert len(list_settle.json()) == 1
        assert list_settle.json()[0]["id"] == settlement_id

        # 6. Reversal: Rahul deletes/cancels the settlement payment
        del_res = await client.delete(
            f"{settings.API_V1_STR}/groups/{group_id}/settlements/{settlement_id}",
            headers=rahul_headers,
        )
        assert del_res.status_code == 200

        # Confirm balances reverted to original state
        bal3_res = await client.get(f"{settings.API_V1_STR}/groups/{group_id}/balances", headers=yash_headers)
        bal3 = {b["user_id"]: b for b in bal3_res.json()["balances"]}
        assert bal3[yash["id"]]["net_balance"] == "2000.00"
        assert bal3[rahul["id"]]["net_balance"] == "-1000.00"
        assert bal3[amit["id"]]["net_balance"] == "-1000.00"
