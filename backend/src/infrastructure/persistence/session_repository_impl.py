"""Session Repository Implementation - Event Sourcing based

イベントソーシングを使用したセッションリポジトリの実装。
イベントストアからイベントを再生してアグリゲートを復元。
"""

from datetime import datetime
from typing import Any

from domain.entities.message import Message
from domain.entities.session import Session, SessionState
from domain.events.session_events import MessageAdded, SessionEnded, SessionStarted
from domain.repositories.session_repository import SessionRepository
from domain.value_objects.content import Content
from domain.value_objects.ids import AgentId, MessageId, SessionId, UserId
from infrastructure.persistence.event_store import EventStore, StoredEvent


class EventSourcedSessionRepository(SessionRepository):
    """イベントソーシングベースのセッションリポジトリ"""

    def __init__(self, event_store: EventStore):
        self._event_store = event_store

    async def save(self, session: Session) -> None:
        """セッションを保存（ドメインイベントを永続化）"""
        events = session.get_domain_events()
        if not events:
            return

        stored_events = []
        base_version = session._version - len(events)

        for i, event in enumerate(events):
            stored_events.append(
                StoredEvent(
                    aggregate_id=str(session.id),
                    aggregate_type="Session",
                    event_type=type(event).__name__,
                    event_data=self._event_to_dict(event),
                    version=base_version + i + 1,
                    timestamp=datetime.utcnow().isoformat(),
                )
            )

        await self._event_store.append(str(session.id), stored_events)
        session.clear_domain_events()

    async def find_by_id(self, session_id: SessionId) -> Session | None:
        """セッションIDで検索（イベント再生）"""
        events = await self._event_store.get_events(str(session_id))
        if not events:
            return None

        return self._rebuild_from_events(events)

    async def find_active_by_user(self, user_id: UserId) -> list[Session]:
        """ユーザーのアクティブセッションを検索"""
        # 注意: 実際のプロダクションでは読み取りモデル（CQRS）を使用すべき
        # ここでは簡易実装としてSessionStartedイベントから検索
        started_events = await self._event_store.get_events_by_type("SessionStarted")

        sessions = []
        for event in started_events:
            if event.event_data.get("user_id") == str(user_id):
                session = await self.find_by_id(
                    SessionId(event.event_data["session_id"])
                )
                if session and session.is_active:
                    sessions.append(session)

        return sessions

    async def delete(self, session_id: SessionId) -> None:
        """セッションを削除（論理削除: 終了イベント発行）"""
        session = await self.find_by_id(session_id)
        if session and session.is_active:
            session.end(reason="deleted")
            await self.save(session)

    def _rebuild_from_events(self, events: list[StoredEvent]) -> Session:
        """イベントからアグリゲートを再構築"""
        session: Session | None = None

        for event in events:
            if event.event_type == "SessionStarted":
                session = self._apply_session_started(event.event_data)
            elif event.event_type == "MessageAdded" and session:
                self._apply_message_added(session, event.event_data)
            elif event.event_type == "SessionEnded" and session:
                self._apply_session_ended(session, event.event_data)

            if session:
                session._version = event.version

        return session

    def _apply_session_started(self, data: dict[str, Any]) -> Session:
        """SessionStartedイベントを適用"""
        return Session(
            id=SessionId(data["session_id"]),
            agent_id=AgentId(data["agent_id"]),
            user_id=UserId(data["user_id"]),
            state=SessionState.ACTIVE,
            created_at=datetime.fromisoformat(data["timestamp"]),
            updated_at=datetime.fromisoformat(data["timestamp"]),
        )

    def _apply_message_added(self, session: Session, data: dict[str, Any]) -> None:
        """MessageAddedイベントを適用"""
        message = Message(
            id=MessageId(data["message_id"]),
            session_id=session.id,
            role=data["role"],
            content=Content(text=data["content"]),
            created_at=datetime.fromisoformat(data["timestamp"]),
        )
        session._messages.append(message)
        session.updated_at = message.created_at

    def _apply_session_ended(self, session: Session, data: dict[str, Any]) -> None:
        """SessionEndedイベントを適用"""
        session.state = SessionState.ENDED
        session.updated_at = datetime.fromisoformat(data["timestamp"])

    def _event_to_dict(self, event) -> dict[str, Any]:
        """イベントを辞書に変換"""
        if isinstance(event, SessionStarted):
            return {
                "session_id": event.session_id,
                "agent_id": event.agent_id,
                "user_id": event.user_id,
                "timestamp": event.timestamp,
            }
        elif isinstance(event, MessageAdded):
            return {
                "session_id": event.session_id,
                "message_id": event.message_id,
                "role": event.role,
                "content": event.content,
                "timestamp": event.timestamp,
            }
        elif isinstance(event, SessionEnded):
            return {
                "session_id": event.session_id,
                "reason": event.reason,
                "timestamp": event.timestamp,
            }
        return {}

