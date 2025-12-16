"""Session Domain Events"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass
class DomainEvent:
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def event_type(self) -> str:
        return self.__class__.__name__


@dataclass
class SessionStarted(DomainEvent):
    session_id: str = ""
    agent_id: str = ""
    user_id: str = ""


@dataclass
class SessionEnded(DomainEvent):
    session_id: str = ""
    reason: str = "user_requested"


@dataclass
class MessageAdded(DomainEvent):
    session_id: str = ""
    message_id: str = ""
    role: str = ""
    content: str = ""


@dataclass
class ToolExecutionCompleted(DomainEvent):
    session_id: str = ""
    tool_call_id: str = ""
    result: Any = None
    latency_ms: int = 0


