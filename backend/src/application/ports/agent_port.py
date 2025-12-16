"""Agent Port - Abstract interface for AI agents

This port allows switching between AgentCore (Strands) and LangChain implementations.
The actual implementations are in poc/agentcore and poc/langchain.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from domain.entities.message import Message


@dataclass
class AgentResponse:
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentPort(ABC):
    """エージェントポート - AgentCore/LangChain切替可能"""

    @abstractmethod
    async def execute(self, context: list[Message], instruction: str) -> AgentResponse:
        """エージェントを実行"""
        ...

    @abstractmethod
    async def execute_with_tools(
        self, context: list[Message], instruction: str, tools: list[dict[str, Any]],
    ) -> AgentResponse:
        """ツール付きでエージェントを実行"""
        ...


