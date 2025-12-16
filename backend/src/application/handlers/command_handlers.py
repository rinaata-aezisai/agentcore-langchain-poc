"""Command Handlers

コマンドを処理するハンドラ。ドメインロジックを実行し、イベントを発行。
"""

from typing import Any

from domain.entities.session import Session
from domain.entities.message import Message
from domain.repositories.session_repository import SessionRepository
from domain.value_objects.ids import SessionId, AgentId, UserId, MessageId
from domain.value_objects.content import Content
from application.commands import (
    StartSessionCommand,
    SendMessageCommand,
    EndSessionCommand,
    ExecuteAgentCommand,
)
from application.ports.agent_port import AgentPort
from infrastructure.messaging.event_publisher import EventPublisher
from ulid import ULID


class StartSessionHandler:
    """セッション開始ハンドラ"""

    def __init__(
        self,
        session_repository: SessionRepository,
        event_publisher: EventPublisher,
    ):
        self._repository = session_repository
        self._publisher = event_publisher

    async def handle(self, command: StartSessionCommand) -> str:
        """セッションを開始"""
        session = Session.start(
            agent_id=AgentId(command.agent_id),
            user_id=UserId(command.user_id),
        )

        await self._repository.save(session)

        # ドメインイベントを発行
        for event in session.get_domain_events():
            await self._publisher.publish(event, type(event).__name__)

        return str(session.id)


class SendMessageHandler:
    """メッセージ送信ハンドラ"""

    def __init__(
        self,
        session_repository: SessionRepository,
        event_publisher: EventPublisher,
    ):
        self._repository = session_repository
        self._publisher = event_publisher

    async def handle(self, command: SendMessageCommand) -> str:
        """メッセージを送信"""
        session = await self._repository.find_by_id(SessionId(command.session_id))
        if not session:
            raise SessionNotFoundError(command.session_id)

        message = Message(
            id=MessageId(str(ULID())),
            session_id=session.id,
            role="user",
            content=Content(text=command.content),
        )

        session.add_message(message)
        await self._repository.save(session)

        # ドメインイベントを発行
        for event in session.get_domain_events():
            await self._publisher.publish(event, type(event).__name__)

        return str(message.id)


class EndSessionHandler:
    """セッション終了ハンドラ"""

    def __init__(
        self,
        session_repository: SessionRepository,
        event_publisher: EventPublisher,
    ):
        self._repository = session_repository
        self._publisher = event_publisher

    async def handle(self, command: EndSessionCommand) -> None:
        """セッションを終了"""
        session = await self._repository.find_by_id(SessionId(command.session_id))
        if not session:
            raise SessionNotFoundError(command.session_id)

        session.end(reason=command.reason)
        await self._repository.save(session)

        # ドメインイベントを発行
        for event in session.get_domain_events():
            await self._publisher.publish(event, type(event).__name__)


class ExecuteAgentHandler:
    """エージェント実行ハンドラ"""

    def __init__(
        self,
        session_repository: SessionRepository,
        agent_port: AgentPort,
        event_publisher: EventPublisher,
    ):
        self._repository = session_repository
        self._agent = agent_port
        self._publisher = event_publisher

    async def handle(self, command: ExecuteAgentCommand) -> dict[str, Any]:
        """エージェントを実行"""
        session = await self._repository.find_by_id(SessionId(command.session_id))
        if not session:
            raise SessionNotFoundError(command.session_id)

        # コンテキストを取得
        context = session.get_context(limit=10)

        # エージェント実行
        if command.tools:
            response = await self._agent.execute_with_tools(
                context=context,
                instruction=command.instruction,
                tools=command.tools,
            )
        else:
            response = await self._agent.execute(
                context=context,
                instruction=command.instruction,
            )

        # レスポンスをメッセージとして追加
        assistant_message = Message(
            id=MessageId(str(ULID())),
            session_id=session.id,
            role="assistant",
            content=Content(text=response.content),
        )
        session.add_message(assistant_message)
        await self._repository.save(session)

        # ドメインイベントを発行
        for event in session.get_domain_events():
            await self._publisher.publish(event, type(event).__name__)

        return {
            "message_id": str(assistant_message.id),
            "content": response.content,
            "tool_calls": response.tool_calls,
            "metadata": response.metadata,
        }


class SessionNotFoundError(Exception):
    """セッション未発見エラー"""

    def __init__(self, session_id: str):
        super().__init__(f"Session not found: {session_id}")
        self.session_id = session_id

