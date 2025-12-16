"""ID Value Objects"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SessionId:
    value: str
    def __str__(self) -> str: return self.value
    def __hash__(self) -> int: return hash(self.value)


@dataclass(frozen=True)
class AgentId:
    value: str
    def __str__(self) -> str: return self.value
    def __hash__(self) -> int: return hash(self.value)


@dataclass(frozen=True)
class UserId:
    value: str
    def __str__(self) -> str: return self.value
    def __hash__(self) -> int: return hash(self.value)


@dataclass(frozen=True)
class MessageId:
    value: str
    def __str__(self) -> str: return self.value
    def __hash__(self) -> int: return hash(self.value)


