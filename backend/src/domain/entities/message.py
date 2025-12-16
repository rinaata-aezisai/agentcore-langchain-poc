"""Message Entity"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

import ulid

from domain.value_objects.content import Content
from domain.value_objects.ids import MessageId

Role = Literal["user", "assistant", "system"]


def _now() -> datetime:
    """タイムゾーン対応の現在時刻を取得"""
    return datetime.now(UTC)


@dataclass
class ToolCall:
    tool_id: str
    params: dict[str, Any]
    result: Any | None = None


@dataclass
class Message:
    """メッセージエンティティ"""

    id: MessageId
    role: Role
    content: Content
    tool_calls: list[ToolCall] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=_now)

    @classmethod
    def user(cls, content: Content, metadata: dict[str, Any] | None = None) -> "Message":
        return cls(
            id=MessageId(ulid.new().str),
            role="user",
            content=content,
            metadata=metadata or {},
        )

    @classmethod
    def assistant(
        cls, content: Content, tool_calls: list[ToolCall] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "Message":
        return cls(
            id=MessageId(ulid.new().str),
            role="assistant",
            content=content,
            tool_calls=tool_calls or [],
            metadata=metadata or {},
        )

    @classmethod
    def system(cls, content: Content) -> "Message":
        return cls(id=MessageId(ulid.new().str), role="system", content=content)
