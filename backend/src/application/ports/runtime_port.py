"""Runtime Port - Agent Runtime Service Interface

AgentCore Runtime / LangGraph Runtimeに対応。
エージェントの実行環境とライフサイクル管理。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator
from enum import Enum


class RuntimeStatus(str, Enum):
    """ランタイムステータス"""
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    TERMINATED = "terminated"


@dataclass
class RuntimeConfig:
    """ランタイム設定"""
    model_id: str
    region: str = "us-east-1"
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout_seconds: int = 300
    max_iterations: int = 10
    system_prompt: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """実行結果"""
    content: str
    status: RuntimeStatus
    iterations: int = 1
    tokens_used: int = 0
    execution_time_ms: int = 0
    tool_calls: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class RuntimePort(ABC):
    """Runtime Port - エージェント実行環境

    Strands Agents: Agent Runtime
    LangChain: LangGraph Runtime / RunnableSequence
    """

    @abstractmethod
    async def initialize(self, config: RuntimeConfig) -> RuntimeStatus:
        """ランタイムを初期化"""
        ...

    @abstractmethod
    async def execute(
        self,
        instruction: str,
        context: list[dict[str, Any]] | None = None,
    ) -> ExecutionResult:
        """同期実行"""
        ...

    @abstractmethod
    async def execute_stream(
        self,
        instruction: str,
        context: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[str]:
        """ストリーミング実行"""
        ...

    @abstractmethod
    async def execute_with_tools(
        self,
        instruction: str,
        tools: list[Any],
        context: list[dict[str, Any]] | None = None,
    ) -> ExecutionResult:
        """ツール付き実行"""
        ...

    @abstractmethod
    async def get_status(self) -> RuntimeStatus:
        """ステータス取得"""
        ...

    @abstractmethod
    async def pause(self) -> bool:
        """一時停止"""
        ...

    @abstractmethod
    async def resume(self) -> bool:
        """再開"""
        ...

    @abstractmethod
    async def terminate(self) -> bool:
        """終了"""
        ...

