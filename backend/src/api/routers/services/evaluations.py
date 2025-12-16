"""Evaluations Service Router - 品質評価比較

AgentCore Evaluations (Preview) vs LangSmith Evaluations の比較:

AgentCore Evaluations:
- 13種類のビルトイン評価器
- Correctness, Helpfulness, Faithfulness等
- CloudWatch統合
- カスタム評価器

LangSmith:
- Multi-turn Evaluations
- カスタム評価
- オンライン評価
"""

from .base import create_service_router

router = create_service_router(
    service_name="Evaluations",
    service_description="エージェント出力の品質評価システム。正確性・関連性・安全性の自動評価。",
    strands_features=[
        "13_builtin_evaluators",
        "correctness_evaluation",
        "helpfulness_evaluation",
        "faithfulness_evaluation",
        "harmfulness_detection",
        "stereotyping_detection",
        "tool_selection_accuracy",
        "context_relevance",
        "cloudwatch_alerts",
        "custom_evaluators",
    ],
    langchain_features=[
        "langsmith_evaluations",
        "multi_turn_evaluations",
        "custom_evaluators",
        "online_evaluation",
        "langfuse_evaluations",
        "custom_metrics",
    ],
)
