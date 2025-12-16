"""Observability Service Router - 監視比較

AgentCore Observability vs LangFuse/LangSmith の比較:

AgentCore Observability:
- 統合トレース
- CloudWatch統合
- Evaluationsとの連携
- OpenTelemetry互換

LangFuse/LangSmith:
- 詳細トレース
- プロンプト管理
- A/Bテスト
- コスト分析
"""

from .base import create_service_router

router = create_service_router(
    service_name="Observability",
    service_description="エージェント実行のトレース・監視・ロギング。パフォーマンス分析。",
    strands_features=[
        "integrated_tracing",
        "cloudwatch_integration",
        "evaluations_integration",
        "opentelemetry_compatible",
        "unified_dashboard",
        "aws_native_monitoring",
    ],
    langchain_features=[
        "langfuse_integration",
        "langsmith_integration",
        "detailed_tracing",
        "prompt_management",
        "ab_testing",
        "unified_cost_tracking",
        "multi_turn_evaluations",
    ],
)
