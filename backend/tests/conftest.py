"""Test Configuration"""

import sys
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport

# srcをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def sample_session_data():
    return {"agent_id": "test-agent", "metadata": {"test": True}}


