"""Pytest Configuration and Fixtures"""

import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

import pytest
from unittest.mock import AsyncMock

from infrastructure.persistence.event_store import InMemoryEventStore
from infrastructure.persistence.session_repository_impl import EventSourcedSessionRepository
from infrastructure.messaging.event_publisher import InMemoryEventPublisher


@pytest.fixture
def event_store():
    """テスト用インメモリイベントストア"""
    return InMemoryEventStore()


@pytest.fixture
def session_repository(event_store):
    """テスト用セッションリポジトリ"""
    return EventSourcedSessionRepository(event_store)


@pytest.fixture
def event_publisher():
    """テスト用イベントパブリッシャー"""
    return InMemoryEventPublisher()


@pytest.fixture
def mock_agent_port():
    """モックエージェントポート"""
    from application.ports.agent_port import AgentPort, AgentResponse

    mock = AsyncMock(spec=AgentPort)
    mock.execute.return_value = AgentResponse(
        content="This is a test response",
        metadata={"provider": "mock"},
    )
    mock.execute_with_tools.return_value = AgentResponse(
        content="This is a test response with tools",
        tool_calls=[{"tool_name": "test_tool", "tool_input": {}}],
        metadata={"provider": "mock"},
    )
    return mock
