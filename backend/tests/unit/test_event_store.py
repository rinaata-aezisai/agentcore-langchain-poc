"""Event Store Unit Tests"""

import pytest
from datetime import datetime
from infrastructure.persistence.event_store import (
    InMemoryEventStore,
    StoredEvent,
    ConcurrencyError,
)


@pytest.fixture
def event_store():
    return InMemoryEventStore()


@pytest.fixture
def sample_events():
    return [
        StoredEvent(
            aggregate_id="session-001",
            aggregate_type="Session",
            event_type="SessionStarted",
            event_data={
                "session_id": "session-001",
                "agent_id": "agent-001",
                "user_id": "user-001",
            },
            version=1,
            timestamp=datetime.utcnow().isoformat(),
        ),
        StoredEvent(
            aggregate_id="session-001",
            aggregate_type="Session",
            event_type="MessageAdded",
            event_data={
                "session_id": "session-001",
                "message_id": "msg-001",
                "role": "user",
                "content": "Hello",
            },
            version=2,
            timestamp=datetime.utcnow().isoformat(),
        ),
    ]


class TestInMemoryEventStore:
    """InMemoryEventStoreのテスト"""

    @pytest.mark.asyncio
    async def test_append_and_get_events(self, event_store, sample_events):
        """イベントの追加と取得"""
        await event_store.append("session-001", sample_events)

        events = await event_store.get_events("session-001")
        assert len(events) == 2
        assert events[0].event_type == "SessionStarted"
        assert events[1].event_type == "MessageAdded"

    @pytest.mark.asyncio
    async def test_get_events_from_version(self, event_store, sample_events):
        """指定バージョン以降のイベント取得"""
        await event_store.append("session-001", sample_events)

        events = await event_store.get_events("session-001", from_version=2)
        assert len(events) == 1
        assert events[0].event_type == "MessageAdded"

    @pytest.mark.asyncio
    async def test_get_latest_version(self, event_store, sample_events):
        """最新バージョンの取得"""
        await event_store.append("session-001", sample_events)

        version = await event_store.get_latest_version("session-001")
        assert version == 2

    @pytest.mark.asyncio
    async def test_get_latest_version_empty(self, event_store):
        """存在しないアグリゲートのバージョン"""
        version = await event_store.get_latest_version("nonexistent")
        assert version == 0

    @pytest.mark.asyncio
    async def test_concurrency_error(self, event_store, sample_events):
        """楽観的ロック競合エラー"""
        await event_store.append("session-001", sample_events)

        # 同じバージョンで追加しようとするとエラー
        conflicting_event = StoredEvent(
            aggregate_id="session-001",
            aggregate_type="Session",
            event_type="SessionEnded",
            event_data={"session_id": "session-001"},
            version=2,  # 既に存在するバージョン
            timestamp=datetime.utcnow().isoformat(),
        )

        with pytest.raises(ConcurrencyError):
            await event_store.append("session-001", [conflicting_event])

