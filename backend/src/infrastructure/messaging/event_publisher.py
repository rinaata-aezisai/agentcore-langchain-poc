"""Event Publisher - EventBridge integration

ドメインイベントをEventBridgeに発行するパブリッシャー。
イベント駆動アーキテクチャをサポート。
"""

import json
from abc import ABC, abstractmethod
from dataclasses import asdict
from datetime import datetime
from typing import Any

import boto3


class EventPublisher(ABC):
    """イベントパブリッシャー抽象インターフェース"""

    @abstractmethod
    async def publish(self, event: Any, event_type: str) -> None:
        """イベントを発行"""
        ...

    @abstractmethod
    async def publish_batch(self, events: list[tuple[Any, str]]) -> None:
        """複数イベントを発行"""
        ...


class EventBridgePublisher(EventPublisher):
    """Amazon EventBridge パブリッシャー"""

    def __init__(
        self,
        event_bus_name: str = "agentcore-poc-events",
        source: str = "agentcore.poc",
        region: str = "us-east-1",
    ):
        self.event_bus_name = event_bus_name
        self.source = source
        self.client = boto3.client("events", region_name=region)

    async def publish(self, event: Any, event_type: str) -> None:
        """単一イベントを発行"""
        await self.publish_batch([(event, event_type)])

    async def publish_batch(self, events: list[tuple[Any, str]]) -> None:
        """複数イベントをバッチ発行"""
        if not events:
            return

        entries = []
        for event, event_type in events:
            event_data = self._serialize_event(event)
            entries.append(
                {
                    "Source": self.source,
                    "DetailType": event_type,
                    "Detail": json.dumps(event_data),
                    "EventBusName": self.event_bus_name,
                    "Time": datetime.utcnow(),
                }
            )

        # EventBridgeは1回のputで最大10件まで
        for i in range(0, len(entries), 10):
            batch = entries[i : i + 10]
            response = self.client.put_events(Entries=batch)

            failed = response.get("FailedEntryCount", 0)
            if failed > 0:
                # 失敗したエントリをログ（本番ではリトライ処理）
                for entry in response.get("Entries", []):
                    if entry.get("ErrorCode"):
                        print(f"Failed to publish event: {entry}")

    def _serialize_event(self, event: Any) -> dict[str, Any]:
        """イベントをシリアライズ"""
        if hasattr(event, "__dataclass_fields__"):
            return asdict(event)
        elif hasattr(event, "dict"):
            return event.dict()
        elif isinstance(event, dict):
            return event
        else:
            return {"data": str(event)}


class InMemoryEventPublisher(EventPublisher):
    """テスト用インメモリパブリッシャー"""

    def __init__(self):
        self.published_events: list[tuple[Any, str]] = []

    async def publish(self, event: Any, event_type: str) -> None:
        self.published_events.append((event, event_type))

    async def publish_batch(self, events: list[tuple[Any, str]]) -> None:
        self.published_events.extend(events)

    def clear(self) -> None:
        self.published_events.clear()

    def get_events_by_type(self, event_type: str) -> list[Any]:
        return [e for e, t in self.published_events if t == event_type]


