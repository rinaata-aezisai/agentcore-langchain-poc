"""Base service router implementation - 本格実装

AgentCore vs LangChain の各サービス機能を比較検証するための
ベースルーター実装。

各サービスの特徴:
- Strands Agents: AgentCore Memory, Tool Decorator, Episodic Memory
- LangChain: LangGraph StateGraph, Checkpointing, ToolNode
"""

import time
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
import ulid


class ServiceExecuteRequest(BaseModel):
    """サービス実行リクエスト"""

    instruction: str
    agent_type: str  # "strands" or "langchain"
    tools: list[dict[str, Any]] | None = None
    use_memory: bool = True  # メモリ機能を使用するか
    session_id: str | None = None  # セッションID（メモリ継続用）


class ServiceExecuteResponse(BaseModel):
    """サービス実行レスポンス"""

    response_id: str
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    latency_ms: int
    metadata: dict[str, Any] | None = None
    framework_features: list[str] | None = None


class ServiceComparisonResult(BaseModel):
    """フレームワーク比較結果"""

    strands_result: ServiceExecuteResponse | None = None
    langchain_result: ServiceExecuteResponse | None = None
    comparison: dict[str, Any] | None = None


# アダプターインスタンスのキャッシュ（セッション管理用）
_strands_adapters: dict[str, Any] = {}
_langchain_adapters: dict[str, Any] = {}


def get_strands_adapter(session_id: str | None = None):
    """Strands Agentアダプターを取得（セッション対応）"""
    from strands_poc.adapter import create_strands_adapter

    if session_id and session_id in _strands_adapters:
        return _strands_adapters[session_id]

    adapter = create_strands_adapter()
    if session_id:
        _strands_adapters[session_id] = adapter
    return adapter


def get_langchain_adapter(session_id: str | None = None):
    """LangChainアダプターを取得（セッション対応）"""
    from langchain_poc.adapter import create_langchain_adapter

    if session_id and session_id in _langchain_adapters:
        return _langchain_adapters[session_id]

    adapter = create_langchain_adapter()
    if session_id:
        _langchain_adapters[session_id] = adapter
    return adapter


def create_service_router(
    service_name: str,
    service_description: str,
    strands_features: list[str] | None = None,
    langchain_features: list[str] | None = None,
) -> APIRouter:
    """サービス用ルーターを作成

    各サービスごとに特化した比較検証を提供。
    """
    router = APIRouter()

    @router.post("/execute", response_model=ServiceExecuteResponse)
    async def execute(request: ServiceExecuteRequest) -> ServiceExecuteResponse:
        """サービスを実行

        指定されたフレームワーク（Strands/LangChain）で実行し、
        フレームワーク固有の機能を活用した結果を返す。
        """
        start_time = time.time()

        try:
            if request.agent_type == "strands":
                adapter = get_strands_adapter(request.session_id)
                framework_features = strands_features or [
                    "bedrock_native_integration",
                    "conversation_memory",
                    "episodic_memory",
                    "tool_decorator",
                ]
            elif request.agent_type == "langchain":
                adapter = get_langchain_adapter(request.session_id)
                framework_features = langchain_features or [
                    "langgraph_state_management",
                    "checkpointing",
                    "tool_node_automation",
                    "multi_provider_support",
                ]
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unknown agent type: {request.agent_type}",
                )

            # ツール付きか通常実行か判定
            if request.tools:
                response = await adapter.execute_with_tools(
                    context=[],
                    instruction=request.instruction,
                    tools=request.tools,
                )
            else:
                response = await adapter.execute(
                    context=[],
                    instruction=request.instruction,
                )

            latency_ms = int((time.time() - start_time) * 1000)

            return ServiceExecuteResponse(
                response_id=str(ulid.new()),
                content=response.content,
                tool_calls=response.tool_calls,
                latency_ms=latency_ms,
                metadata={
                    "service": service_name,
                    "agent_type": request.agent_type,
                    "session_id": request.session_id,
                    "memory_enabled": request.use_memory,
                    **(response.metadata or {}),
                },
                framework_features=framework_features,
            )

        except ImportError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Adapter not available: {e}",
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Execution failed: {e}",
            ) from e

    @router.post("/execute-with-tools", response_model=ServiceExecuteResponse)
    async def execute_with_tools(request: ServiceExecuteRequest) -> ServiceExecuteResponse:
        """ツール付きでサービスを実行

        各フレームワークのツール呼び出し機能を活用:
        - Strands: @tool decorator + automatic tool loop
        - LangChain: LangGraph ToolNode + conditional edges
        """
        start_time = time.time()

        try:
            if request.agent_type == "strands":
                adapter = get_strands_adapter(request.session_id)
            elif request.agent_type == "langchain":
                adapter = get_langchain_adapter(request.session_id)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unknown agent type: {request.agent_type}",
                )

            response = await adapter.execute_with_tools(
                context=[],
                instruction=request.instruction,
                tools=request.tools,
            )

            latency_ms = int((time.time() - start_time) * 1000)

            return ServiceExecuteResponse(
                response_id=str(ulid.new()),
                content=response.content,
                tool_calls=response.tool_calls,
                latency_ms=latency_ms,
                metadata={
                    "service": service_name,
                    "agent_type": request.agent_type,
                    "execution_type": "with_tools",
                    **(response.metadata or {}),
                },
            )

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Execution failed: {e}",
            ) from e

    @router.post("/compare", response_model=ServiceComparisonResult)
    async def compare_frameworks(request: ServiceExecuteRequest) -> ServiceComparisonResult:
        """両フレームワークで実行して比較

        同じ指示を Strands Agents と LangChain で実行し、
        結果を比較可能な形式で返す。
        """
        strands_result = None
        langchain_result = None

        # Strands Agents で実行
        try:
            strands_adapter = get_strands_adapter()
            start_time = time.time()

            if request.tools:
                strands_response = await strands_adapter.execute_with_tools(
                    context=[], instruction=request.instruction, tools=request.tools
                )
            else:
                strands_response = await strands_adapter.execute(
                    context=[], instruction=request.instruction
                )

            strands_latency = int((time.time() - start_time) * 1000)
            strands_result = ServiceExecuteResponse(
                response_id=str(ulid.new()),
                content=strands_response.content,
                tool_calls=strands_response.tool_calls,
                latency_ms=strands_latency,
                metadata=strands_response.metadata,
                framework_features=strands_features,
            )
        except Exception as e:
            strands_result = ServiceExecuteResponse(
                response_id=str(ulid.new()),
                content=f"Error: {e}",
                latency_ms=0,
                metadata={"error": str(e)},
            )

        # LangChain で実行
        try:
            langchain_adapter = get_langchain_adapter()
            start_time = time.time()

            if request.tools:
                langchain_response = await langchain_adapter.execute_with_tools(
                    context=[], instruction=request.instruction, tools=request.tools
                )
            else:
                langchain_response = await langchain_adapter.execute(
                    context=[], instruction=request.instruction
                )

            langchain_latency = int((time.time() - start_time) * 1000)
            langchain_result = ServiceExecuteResponse(
                response_id=str(ulid.new()),
                content=langchain_response.content,
                tool_calls=langchain_response.tool_calls,
                latency_ms=langchain_latency,
                metadata=langchain_response.metadata,
                framework_features=langchain_features,
            )
        except Exception as e:
            langchain_result = ServiceExecuteResponse(
                response_id=str(ulid.new()),
                content=f"Error: {e}",
                latency_ms=0,
                metadata={"error": str(e)},
            )

        # 比較分析
        comparison = {
            "latency_diff_ms": (
                strands_result.latency_ms - langchain_result.latency_ms
                if strands_result and langchain_result
                else None
            ),
            "faster_framework": (
                "strands"
                if strands_result
                and langchain_result
                and strands_result.latency_ms < langchain_result.latency_ms
                else "langchain"
            ),
            "strands_tool_calls": len(strands_result.tool_calls) if strands_result and strands_result.tool_calls else 0,
            "langchain_tool_calls": len(langchain_result.tool_calls) if langchain_result and langchain_result.tool_calls else 0,
            "service": service_name,
        }

        return ServiceComparisonResult(
            strands_result=strands_result,
            langchain_result=langchain_result,
            comparison=comparison,
        )

    @router.get("/info")
    async def get_info():
        """サービス情報を取得"""
        return {
            "service": service_name,
            "description": service_description,
            "supported_agents": ["strands", "langchain"],
            "strands_features": strands_features or [],
            "langchain_features": langchain_features or [],
            "comparison_available": True,
        }

    @router.get("/memory-stats/{session_id}")
    async def get_memory_stats(session_id: str, agent_type: str = "strands"):
        """セッションのメモリ統計を取得"""
        try:
            if agent_type == "strands" and session_id in _strands_adapters:
                adapter = _strands_adapters[session_id]
                return {
                    "session_id": session_id,
                    "agent_type": "strands",
                    "stats": adapter.get_memory_stats(),
                }
            elif agent_type == "langchain" and session_id in _langchain_adapters:
                adapter = _langchain_adapters[session_id]
                return {
                    "session_id": session_id,
                    "agent_type": "langchain",
                    "stats": adapter.get_memory_stats(),
                    "execution_stats": adapter.get_execution_stats(),
                }
            else:
                return {
                    "session_id": session_id,
                    "agent_type": agent_type,
                    "error": "Session not found",
                }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
            ) from e

    @router.delete("/session/{session_id}")
    async def clear_session(session_id: str):
        """セッションをクリア"""
        cleared = []
        if session_id in _strands_adapters:
            _strands_adapters[session_id].clear_memory()
            del _strands_adapters[session_id]
            cleared.append("strands")
        if session_id in _langchain_adapters:
            _langchain_adapters[session_id].clear_memory()
            del _langchain_adapters[session_id]
            cleared.append("langchain")

        return {
            "session_id": session_id,
            "cleared": cleared,
            "success": len(cleared) > 0,
        }

    return router
