import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.core.config import settings


@pytest.mark.asyncio
async def test_groups_workflow_and_isolation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register User A (Group Owner)
        user_a_email = f"owner_{uuid.uuid4().hex[:8]}@example.com"
        await client.post(
            f"{settings.API_V1_STR}/auth/register",
            json={"email": user_a_email, "password": "Password123!", "full_name": "Owner A"},
        )
        login_a = await client.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"email": user_a_email, "password": "Password123!"},
        )
        token_a = login_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # 2. Register User B (Normal Member)
        user_b_email = f"member_{uuid.uuid4().hex[:8]}@example.com"
        await client.post(
            f"{settings.API_V1_STR}/auth/register",
            json={"email": user_b_email, "password": "Password123!", "full_name": "Member B"},
        )
        login_b = await client.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"email": user_b_email, "password": "Password123!"},
        )
        token_b = login_b.json()["access_token"]
        user_b_id = login_b.json()["user"]["id"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # 3. Register User C (Non-member)
        user_c_email = f"outsider_{uuid.uuid4().hex[:8]}@example.com"
        await client.post(
            f"{settings.API_V1_STR}/auth/register",
            json={"email": user_c_email, "password": "Password123!", "full_name": "Outsider C"},
        )
        login_c = await client.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"email": user_c_email, "password": "Password123!"},
        )
        token_c = login_c.json()["access_token"]
        headers_c = {"Authorization": f"Bearer {token_c}"}

        # 4. User A creates a Group
        group_payload = {
            "name": "Goa Trip 2026",
            "icon": "🌴",
            "description": "Shared expenses for the Goa holiday",
        }
        create_res = await client.post(
            f"{settings.API_V1_STR}/groups",
            headers=headers_a,
            json=group_payload,
        )
        assert create_res.status_code == 201
        group = create_res.json()
        assert group["name"] == "Goa Trip 2026"
        assert group["icon"] == "🌴"
        group_id = group["id"]

        # 5. User A lists their groups
        list_res = await client.get(
            f"{settings.API_V1_STR}/groups",
            headers=headers_a,
        )
        assert list_res.status_code == 200
        groups = list_res.json()
        assert len(groups) == 1
        assert groups[0]["id"] == group_id

        # 6. User B lists their groups (should be empty initially)
        list_b_res = await client.get(
            f"{settings.API_V1_STR}/groups",
            headers=headers_b,
        )
        assert list_b_res.status_code == 200
        assert len(list_b_res.json()) == 0

        # 7. User A adds User B to the group
        add_res = await client.post(
            f"{settings.API_V1_STR}/groups/{group_id}/members",
            headers=headers_a,
            json={"email": user_b_email},
        )
        assert add_res.status_code == 201
        member = add_res.json()
        assert member["email"] == user_b_email
        assert member["role"] == "member"

        # 8. User B lists their groups again (should have 1 group now)
        list_b_res2 = await client.get(
            f"{settings.API_V1_STR}/groups",
            headers=headers_b,
        )
        assert list_b_res2.status_code == 200
        assert len(list_b_res2.json()) == 1
        assert list_b_res2.json()[0]["id"] == group_id

        # 9. Authorization/Isolation Check: User C (outsider) tries to retrieve the group details
        unauth_get = await client.get(
            f"{settings.API_V1_STR}/groups/{group_id}",
            headers=headers_c,
        )
        assert unauth_get.status_code == 403

        # 10. User B (member but not admin/owner) tries to update group details (should fail)
        update_fail = await client.patch(
            f"{settings.API_V1_STR}/groups/{group_id}",
            headers=headers_b,
            json={"name": "Goa Trip - Hacked!"},
        )
        assert update_fail.status_code == 403

        # 11. User B leaves the group
        leave_res = await client.delete(
            f"{settings.API_V1_STR}/groups/{group_id}/members/{user_b_id}",
            headers=headers_b,
        )
        assert leave_res.status_code == 200
        assert "Member successfully removed" in leave_res.json()["message"]

        # 12. Verify User B is no longer in group's member list
        group_details = await client.get(
            f"{settings.API_V1_STR}/groups/{group_id}",
            headers=headers_a,
        )
        assert group_details.status_code == 200
        members = group_details.json()["members"]
        # Only User A should be left
        assert len(members) == 1
        assert members[0]["email"] == user_a_email

        # 13. Owner A deletes the group
        del_res = await client.delete(
            f"{settings.API_V1_STR}/groups/{group_id}",
            headers=headers_a,
        )
        assert del_res.status_code == 200

        # 14. Verify group is deleted
        get_deleted = await client.get(
            f"{settings.API_V1_STR}/groups/{group_id}",
            headers=headers_a,
        )
        assert get_deleted.status_code == 404
