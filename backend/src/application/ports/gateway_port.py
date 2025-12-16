"""Gateway Port - API Gateway Service Interface

AgentCore Gateway / LangServe に対応。
API管理、ルーティング、レート制限。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class RouteMethod(str, Enum):
    """HTTPメソッド"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class RateLimitStrategy(str, Enum):
    """レート制限戦略"""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"


@dataclass
class RouteConfig:
    """ルート設定"""
    path: str
    method: RouteMethod
    handler: str
    rate_limit: int | None = None  # requests per minute
    timeout_ms: int = 30000
    auth_required: bool = True
    cors_enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GatewayConfig:
    """Gateway設定"""
    base_url: str = ""
    rate_limit_strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET
    global_rate_limit: int = 1000  # requests per minute
    enable_logging: bool = True
    enable_metrics: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GatewayResponse:
    """Gatewayレスポンス"""
    status_code: int
    body: Any
    headers: dict[str, str] = field(default_factory=dict)
    latency_ms: int = 0


class GatewayPort(ABC):
    """Gateway Port - API Gateway

    Strands Agents: AgentCore Gateway
    LangChain: LangServe
    """

    @abstractmethod
    async def initialize(self, config: GatewayConfig) -> bool:
        """Gatewayを初期化"""
        ...

    @abstractmethod
    async def register_route(self, route: RouteConfig) -> bool:
        """ルートを登録"""
        ...

    @abstractmethod
    async def unregister_route(self, path: str, method: RouteMethod) -> bool:
        """ルートを解除"""
        ...

    @abstractmethod
    async def list_routes(self) -> list[RouteConfig]:
        """ルート一覧を取得"""
        ...

    @abstractmethod
    async def invoke(
        self,
        path: str,
        method: RouteMethod,
        payload: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> GatewayResponse:
        """エンドポイントを呼び出し"""
        ...

    @abstractmethod
    async def get_rate_limit_status(self, client_id: str | None = None) -> dict[str, Any]:
        """レート制限状態を取得"""
        ...

    @abstractmethod
    async def get_metrics(self) -> dict[str, Any]:
        """メトリクスを取得"""
        ...

