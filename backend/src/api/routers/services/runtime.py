"""Runtime Service Router

エージェント実行環境APIエンドポイント。
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any
from enum import Enum

router = APIRouter(prefix="/runtime", tags=["Runtime"])


class AgentType(str, Enum):
    STRANDS = "strands"
    LANGCHAIN = "langchain"


class RuntimeConfigRequest(BaseModel):
    agent_type: AgentType = AgentType.STRANDS
    model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    region: str = "us-east-1"
    max_tokens: int = 4096
    temperature: float = 0.7
    system_prompt: str | None = None


class ExecuteRequest(BaseModel):
    instruction: str
    context: list[dict[str, Any]] | None = None


class ExecuteWithToolsRequest(BaseModel):
    instruction: str
    tools: list[dict[str, Any]]
    context: list[dict[str, Any]] | None = None


@router.post("/initialize")
async def initialize_runtime(config: RuntimeConfigRequest):
    """ランタイムを初期化"""
    try:
        # Agent typeに応じて適切なアダプターを選択
        if config.agent_type == AgentType.STRANDS:
            from poc.strands_agents.src.services.runtime import create_strands_runtime
            adapter = create_strands_runtime()
        else:
            from poc.langchain.src.services.runtime import create_langchain_runtime
            adapter = create_langchain_runtime()
        
        from application.ports.runtime_port import RuntimeConfig
        runtime_config = RuntimeConfig(
            model_id=config.model_id,
            region=config.region,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            system_prompt=config.system_prompt,
        )
        
        status = await adapter.initialize(runtime_config)
        
        return {
            "status": status.value,
            "agent_type": config.agent_type.value,
            "model_id": config.model_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute")
async def execute(request: ExecuteRequest, agent_type: AgentType = AgentType.STRANDS):
    """同期実行"""
    try:
        # 簡易実装: 実際にはDIを使用
        return {
            "content": f"Mock response for: {request.instruction}",
            "agent_type": agent_type.value,
            "status": "ready",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute-stream")
async def execute_stream(request: ExecuteRequest, agent_type: AgentType = AgentType.STRANDS):
    """ストリーミング実行（SSE）"""
    # 本番ではStreamingResponseを使用
    return {
        "message": "Streaming endpoint - use SSE client",
        "agent_type": agent_type.value,
    }


@router.post("/execute-with-tools")
async def execute_with_tools(request: ExecuteWithToolsRequest, agent_type: AgentType = AgentType.STRANDS):
    """ツール付き実行"""
    try:
        return {
            "content": f"Mock tool response for: {request.instruction}",
            "agent_type": agent_type.value,
            "tools_count": len(request.tools),
            "status": "ready",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_status(agent_type: AgentType = AgentType.STRANDS):
    """ステータス取得"""
    return {
        "status": "ready",
        "agent_type": agent_type.value,
    }


@router.post("/pause")
async def pause_runtime(agent_type: AgentType = AgentType.STRANDS):
    """一時停止"""
    return {"paused": True, "agent_type": agent_type.value}


@router.post("/resume")
async def resume_runtime(agent_type: AgentType = AgentType.STRANDS):
    """再開"""
    return {"resumed": True, "agent_type": agent_type.value}


@router.post("/terminate")
async def terminate_runtime(agent_type: AgentType = AgentType.STRANDS):
    """終了"""
    return {"terminated": True, "agent_type": agent_type.value}

