import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.core.config import settings


@pytest.mark.asyncio
async def test_root_endpoint():
    """Verify that the root endpoint returns a 200 OK and valid welcome payload."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["docs_url"] == "/docs"


@pytest.mark.asyncio
async def test_v1_health_check_endpoint():
    """Verify that /api/v1/health returns the correct structured Pydantic schema."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"{settings.API_V1_STR}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == settings.PROJECT_NAME
        assert data["version"] == "1.0.0"
        assert data["environment"] == settings.ENVIRONMENT


@pytest.mark.asyncio
async def test_legacy_health_check_endpoint():
    """Verify backward compatibility for /api/health."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == settings.PROJECT_NAME
