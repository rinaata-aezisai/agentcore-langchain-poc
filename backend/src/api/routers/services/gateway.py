"""Gateway Service Router

API GatewayサービスAPIエンドポイント。
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any
from enum import Enum

router = APIRouter(prefix="/gateway", tags=["Gateway"])


class AgentType(str, Enum):
    STRANDS = "strands"
    LANGCHAIN = "langchain"


class RouteMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


class GatewayConfigRequest(BaseModel):
    agent_type: AgentType = AgentType.STRANDS
    base_url: str = ""
    global_rate_limit: int = 1000


class RegisterRouteRequest(BaseModel):
    path: str
    method: RouteMethod
    handler: str
    rate_limit: int | None = None
    auth_required: bool = True


class InvokeRequest(BaseModel):
    path: str
    method: RouteMethod
    payload: dict[str, Any] | None = None
    headers: dict[str, str] | None = None


@router.post("/initialize")
async def initialize_gateway(config: GatewayConfigRequest):
    """Gatewayを初期化"""
    return {
        "initialized": True,
        "agent_type": config.agent_type.value,
        "base_url": config.base_url,
    }


@router.post("/routes")
async def register_route(request: RegisterRouteRequest, agent_type: AgentType = AgentType.STRANDS):
    """ルートを登録"""
    return {
        "path": request.path,
        "method": request.method.value,
        "registered": True,
        "agent_type": agent_type.value,
    }


@router.delete("/routes")
async def unregister_route(path: str, method: RouteMethod, agent_type: AgentType = AgentType.STRANDS):
    """ルートを解除"""
    return {
        "path": path,
        "method": method.value,
        "unregistered": True,
        "agent_type": agent_type.value,
    }


@router.get("/routes")
async def list_routes(agent_type: AgentType = AgentType.STRANDS):
    """ルート一覧を取得"""
    return {
        "routes": [],
        "agent_type": agent_type.value,
    }


@router.post("/invoke")
async def invoke_route(request: InvokeRequest, agent_type: AgentType = AgentType.STRANDS):
    """エンドポイントを呼び出し"""
    return {
        "status_code": 200,
        "body": {"success": True},
        "agent_type": agent_type.value,
    }


@router.get("/rate-limit")
async def get_rate_limit_status(client_id: str | None = None, agent_type: AgentType = AgentType.STRANDS):
    """レート制限状態を取得"""
    return {
        "client_id": client_id,
        "requests_last_minute": 0,
        "limit": 1000,
        "agent_type": agent_type.value,
    }


@router.get("/metrics")
async def get_gateway_metrics(agent_type: AgentType = AgentType.STRANDS):
    """メトリクスを取得"""
    return {
        "total_requests": 0,
        "success": 0,
        "errors": 0,
        "agent_type": agent_type.value,
    }

