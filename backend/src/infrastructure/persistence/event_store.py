"""Event Store - DynamoDB based Event Sourcing storage

イベントソーシングのためのイベントストア実装。
DynamoDBを使用し、イベントの永続化と再生をサポート。
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, TypeVar

import boto3

T = TypeVar("T")


@dataclass
class StoredEvent:
    """永続化されたイベント"""

    aggregate_id: str
    aggregate_type: str
    event_type: str
    event_data: dict[str, Any]
    version: int
    timestamp: str
    metadata: dict[str, Any] = field(default_factory=dict)


class EventStore(ABC):
    """イベントストア抽象インターフェース"""

    @abstractmethod
    async def append(self, aggregate_id: str, events: list[StoredEvent]) -> None:
        """イベントを追加"""
        ...

    @abstractmethod
    async def get_events(
        self, aggregate_id: str, from_version: int = 0
    ) -> list[StoredEvent]:
        """イベントを取得"""
        ...

    @abstractmethod
    async def get_latest_version(self, aggregate_id: str) -> int:
        """最新バージョンを取得"""
        ...


class DynamoDBEventStore(EventStore):
    """DynamoDB実装のイベントストア"""

    def __init__(
        self,
        table_name: str = "agentcore-poc-events",
        region: str = "us-east-1",
        endpoint_url: str | None = None,
    ):
        self.table_name = table_name
        session = boto3.Session(region_name=region)
        dynamodb_kwargs = {"service_name": "dynamodb"}
        if endpoint_url:
            dynamodb_kwargs["endpoint_url"] = endpoint_url

        self.dynamodb = session.resource(**dynamodb_kwargs)
        self.table = self.dynamodb.Table(table_name)

    async def append(self, aggregate_id: str, events: list[StoredEvent]) -> None:
        """イベントをDynamoDBに追加（楽観的ロック付き）"""
        if not events:
            return

        current_version = await self.get_latest_version(aggregate_id)
        expected_version = events[0].version - 1

        if current_version != expected_version:
            raise ConcurrencyError(
                f"Expected version {expected_version}, but found {current_version}"
            )

        with self.table.batch_writer() as batch:
            for event in events:
                item = {
                    "PK": f"AGGREGATE#{aggregate_id}",
                    "SK": f"VERSION#{event.version:010d}",
                    "aggregate_id": aggregate_id,
                    "aggregate_type": event.aggregate_type,
                    "event_type": event.event_type,
                    "event_data": json.dumps(event.event_data),
                    "version": event.version,
                    "timestamp": event.timestamp,
                    "metadata": json.dumps(event.metadata),
                    "GSI1PK": f"TYPE#{event.event_type}",
                    "GSI1SK": event.timestamp,
                }
                batch.put_item(Item=item)

    async def get_events(
        self, aggregate_id: str, from_version: int = 0
    ) -> list[StoredEvent]:
        """アグリゲートのイベントを取得"""
        response = self.table.query(
            KeyConditionExpression="PK = :pk AND SK >= :sk",
            ExpressionAttributeValues={
                ":pk": f"AGGREGATE#{aggregate_id}",
                ":sk": f"VERSION#{from_version:010d}",
            },
        )

        events = []
        for item in response.get("Items", []):
            events.append(
                StoredEvent(
                    aggregate_id=item["aggregate_id"],
                    aggregate_type=item["aggregate_type"],
                    event_type=item["event_type"],
                    event_data=json.loads(item["event_data"]),
                    version=int(item["version"]),
                    timestamp=item["timestamp"],
                    metadata=json.loads(item.get("metadata", "{}")),
                )
            )

        return sorted(events, key=lambda e: e.version)

    async def get_latest_version(self, aggregate_id: str) -> int:
        """アグリゲートの最新バージョンを取得"""
        response = self.table.query(
            KeyConditionExpression="PK = :pk",
            ExpressionAttributeValues={
                ":pk": f"AGGREGATE#{aggregate_id}",
            },
            ScanIndexForward=False,
            Limit=1,
        )

        items = response.get("Items", [])
        if not items:
            return 0

        return int(items[0]["version"])

    async def get_events_by_type(
        self,
        event_type: str,
        from_timestamp: str | None = None,
        limit: int = 100,
    ) -> list[StoredEvent]:
        """イベントタイプでイベントを取得（GSI使用）"""
        query_params = {
            "IndexName": "GSI1",
            "KeyConditionExpression": "GSI1PK = :pk",
            "ExpressionAttributeValues": {
                ":pk": f"TYPE#{event_type}",
            },
            "Limit": limit,
        }

        if from_timestamp:
            query_params["KeyConditionExpression"] += " AND GSI1SK >= :ts"
            query_params["ExpressionAttributeValues"][":ts"] = from_timestamp

        response = self.table.query(**query_params)

        events = []
        for item in response.get("Items", []):
            events.append(
                StoredEvent(
                    aggregate_id=item["aggregate_id"],
                    aggregate_type=item["aggregate_type"],
                    event_type=item["event_type"],
                    event_data=json.loads(item["event_data"]),
                    version=int(item["version"]),
                    timestamp=item["timestamp"],
                    metadata=json.loads(item.get("metadata", "{}")),
                )
            )

        return events


class InMemoryEventStore(EventStore):
    """テスト用インメモリイベントストア"""

    def __init__(self):
        self._events: dict[str, list[StoredEvent]] = {}

    async def append(self, aggregate_id: str, events: list[StoredEvent]) -> None:
        if aggregate_id not in self._events:
            self._events[aggregate_id] = []

        current_version = await self.get_latest_version(aggregate_id)
        expected_version = events[0].version - 1 if events else 0

        if current_version != expected_version:
            raise ConcurrencyError(
                f"Expected version {expected_version}, but found {current_version}"
            )

        self._events[aggregate_id].extend(events)

    async def get_events(
        self, aggregate_id: str, from_version: int = 0
    ) -> list[StoredEvent]:
        events = self._events.get(aggregate_id, [])
        return [e for e in events if e.version >= from_version]

    async def get_latest_version(self, aggregate_id: str) -> int:
        events = self._events.get(aggregate_id, [])
        if not events:
            return 0
        return max(e.version for e in events)


class ConcurrencyError(Exception):
    """楽観的ロック競合エラー"""

    pass

