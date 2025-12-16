"""Command/Query Handlers Unit Tests"""

from unittest.mock import AsyncMock

import pytest

from application.commands import SendMessageCommand, StartSessionCommand
from application.handlers.command_handlers import (
    SendMessageHandler,
    SessionNotFoundError,
    StartSessionHandler,
)
from application.handlers.query_handlers import GetSessionHandler
from application.queries import GetSessionQuery
from domain.entities.session import Session
from domain.value_objects.ids import AgentId, UserId


@pytest.fixture
def mock_repository():
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_publisher():
    publisher = AsyncMock()
    return publisher


class TestStartSessionHandler:
    """StartSessionHandlerのテスト"""

    @pytest.mark.asyncio
    async def test_start_session_success(self, mock_repository, mock_publisher):
        """セッション開始の成功"""
        handler = StartSessionHandler(mock_repository, mock_publisher)
        command = StartSessionCommand(agent_id="agent-001", user_id="user-001")

        session_id = await handler.handle(command)

        assert session_id is not None
        mock_repository.save.assert_called_once()
        mock_publisher.publish.assert_called()


class TestSendMessageHandler:
    """SendMessageHandlerのテスト"""

    @pytest.mark.asyncio
    async def test_send_message_success(self, mock_repository, mock_publisher):
        """メッセージ送信の成功"""
        # セッションを作成
        session = Session.start(
            agent_id=AgentId("agent-001"),
            user_id=UserId("user-001"),
        )
        session.clear_domain_events()
        mock_repository.find_by_id.return_value = session

        handler = SendMessageHandler(mock_repository, mock_publisher)
        command = SendMessageCommand(
            session_id=str(session.id),
            content="Hello, AI!",
        )

        message_id = await handler.handle(command)

        assert message_id is not None
        assert len(session.messages) == 1
        mock_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_session_not_found(self, mock_repository, mock_publisher):
        """存在しないセッションへのメッセージ送信"""
        mock_repository.find_by_id.return_value = None

        handler = SendMessageHandler(mock_repository, mock_publisher)
        command = SendMessageCommand(
            session_id="nonexistent",
            content="Hello",
        )

        with pytest.raises(SessionNotFoundError):
            await handler.handle(command)


class TestGetSessionHandler:
    """GetSessionHandlerのテスト"""

    @pytest.mark.asyncio
    async def test_get_session_success(self, mock_repository):
        """セッション取得の成功"""
        session = Session.start(
            agent_id=AgentId("agent-001"),
            user_id=UserId("user-001"),
        )
        mock_repository.find_by_id.return_value = session

        handler = GetSessionHandler(mock_repository)
        query = GetSessionQuery(session_id=str(session.id))

        result = await handler.handle(query)

        assert result is not None
        assert result.agent_id == "agent-001"
        assert result.state == "active"

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, mock_repository):
        """存在しないセッション"""
        mock_repository.find_by_id.return_value = None

        handler = GetSessionHandler(mock_repository)
        query = GetSessionQuery(session_id="nonexistent")

        result = await handler.handle(query)

        assert result is None

