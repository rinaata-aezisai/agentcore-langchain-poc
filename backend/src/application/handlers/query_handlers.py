"""Query Handlers

クエリを処理するハンドラ。読み取り専用操作。
"""

from dataclasses import dataclass

from application.queries import (
    GetActiveSessionsQuery,
    GetSessionMessagesQuery,
    GetSessionQuery,
)
from domain.entities.session import Session
from domain.repositories.session_repository import SessionRepository
from domain.value_objects.ids import SessionId, UserId


@dataclass
class SessionDTO:
    """セッションDTO"""

    id: str
    agent_id: str
    user_id: str
    state: str
    created_at: str
    updated_at: str
    message_count: int


@dataclass
class MessageDTO:
    """メッセージDTO"""

    id: str
    role: str
    content: str
    created_at: str


class GetSessionHandler:
    """セッション取得ハンドラ"""

    def __init__(self, session_repository: SessionRepository):
        self._repository = session_repository

    async def handle(self, query: GetSessionQuery) -> SessionDTO | None:
        """セッションを取得"""
        session = await self._repository.find_by_id(SessionId(query.session_id))
        if not session:
            return None

        return self._to_dto(session)

    def _to_dto(self, session: Session) -> SessionDTO:
        return SessionDTO(
            id=str(session.id),
            agent_id=str(session.agent_id),
            user_id=str(session.user_id),
            state=session.state.value,
            created_at=session.created_at.isoformat(),
            updated_at=session.updated_at.isoformat(),
            message_count=len(session.messages),
        )


class GetSessionMessagesHandler:
    """セッションメッセージ取得ハンドラ"""

    def __init__(self, session_repository: SessionRepository):
        self._repository = session_repository

    async def handle(self, query: GetSessionMessagesQuery) -> list[MessageDTO]:
        """メッセージを取得"""
        session = await self._repository.find_by_id(SessionId(query.session_id))
        if not session:
            return []

        messages = session.messages[query.offset : query.offset + query.limit]
        return [self._to_dto(m) for m in messages]

    def _to_dto(self, message) -> MessageDTO:
        return MessageDTO(
            id=str(message.id),
            role=message.role,
            content=message.content.text,
            created_at=message.created_at.isoformat(),
        )


class GetActiveSessionsHandler:
    """アクティブセッション取得ハンドラ"""

    def __init__(self, session_repository: SessionRepository):
        self._repository = session_repository

    async def handle(self, query: GetActiveSessionsQuery) -> list[SessionDTO]:
        """アクティブセッションを取得"""
        sessions = await self._repository.find_active_by_user(UserId(query.user_id))
        return [self._to_session_dto(s) for s in sessions]

    def _to_session_dto(self, session: Session) -> SessionDTO:
        return SessionDTO(
            id=str(session.id),
            agent_id=str(session.agent_id),
            user_id=str(session.user_id),
            state=session.state.value,
            created_at=session.created_at.isoformat(),
            updated_at=session.updated_at.isoformat(),
            message_count=len(session.messages),
        )

