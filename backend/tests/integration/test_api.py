"""API Integration Tests"""

import pytest


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


