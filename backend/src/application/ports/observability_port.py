"""Observability Port - Observability Service Interface

AgentCore Observability / LangFuse / LangSmith に対応。
トレーシング、メトリクス、ログ収集。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime
from enum import Enum


class TraceStatus(str, Enum):
    """トレースステータス"""
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


class SpanKind(str, Enum):
    """Spanの種類"""
    LLM = "llm"
    TOOL = "tool"
    RETRIEVAL = "retrieval"
    EMBEDDING = "embedding"
    CHAIN = "chain"
    AGENT = "agent"
    CUSTOM = "custom"


@dataclass
class ObservabilityConfig:
    """Observability設定"""
    provider: str = "local"  # "local", "langfuse", "langsmith", "agentcore"
    project_name: str = "default"
    api_key: str | None = None
    api_url: str | None = None
    enable_metrics: bool = True
    enable_logging: bool = True
    sample_rate: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Span:
    """Span（トレースの単位）"""
    span_id: str
    name: str
    kind: SpanKind
    start_time: datetime
    end_time: datetime | None = None
    status: TraceStatus = TraceStatus.RUNNING
    input_data: Any | None = None
    output_data: Any | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    parent_span_id: str | None = None


@dataclass
class Trace:
    """トレース"""
    trace_id: str
    name: str
    start_time: datetime
    end_time: datetime | None = None
    status: TraceStatus = TraceStatus.RUNNING
    spans: list[Span] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Metric:
    """メトリクス"""
    name: str
    value: float
    timestamp: datetime
    tags: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class ObservabilityPort(ABC):
    """Observability Port - 監視・トレーシング

    Strands Agents: AgentCore Observability
    LangChain: LangFuse / LangSmith
    """

    @abstractmethod
    async def initialize(self, config: ObservabilityConfig) -> bool:
        """Observabilityを初期化"""
        ...

    # Tracing
    @abstractmethod
    async def start_trace(
        self,
        name: str,
        metadata: dict[str, Any] | None = None,
    ) -> Trace:
        """トレースを開始"""
        ...

    @abstractmethod
    async def end_trace(
        self,
        trace_id: str,
        status: TraceStatus = TraceStatus.COMPLETED,
    ) -> Trace:
        """トレースを終了"""
        ...

    @abstractmethod
    async def start_span(
        self,
        trace_id: str,
        name: str,
        kind: SpanKind,
        parent_span_id: str | None = None,
        input_data: Any | None = None,
    ) -> Span:
        """Spanを開始"""
        ...

    @abstractmethod
    async def end_span(
        self,
        span_id: str,
        output_data: Any | None = None,
        status: TraceStatus = TraceStatus.COMPLETED,
    ) -> Span:
        """Spanを終了"""
        ...

    @abstractmethod
    async def add_span_event(
        self,
        span_id: str,
        event_name: str,
        attributes: dict[str, Any] | None = None,
    ) -> bool:
        """SpanにEventを追加"""
        ...

    # Metrics
    @abstractmethod
    async def record_metric(
        self,
        name: str,
        value: float,
        tags: dict[str, str] | None = None,
    ) -> bool:
        """メトリクスを記録"""
        ...

    @abstractmethod
    async def get_metrics(
        self,
        name: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[Metric]:
        """メトリクスを取得"""
        ...

    # Logging
    @abstractmethod
    async def log(
        self,
        level: str,
        message: str,
        trace_id: str | None = None,
        span_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """ログを記録"""
        ...

    # Query
    @abstractmethod
    async def get_trace(self, trace_id: str) -> Trace | None:
        """トレースを取得"""
        ...

    @abstractmethod
    async def list_traces(
        self,
        limit: int = 100,
        status: TraceStatus | None = None,
    ) -> list[Trace]:
        """トレース一覧を取得"""
        ...

