"""Agents Router - エージェント情報・比較API"""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.dependencies import SettingsDep

router = APIRouter()


class AgentInfoResponse(BaseModel):
    """エージェント情報レスポンス"""

    agent_type: str = Field(..., description="エージェントタイプ (strands/langchain)")
    model_id: str = Field(..., description="使用モデルID")
    provider: str = Field(..., description="プロバイダー")
    capabilities: list[str] = Field(..., description="対応機能")


class AgentComparisonResponse(BaseModel):
    """エージェント比較レスポンス"""

    strands: dict[str, Any]
    langchain: dict[str, Any]


@router.get("/info", response_model=AgentInfoResponse)
async def get_agent_info(settings: SettingsDep):
    """現在のエージェント情報を取得"""
    capabilities = ["chat", "tools", "streaming"]

    if settings.agent_type == "langchain":
        capabilities.append("langgraph_workflow")
        if settings.langfuse_enabled:
            capabilities.append("langfuse_observability")
        provider = "langchain"
    else:
        capabilities.append("bedrock_native")
        provider = "strands-agents"

    return AgentInfoResponse(
        agent_type=settings.agent_type,
        model_id=settings.bedrock_model_id,
        provider=provider,
        capabilities=capabilities,
    )


@router.get("/comparison", response_model=AgentComparisonResponse)
async def get_agent_comparison():
    """Strands vs LangChainの比較情報を取得"""
    return AgentComparisonResponse(
        strands={
            "name": "Strands Agents (AWS Bedrock AgentCore)",
            "strengths": [
                "AWS ネイティブ統合",
                "シンプルなAPI",
                "Bedrock完全対応",
                "低オーバーヘッド",
            ],
            "features": {
                "tool_calling": True,
                "streaming": True,
                "memory": True,
                "multi_agent": False,
                "workflow": False,
            },
        },
        langchain={
            "name": "LangChain + LangGraph",
            "strengths": [
                "成熟したエコシステム",
                "高度なワークフロー (LangGraph)",
                "LangFuse/LangSmith統合",
                "マルチエージェント対応",
            ],
            "features": {
                "tool_calling": True,
                "streaming": True,
                "memory": True,
                "multi_agent": True,
                "workflow": True,
            },
        },
    )


@router.get("/tools")
async def list_available_tools(settings: SettingsDep):
    """利用可能なツール一覧を取得"""
    tools = [
        {
            "name": "get_current_weather",
            "description": "指定された場所の現在の天気を取得",
            "available": True,
        },
        {
            "name": "search_documents",
            "description": "ドキュメントを検索",
            "available": True,
        },
        {
            "name": "calculate",
            "description": "数式を計算",
            "available": True,
        },
        {
            "name": "create_task",
            "description": "タスクを作成",
            "available": True,
        },
        {
            "name": "fetch_url",
            "description": "URLからコンテンツを取得",
            "available": True,
        },
    ]

    return {
        "agent_type": settings.agent_type,
        "tools": tools,
        "total_count": len(tools),
    }
