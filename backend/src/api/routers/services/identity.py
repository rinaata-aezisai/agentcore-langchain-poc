"""Identity Service Router - アイデンティティ管理比較

AgentCore Identity vs 自己実装 の比較:

AgentCore Identity:
- IdP統合（Cognito, Okta, Azure AD）
- エージェント用認証
- アクセス制御
- ワークロードID

LangChain:
- 自己実装が必要
- サードパーティ統合
"""

from .base import create_service_router

router = create_service_router(
    service_name="Identity",
    service_description="エージェントと人間のアイデンティティ管理。認証・認可の統合管理。",
    strands_features=[
        "idp_integration",
        "cognito_integration",
        "okta_integration",
        "azure_ad_integration",
        "agent_authentication",
        "workload_identity",
        "access_control",
    ],
    langchain_features=[
        "self_implementation_required",
        "third_party_integration",
        "custom_auth_middleware",
        "api_key_management",
    ],
)
