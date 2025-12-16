"""Code Interpreter Service Router - コード実行比較

AgentCore Code Interpreter vs LangChain/E2B の比較:

AgentCore Code Interpreter:
- 隔離サンドボックス
- 最大8時間実行
- VPC統合
- 多言語対応

LangChain/Deep Agents:
- E2B Sandbox統合
- リモートサンドボックス
- カスタム実行環境
"""

from .base import create_service_router

router = create_service_router(
    service_name="Code Interpreter",
    service_description="セキュアなサンドボックス環境でのコード実行。多言語対応のインタプリタ。",
    strands_features=[
        "isolated_sandbox",
        "8_hour_execution",
        "vpc_integration",
        "multi_language_support",
        "python_support",
        "javascript_support",
        "typescript_support",
        "aws_managed_security",
    ],
    langchain_features=[
        "e2b_sandbox_integration",
        "remote_sandbox",
        "custom_execution_environment",
        "deepagents_sandboxes",
        "reproducible_execution",
    ],
)
