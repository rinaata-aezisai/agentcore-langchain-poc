"""Gateway Service Router - ツール変換比較

AgentCore Gateway vs LangChain Tool Integration の比較:

AgentCore Gateway:
- MCPプロトコル完全対応
- API/Lambdaの自動変換
- 認証情報管理
- Policyとの統合

LangChain:
- @tool デコレータ
- ToolNode (LangGraph)
- コミュニティツール
- MCPサポート（コミュニティ）
"""

from .base import create_service_router

router = create_service_router(
    service_name="Gateway",
    service_description="MCPプロトコル対応のツール変換ゲートウェイ。外部サービス連携を簡素化。",
    strands_features=[
        "mcp_protocol_native",
        "api_lambda_conversion",
        "credential_management",
        "policy_integration",
        "openapi_support",
        "smithy_model_support",
    ],
    langchain_features=[
        "tool_decorator",
        "langgraph_toolnode",
        "community_tools",
        "mcp_community_support",
        "custom_tool_creation",
        "async_tool_support",
    ],
)
