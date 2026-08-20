import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.core.config import settings


@pytest.mark.asyncio
async def test_register_new_user_success():
    """Verify that a new user can register and receive a 201 Created status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unique_email = f"sarah_{uuid.uuid4().hex[:8]}@example.com"
        payload = {
            "email": unique_email,
            "password": "StrongPassword123!",
            "full_name": "Sarah Architect",
        }
        response = await client.post(f"{settings.API_V1_STR}/auth/register", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == unique_email
        assert data["full_name"] == "Sarah Architect"
        assert "id" in data
        assert "password" not in data
        assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email_conflict():
    """Verify that registering with an existing email returns 409 Conflict."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unique_email = f"duplicate_{uuid.uuid4().hex[:8]}@example.com"
        payload = {
            "email": unique_email,
            "password": "StrongPassword123!",
            "full_name": "Original User",
        }
        # First registration -> 201
        res1 = await client.post(f"{settings.API_V1_STR}/auth/register", json=payload)
        assert res1.status_code == 201

        # Second registration with same email -> 409 Conflict
        res2 = await client.post(f"{settings.API_V1_STR}/auth/register", json=payload)
        assert res2.status_code == 409
        assert "already exists" in res2.json()["detail"]


@pytest.mark.asyncio
async def test_register_invalid_short_password():
    """Verify that password under 8 characters triggers Pydantic 422 validation error."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "email": f"short_{uuid.uuid4().hex[:8]}@example.com",
            "password": "123",
            "full_name": "Short Password User",
        }
        response = await client.post(f"{settings.API_V1_STR}/auth/register", json=payload)
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success_and_jwt_token():
    """Verify that valid login returns a signed JWT access token."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unique_email = f"login_user_{uuid.uuid4().hex[:8]}@example.com"
        await client.post(
            f"{settings.API_V1_STR}/auth/register",
            json={"email": unique_email, "password": "StrongPassword123!", "full_name": "Login User"},
        )

        response = await client.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"email": unique_email, "password": "StrongPassword123!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == unique_email


@pytest.mark.asyncio
async def test_login_invalid_password():
    """Verify that incorrect password returns 401 Unauthorized."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unique_email = f"login_fail_{uuid.uuid4().hex[:8]}@example.com"
        await client.post(
            f"{settings.API_V1_STR}/auth/register",
            json={"email": unique_email, "password": "CorrectPassword123!", "full_name": "Fail Test"},
        )

        response = await client.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"email": unique_email, "password": "WrongPassword!"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_me_with_jwt():
    """Verify that protected route /auth/me returns current user when Bearer token is provided."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unique_email = f"me_test_{uuid.uuid4().hex[:8]}@example.com"
        await client.post(
            f"{settings.API_V1_STR}/auth/register",
            json={"email": unique_email, "password": "StrongPassword123!", "full_name": "Me User"},
        )

        login_res = await client.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"email": unique_email, "password": "StrongPassword123!"},
        )
        token = login_res.json()["access_token"]

        me_res = await client.get(
            f"{settings.API_V1_STR}/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_res.status_code == 200
        data = me_res.json()
        assert data["email"] == unique_email


@pytest.mark.asyncio
async def test_get_current_user_unauthorized_without_token():
    """Verify that accessing protected route /auth/me without token returns 401 Unauthorized."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"{settings.API_V1_STR}/auth/me")
        assert response.status_code == 401
