"""API Integration Tests"""

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import create_app


@pytest.fixture
async def client():
    """テスト用HTTPクライアント"""
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def sample_session_data():
    """サンプルセッションデータ"""
    return {
        "agent_id": "test-agent-001",
        "user_id": "test-user-001",
    }


class TestHealthAPI:
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestSessionsAPI:
    @pytest.mark.asyncio
    async def test_create_session(self, client, sample_session_data):
        response = await client.post("/sessions", json=sample_session_data)
        assert response.status_code == 201
        assert "session_id" in response.json()
