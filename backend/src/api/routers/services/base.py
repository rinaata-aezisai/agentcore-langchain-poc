"""Base service router implementation"""

import time
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel


class ServiceExecuteRequest(BaseModel):
    """サービス実行リクエスト"""

    instruction: str
    agent_type: str  # "strands" or "langchain"
    tools: list[dict[str, Any]] | None = None


class ServiceExecuteResponse(BaseModel):
    """サービス実行レスポンス"""

    response_id: str
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    latency_ms: int
    metadata: dict[str, Any] | None = None


def create_service_router(service_name: str, service_description: str) -> APIRouter:
    """サービス用ルーターを作成"""

    router = APIRouter()

    @router.post("/execute", response_model=ServiceExecuteResponse)
    async def execute(request: ServiceExecuteRequest) -> ServiceExecuteResponse:
        """サービスを実行"""
        import ulid

        start_time = time.time()

        try:
            # アダプターを取得
            if request.agent_type == "strands":
                from strands_poc.adapter import create_strands_adapter

                adapter = create_strands_adapter()
            elif request.agent_type == "langchain":
                from langchain_poc.adapter import create_langchain_adapter

                adapter = create_langchain_adapter()
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unknown agent type: {request.agent_type}",
                )

            # 実行
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
                    **(response.metadata or {}),
                },
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

    @router.get("/info")
    async def get_info():
        """サービス情報を取得"""
        return {
            "service": service_name,
            "description": service_description,
            "supported_agents": ["strands", "langchain"],
        }

    return router

