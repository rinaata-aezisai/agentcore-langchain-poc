"""Runtime Service Router - 実行環境比較

AgentCore Runtime vs LangGraph Platform の比較:

AgentCore Runtime:
- サーバーレス実行環境
- 双方向ストリーミング（音声エージェント対応）
- 自動スケーリング
- セッション分離

LangGraph Platform:
- LangGraph Cloud
- カスタムデプロイオプション
- セルフホスティング可能
"""

from .base import create_service_router

router = create_service_router(
    service_name="Runtime",
    service_description="AIエージェントとツールをホストするサーバーレス実行環境。双方向ストリーミング対応。",
    strands_features=[
        "bedrock_native_integration",
        "serverless_execution",
        "bidirectional_streaming",
        "auto_scaling",
        "session_isolation",
        "aws_managed",
    ],
    langchain_features=[
        "langgraph_cloud",
        "custom_deployment",
        "self_hosting_option",
        "multi_provider",
        "flexible_hosting",
    ],
)
