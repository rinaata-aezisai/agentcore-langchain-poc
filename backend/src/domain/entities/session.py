"""Session Aggregate Root"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from ulid import ULID
from domain.events.session_events import SessionStarted, SessionEnded, MessageAdded
from domain.value_objects.ids import SessionId, AgentId, UserId
from domain.value_objects.content import Content

if TYPE_CHECKING:
    from domain.entities.message import Message


class SessionState(str, Enum):
    ACTIVE = "active"
    ENDED = "ended"


@dataclass
class Session:
    """セッションアグリゲート"""

    id: SessionId
    agent_id: AgentId
    user_id: UserId
    state: SessionState = SessionState.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    _messages: list[Message] = field(default_factory=list)
    _domain_events: list = field(default_factory=list)
    _version: int = 0

    @classmethod
    def start(cls, agent_id: AgentId, user_id: UserId) -> Session:
        """新しいセッションを開始"""
        session_id = SessionId(str(ULID()))
        now = datetime.utcnow()
        session = cls(
            id=session_id, agent_id=agent_id, user_id=user_id,
            state=SessionState.ACTIVE, created_at=now, updated_at=now,
        )
        session._add_event(SessionStarted(
            session_id=str(session_id), agent_id=str(agent_id),
            user_id=str(user_id), timestamp=now.isoformat(),
        ))
        return session

    def add_message(self, message: Message) -> None:
        """メッセージを追加"""
        self._ensure_active()
        self._messages.append(message)
        self.updated_at = datetime.utcnow()
        self._add_event(MessageAdded(
            session_id=str(self.id), message_id=str(message.id),
            role=message.role, content=message.content.text,
            timestamp=self.updated_at.isoformat(),
        ))

    def end(self, reason: str = "user_requested") -> None:
        """セッションを終了"""
        self._ensure_active()
        self.state = SessionState.ENDED
        self.updated_at = datetime.utcnow()
        self._add_event(SessionEnded(
            session_id=str(self.id), reason=reason,
            timestamp=self.updated_at.isoformat(),
        ))

    def get_context(self, limit: int = 10) -> list[Message]:
        return self._messages[-limit:]

    @property
    def messages(self) -> list[Message]:
        return list(self._messages)

    @property
    def is_active(self) -> bool:
        return self.state == SessionState.ACTIVE

    def get_domain_events(self) -> list:
        return list(self._domain_events)

    def clear_domain_events(self) -> None:
        self._domain_events.clear()

    def _add_event(self, event) -> None:
        self._domain_events.append(event)
        self._version += 1

    def _ensure_active(self) -> None:
        if not self.is_active:
            raise SessionNotActiveError(self.id)


class SessionNotActiveError(Exception):
    def __init__(self, session_id: SessionId):
        super().__init__(f"Session {session_id} is not active")
        self.session_id = session_id


