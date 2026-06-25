import pytest
from httpx import AsyncClient, ASGITransport

from app.api.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.mark.asyncio
class TestHealth:
    async def test_health_endpoint(self, app) -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/v1/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"

    async def test_readiness_endpoint(self, app) -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/v1/health/ready")
            assert response.status_code in (200, 503)
