"""LangChain Observability Adapter

LangFuse / LangSmith による実装。
トレーシング、メトリクス、ログ収集。
"""

import os
from datetime import datetime
from typing import Any
import uuid

import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent.parent.parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_path))

from application.ports.observability_port import (
    ObservabilityPort,
    ObservabilityConfig,
    TraceStatus,
    SpanKind,
    Trace,
    Span,
    Metric,
)


class LangChainObservabilityAdapter(ObservabilityPort):
    """LangChain Observability (LangFuse/LangSmith) アダプター
    
    LangChain相当機能:
    - LangFuse統合
    - LangSmith統合
    - Callbacks
    """

    def __init__(self):
        self._config: ObservabilityConfig | None = None
        self._traces: dict[str, Trace] = {}
        self._spans: dict[str, Span] = {}
        self._metrics: list[Metric] = []
        self._logs: list[dict[str, Any]] = []
        self._langfuse = None
        self._langsmith_client = None

    async def initialize(self, config: ObservabilityConfig) -> bool:
        """Observabilityを初期化"""
        self._config = config
        
        # LangFuse初期化
        if config.provider == "langfuse":
            try:
                from langfuse import Langfuse
                self._langfuse = Langfuse(
                    public_key=config.api_key or os.getenv("LANGFUSE_PUBLIC_KEY"),
                    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
                    host=config.api_url or os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
                )
            except ImportError:
                pass
        
        # LangSmith初期化
        elif config.provider == "langsmith":
            try:
                from langsmith import Client
                self._langsmith_client = Client(
                    api_key=config.api_key or os.getenv("LANGCHAIN_API_KEY"),
                )
            except ImportError:
                pass
        
        return True

    # Tracing
    async def start_trace(
        self,
        name: str,
        metadata: dict[str, Any] | None = None,
    ) -> Trace:
        """トレースを開始"""
        trace_id = str(uuid.uuid4())
        
        # LangFuseトレース
        langfuse_trace = None
        if self._langfuse:
            try:
                langfuse_trace = self._langfuse.trace(
                    name=name,
                    metadata=metadata,
                )
                trace_id = langfuse_trace.id
            except Exception:
                pass
        
        trace = Trace(
            trace_id=trace_id,
            name=name,
            start_time=datetime.now(),
            status=TraceStatus.RUNNING,
            metadata={
                **(metadata or {}),
                "provider": self._config.provider if self._config else "local",
                "langfuse_trace_id": langfuse_trace.id if langfuse_trace else None,
            },
        )
        
        self._traces[trace_id] = trace
        return trace

    async def end_trace(
        self,
        trace_id: str,
        status: TraceStatus = TraceStatus.COMPLETED,
    ) -> Trace:
        """トレースを終了"""
        trace = self._traces.get(trace_id)
        if not trace:
            raise ValueError(f"Trace not found: {trace_id}")
        
        trace.end_time = datetime.now()
        trace.status = status
        
        # LangFuseフラッシュ
        if self._langfuse:
            try:
                self._langfuse.flush()
            except Exception:
                pass
        
        return trace

    async def start_span(
        self,
        trace_id: str,
        name: str,
        kind: SpanKind,
        parent_span_id: str | None = None,
        input_data: Any | None = None,
    ) -> Span:
        """Spanを開始"""
        span_id = str(uuid.uuid4())
        
        # LangFuse Span
        if self._langfuse:
            try:
                langfuse_span = self._langfuse.span(
                    name=name,
                    trace_id=trace_id,
                    parent_observation_id=parent_span_id,
                    input=input_data,
                    metadata={"kind": kind.value},
                )
                span_id = langfuse_span.id
            except Exception:
                pass
        
        span = Span(
            span_id=span_id,
            name=name,
            kind=kind,
            start_time=datetime.now(),
            status=TraceStatus.RUNNING,
            input_data=input_data,
            parent_span_id=parent_span_id,
        )
        
        self._spans[span_id] = span
        
        trace = self._traces.get(trace_id)
        if trace:
            trace.spans.append(span)
        
        return span

    async def end_span(
        self,
        span_id: str,
        output_data: Any | None = None,
        status: TraceStatus = TraceStatus.COMPLETED,
    ) -> Span:
        """Spanを終了"""
        span = self._spans.get(span_id)
        if not span:
            raise ValueError(f"Span not found: {span_id}")
        
        span.end_time = datetime.now()
        span.output_data = output_data
        span.status = status
        
        return span

    async def add_span_event(
        self,
        span_id: str,
        event_name: str,
        attributes: dict[str, Any] | None = None,
    ) -> bool:
        """SpanにEventを追加"""
        span = self._spans.get(span_id)
        if not span:
            return False
        
        span.events.append({
            "name": event_name,
            "timestamp": datetime.now().isoformat(),
            "attributes": attributes or {},
        })
        
        return True

    # Metrics
    async def record_metric(
        self,
        name: str,
        value: float,
        tags: dict[str, str] | None = None,
    ) -> bool:
        """メトリクスを記録"""
        metric = Metric(
            name=name,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {},
        )
        
        self._metrics.append(metric)
        
        # LangFuseスコア
        if self._langfuse and name.startswith("score_"):
            try:
                self._langfuse.score(
                    name=name,
                    value=value,
                    data_type="NUMERIC",
                )
            except Exception:
                pass
        
        return True

    async def get_metrics(
        self,
        name: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[Metric]:
        """メトリクスを取得"""
        filtered = self._metrics
        
        if name:
            filtered = [m for m in filtered if m.name == name]
        if start_time:
            filtered = [m for m in filtered if m.timestamp >= start_time]
        if end_time:
            filtered = [m for m in filtered if m.timestamp <= end_time]
        
        return filtered

    # Logging
    async def log(
        self,
        level: str,
        message: str,
        trace_id: str | None = None,
        span_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """ログを記録"""
        log_entry = {
            "level": level,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "trace_id": trace_id,
            "span_id": span_id,
            "metadata": metadata or {},
            "provider": "langfuse" if self._langfuse else "local",
        }
        
        self._logs.append(log_entry)
        
        if self._config and self._config.enable_logging:
            print(f"[{level.upper()}][LangChain] {message}")
        
        return True

    # Query
    async def get_trace(self, trace_id: str) -> Trace | None:
        """トレースを取得"""
        return self._traces.get(trace_id)

    async def list_traces(
        self,
        limit: int = 100,
        status: TraceStatus | None = None,
    ) -> list[Trace]:
        """トレース一覧を取得"""
        traces = list(self._traces.values())
        
        if status:
            traces = [t for t in traces if t.status == status]
        
        traces.sort(key=lambda t: t.start_time, reverse=True)
        
        return traces[:limit]


def create_langchain_observability() -> LangChainObservabilityAdapter:
    """ファクトリ関数"""
    return LangChainObservabilityAdapter()

