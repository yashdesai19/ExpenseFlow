import uuid
from decimal import Decimal
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.core.config import settings


@pytest.mark.asyncio
async def test_group_expenses_splits_and_calculations():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register 3 Users (Yash, Rahul, Amit)
        users = []
        headers = []
        user_emails = []
        for name in ["Yash", "Rahul", "Amit"]:
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

        # Get Yash's categories
        cats_res = await client.get(f"{settings.API_V1_STR}/categories", headers=yash_headers)
        category_id = cats_res.json()[0]["id"]

        # 2. Create Group (Goa Trip)
        group_res = await client.post(
            f"{settings.API_V1_STR}/groups",
            headers=yash_headers,
            json={"name": "Goa Trip", "icon": "🌴"},
        )
        group = group_res.json()
        group_id = group["id"]

        # Add Rahul and Amit to Goa Trip
        await client.post(f"{settings.API_V1_STR}/groups/{group_id}/members", headers=yash_headers, json={"email": user_emails[1]})
        await client.post(f"{settings.API_V1_STR}/groups/{group_id}/members", headers=yash_headers, json={"email": user_emails[2]})

        # 3. Test Equal Split: ₹3000 Hotel, paid entirely by Yash. Participants: Yash, Rahul, Amit.
        equal_expense_payload = {
            "category_id": category_id,
            "amount": 3000.00,
            "description": "Hotel Goa",
            "date": "2026-08-25",
            "split_method": "equal",
            "payments": [{"user_id": yash["id"], "amount": 3000.00}],
            "participants": [
                {"user_id": yash["id"], "share_value": 1.0},
                {"user_id": rahul["id"], "share_value": 1.0},
                {"user_id": amit["id"], "share_value": 1.0},
            ],
        }
        res1 = await client.post(
            f"{settings.API_V1_STR}/groups/{group_id}/expenses",
            headers=yash_headers,
            json=equal_expense_payload,
        )
        assert res1.status_code == 201
        exp1 = res1.json()
        assert exp1["amount"] == "3000.00"
        assert len(exp1["payments"]) == 1
        assert exp1["payments"][0]["user_id"] == yash["id"]
        assert exp1["payments"][0]["amount"] == "3000.00"
        
        # Verify calculated amounts for equal split (₹1000 each)
        for part in exp1["participants"]:
            assert part["calculated_amount"] == "1000.00"

        # 4. Test Exact Split: ₹3000 split Yash: ₹500, Rahul: ₹1000, Amit: ₹1500. Paid by Yash.
        exact_expense_payload = {
            "category_id": category_id,
            "amount": 3000.00,
            "description": "Scuba Diving",
            "date": "2026-08-25",
            "split_method": "exact",
            "payments": [{"user_id": yash["id"], "amount": 3000.00}],
            "participants": [
                {"user_id": yash["id"], "share_value": 500.0},
                {"user_id": rahul["id"], "share_value": 1000.0},
                {"user_id": amit["id"], "share_value": 1500.0},
            ],
        }
        res2 = await client.post(
            f"{settings.API_V1_STR}/groups/{group_id}/expenses",
            headers=yash_headers,
            json=exact_expense_payload,
        )
        assert res2.status_code == 201
        exp2 = res2.json()
        participants_by_id = {p["user_id"]: p for p in exp2["participants"]}
        assert participants_by_id[yash["id"]]["calculated_amount"] == "500.00"
        assert participants_by_id[rahul["id"]]["calculated_amount"] == "1000.00"
        assert participants_by_id[amit["id"]]["calculated_amount"] == "1500.00"

        # 5. Test Percentage Split: ₹3000 split Yash 20% (₹600), Rahul 30% (₹900), Amit 50% (₹1500). Paid by Yash.
        pct_expense_payload = {
            "category_id": category_id,
            "amount": 3000.00,
            "description": "Dinner",
            "date": "2026-08-25",
            "split_method": "percentage",
            "payments": [{"user_id": yash["id"], "amount": 3000.00}],
            "participants": [
                {"user_id": yash["id"], "share_value": 20.0},
                {"user_id": rahul["id"], "share_value": 30.0},
                {"user_id": amit["id"], "share_value": 50.0},
            ],
        }
        res3 = await client.post(
            f"{settings.API_V1_STR}/groups/{group_id}/expenses",
            headers=yash_headers,
            json=pct_expense_payload,
        )
        assert res3.status_code == 201
        exp3 = res3.json()
        parts3 = {p["user_id"]: p for p in exp3["participants"]}
        assert parts3[yash["id"]]["calculated_amount"] == "600.00"
        assert parts3[rahul["id"]]["calculated_amount"] == "900.00"
        assert parts3[amit["id"]]["calculated_amount"] == "1500.00"

        # 6. Test Shares Split: ₹6000 split Yash 1 share, Rahul 2 shares, Amit 3 shares. Paid by Yash.
        shares_expense_payload = {
            "category_id": category_id,
            "amount": 6000.00,
            "description": "Boat Party",
            "date": "2026-08-25",
            "split_method": "shares",
            "payments": [{"user_id": yash["id"], "amount": 6000.00}],
            "participants": [
                {"user_id": yash["id"], "share_value": 1.0},
                {"user_id": rahul["id"], "share_value": 2.0},
                {"user_id": amit["id"], "share_value": 3.0},
            ],
        }
        res4 = await client.post(
            f"{settings.API_V1_STR}/groups/{group_id}/expenses",
            headers=yash_headers,
            json=shares_expense_payload,
        )
        assert res4.status_code == 201
        exp4 = res4.json()
        parts4 = {p["user_id"]: p for p in exp4["participants"]}
        assert parts4[yash["id"]]["calculated_amount"] == "1000.00"
        assert parts4[rahul["id"]]["calculated_amount"] == "2000.00"
        assert parts4[amit["id"]]["calculated_amount"] == "3000.00"

        # 7. Test Multiple Payers: Total ₹5000, Yash paid ₹3000, Rahul paid ₹2000.
        # Split equally among Yash, Rahul, Amit.
        multi_payer_payload = {
            "category_id": category_id,
            "amount": 5000.00,
            "description": "Flight bookings",
            "date": "2026-08-25",
            "split_method": "equal",
            "payments": [
                {"user_id": yash["id"], "amount": 3000.00},
                {"user_id": rahul["id"], "amount": 2000.00},
            ],
            "participants": [
                {"user_id": yash["id"], "share_value": 1.0},
                {"user_id": rahul["id"], "share_value": 1.0},
                {"user_id": amit["id"], "share_value": 1.0},
            ],
        }
        res5 = await client.post(
            f"{settings.API_V1_STR}/groups/{group_id}/expenses",
            headers=yash_headers,
            json=multi_payer_payload,
        )
        assert res5.status_code == 201
        exp5 = res5.json()
        assert len(exp5["payments"]) == 2
        payments_by_user = {p["user_id"]: p for p in exp5["payments"]}
        assert payments_by_user[yash["id"]]["amount"] == "3000.00"
        assert payments_by_user[rahul["id"]]["amount"] == "2000.00"

        # 8. Test validation error (Sum of payments != total amount)
        invalid_payment_payload = equal_expense_payload.copy()
        invalid_payment_payload["payments"] = [{"user_id": yash["id"], "amount": 2999.00}]
        res_fail1 = await client.post(
            f"{settings.API_V1_STR}/groups/{group_id}/expenses",
            headers=yash_headers,
            json=invalid_payment_payload,
        )
        assert res_fail1.status_code == 422
        assert "Sum of payments" in res_fail1.json()["errors"][0]

        # 9. Test percentage validation error (percentages != 100)
        invalid_pct_payload = pct_expense_payload.copy()
        invalid_pct_payload["participants"] = [
            {"user_id": yash["id"], "share_value": 20.0},
            {"user_id": rahul["id"], "share_value": 30.0},
            {"user_id": amit["id"], "share_value": 40.0}, # Total = 90
        ]
        res_fail2 = await client.post(
            f"{settings.API_V1_STR}/groups/{group_id}/expenses",
            headers=yash_headers,
            json=invalid_pct_payload,
        )
        assert res_fail2.status_code == 422
        assert "must equal exactly 100%" in res_fail2.json()["errors"][0]

        # 10. Test Shares Split: ₹6000 split Yash 1 share, Rahul 2 shares, Amit 3 shares. Paid entirely by Yash.
        shares_expense_payload = {
            "category_id": category_id,
            "amount": 6000.00,
            "description": "Boat Party Shares",
            "date": "2026-08-25",
            "split_method": "shares",
            "payments": [{"user_id": yash["id"], "amount": 6000.00}],
            "participants": [
                {"user_id": yash["id"], "share_value": 1.0},
                {"user_id": rahul["id"], "share_value": 2.0},
                {"user_id": amit["id"], "share_value": 3.0},
            ],
        }
        res6 = await client.post(
            f"{settings.API_V1_STR}/groups/{group_id}/expenses",
            headers=yash_headers,
            json=shares_expense_payload,
        )
        assert res6.status_code == 201
        exp6 = res6.json()
        parts6 = {p["user_id"]: p for p in exp6["participants"]}
        assert parts6[yash["id"]]["calculated_amount"] == "1000.00"
        assert parts6[rahul["id"]]["calculated_amount"] == "2000.00"
        assert parts6[amit["id"]]["calculated_amount"] == "3000.00"

        # 11. Test updating a group expense (PATCH)
        update_payload = {
            "category_id": category_id,
            "amount": 4000.00,
            "description": "Boat Party Updated",
            "date": "2026-08-26",
            "split_method": "equal",
            "payments": [{"user_id": yash["id"], "amount": 4000.00}],
            "participants": [
                {"user_id": yash["id"], "share_value": 1.0},
                {"user_id": rahul["id"], "share_value": 1.0},
                {"user_id": amit["id"], "share_value": 1.0},
            ],
        }
        res_update = await client.patch(
            f"{settings.API_V1_STR}/groups/{group_id}/expenses/{exp1['id']}",
            headers=yash_headers,
            json=update_payload,
        )
        assert res_update.status_code == 200
        updated_exp = res_update.json()
        assert updated_exp["amount"] == "4000.00"
        assert updated_exp["description"] == "Boat Party Updated"
        assert updated_exp["date"] == "2026-08-26"

        # 12. Test that a non-creator member cannot update expense (403)
        res_forbidden = await client.patch(
            f"{settings.API_V1_STR}/groups/{group_id}/expenses/{exp1['id']}",
            headers=amit_headers,
            json=update_payload,
        )
        assert res_forbidden.status_code == 403

        # 13. Test that an outsider (non-member) cannot access/update expense (403)
        outsider_email = f"outsider_{uuid.uuid4().hex[:8]}@example.com"
        await client.post(
            f"{settings.API_V1_STR}/auth/register",
            json={"email": outsider_email, "password": "Password123!", "full_name": "Outsider"},
        )
        outsider_login = await client.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"email": outsider_email, "password": "Password123!"},
        )
        outsider_headers = {"Authorization": f"Bearer {outsider_login.json()['access_token']}"}
        res_outsider = await client.patch(
            f"{settings.API_V1_STR}/groups/{group_id}/expenses/{exp1['id']}",
            headers=outsider_headers,
            json=update_payload,
        )
        assert res_outsider.status_code == 403
