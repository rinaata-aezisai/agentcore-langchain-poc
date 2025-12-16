"""Strands Observability Adapter

AgentCore Observability サービスの実装。
トレーシング、メトリクス、ログ収集。
"""

import asyncio
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


class StrandsObservabilityAdapter(ObservabilityPort):
    """Strands Agents Observability アダプター
    
    AgentCore Observabilityの機能:
    - 分散トレーシング
    - メトリクス収集
    - ログ管理
    - パフォーマンス監視
    """

    def __init__(self):
        self._config: ObservabilityConfig | None = None
        self._traces: dict[str, Trace] = {}
        self._spans: dict[str, Span] = {}
        self._metrics: list[Metric] = []
        self._logs: list[dict[str, Any]] = []

    async def initialize(self, config: ObservabilityConfig) -> bool:
        """Observabilityを初期化"""
        self._config = config
        return True

    # Tracing
    async def start_trace(
        self,
        name: str,
        metadata: dict[str, Any] | None = None,
    ) -> Trace:
        """トレースを開始"""
        trace_id = str(uuid.uuid4())
        
        trace = Trace(
            trace_id=trace_id,
            name=name,
            start_time=datetime.now(),
            status=TraceStatus.RUNNING,
            metadata=metadata or {},
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
        
        # トレースにSpanを追加
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
        }
        
        self._logs.append(log_entry)
        
        # 設定に応じてコンソール出力
        if self._config and self._config.enable_logging:
            print(f"[{level.upper()}] {message}")
        
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
        
        # 新しい順にソート
        traces.sort(key=lambda t: t.start_time, reverse=True)
        
        return traces[:limit]


def create_strands_observability() -> StrandsObservabilityAdapter:
    """ファクトリ関数"""
    return StrandsObservabilityAdapter()

