"""Policy Service Router - ガバナンス比較

AgentCore Policy (Preview) vs 自己実装 の比較:

AgentCore Policy:
- Cedar統合
- 自然言語ポリシー定義
- リアルタイムポリシーチェック
- MCP Policy Authoring Server

LangChain:
- 自己実装が必要
- ミドルウェアでの実装
"""

from .base import create_service_router

router = create_service_router(
    service_name="Policy",
    service_description="エージェント動作のガバナンス制御。セキュリティポリシー・コンプライアンス管理。",
    strands_features=[
        "cedar_integration",
        "natural_language_policy",
        "realtime_policy_check",
        "mcp_policy_authoring",
        "gateway_integration",
        "independent_validation_layer",
        "enterprise_governance",
    ],
    langchain_features=[
        "self_implementation_required",
        "middleware_approach",
        "content_moderation_middleware",
        "custom_guardrails",
    ],
)
