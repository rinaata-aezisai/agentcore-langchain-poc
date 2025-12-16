"""Strands Gateway Adapter

AgentCore Gateway サービスの実装。
API管理、ルーティング、レート制限。
"""

import asyncio
import time
from collections import defaultdict
from typing import Any

import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent.parent.parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_path))

from application.ports.gateway_port import (
    GatewayPort,
    GatewayConfig,
    RouteConfig,
    RouteMethod,
    GatewayResponse,
    RateLimitStrategy,
)


class StrandsGatewayAdapter(GatewayPort):
    """Strands Agents Gateway アダプター
    
    AgentCore Gatewayの機能:
    - APIルート管理
    - レート制限
    - リクエストログ
    - メトリクス収集
    """

    def __init__(self):
        self._config: GatewayConfig | None = None
        self._routes: dict[str, RouteConfig] = {}  # key: f"{method}:{path}"
        self._rate_limits: dict[str, list[float]] = defaultdict(list)  # client_id -> timestamps
        self._metrics: dict[str, int] = defaultdict(int)
        self._handlers: dict[str, Any] = {}

    async def initialize(self, config: GatewayConfig) -> bool:
        """Gatewayを初期化"""
        self._config = config
        return True

    async def register_route(self, route: RouteConfig) -> bool:
        """ルートを登録"""
        key = f"{route.method.value}:{route.path}"
        self._routes[key] = route
        return True

    async def unregister_route(self, path: str, method: RouteMethod) -> bool:
        """ルートを解除"""
        key = f"{method.value}:{path}"
        if key in self._routes:
            del self._routes[key]
            return True
        return False

    async def list_routes(self) -> list[RouteConfig]:
        """ルート一覧を取得"""
        return list(self._routes.values())

    async def invoke(
        self,
        path: str,
        method: RouteMethod,
        payload: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> GatewayResponse:
        """エンドポイントを呼び出し"""
        start_time = time.time()
        key = f"{method.value}:{path}"
        
        # ルート存在チェック
        if key not in self._routes:
            return GatewayResponse(
                status_code=404,
                body={"error": "Route not found"},
                latency_ms=int((time.time() - start_time) * 1000),
            )
        
        route = self._routes[key]
        
        # レート制限チェック
        client_id = headers.get("X-Client-ID", "anonymous") if headers else "anonymous"
        if not await self._check_rate_limit(client_id, route.rate_limit):
            self._metrics["rate_limited"] += 1
            return GatewayResponse(
                status_code=429,
                body={"error": "Rate limit exceeded"},
                headers={"Retry-After": "60"},
                latency_ms=int((time.time() - start_time) * 1000),
            )
        
        # 認証チェック（簡易実装）
        if route.auth_required:
            auth_header = headers.get("Authorization") if headers else None
            if not auth_header:
                self._metrics["auth_failed"] += 1
                return GatewayResponse(
                    status_code=401,
                    body={"error": "Authentication required"},
                    latency_ms=int((time.time() - start_time) * 1000),
                )
        
        # ハンドラー呼び出し（モック実装）
        try:
            # 実際の実装ではハンドラーを呼び出す
            response_body = {
                "success": True,
                "route": path,
                "method": method.value,
                "payload": payload,
            }
            
            self._metrics["success"] += 1
            latency = int((time.time() - start_time) * 1000)
            
            return GatewayResponse(
                status_code=200,
                body=response_body,
                headers={"X-Request-ID": f"req-{int(time.time())}"},
                latency_ms=latency,
            )
        except Exception as e:
            self._metrics["errors"] += 1
            return GatewayResponse(
                status_code=500,
                body={"error": str(e)},
                latency_ms=int((time.time() - start_time) * 1000),
            )

    async def get_rate_limit_status(self, client_id: str | None = None) -> dict[str, Any]:
        """レート制限状態を取得"""
        if client_id:
            requests = self._rate_limits.get(client_id, [])
            # 過去1分のリクエストをカウント
            now = time.time()
            recent = [t for t in requests if now - t < 60]
            return {
                "client_id": client_id,
                "requests_last_minute": len(recent),
                "limit": self._config.global_rate_limit if self._config else 1000,
            }
        
        return {
            "global_limit": self._config.global_rate_limit if self._config else 1000,
            "strategy": self._config.rate_limit_strategy.value if self._config else "token_bucket",
            "active_clients": len(self._rate_limits),
        }

    async def get_metrics(self) -> dict[str, Any]:
        """メトリクスを取得"""
        return {
            "total_requests": sum(self._metrics.values()),
            "success": self._metrics["success"],
            "errors": self._metrics["errors"],
            "rate_limited": self._metrics["rate_limited"],
            "auth_failed": self._metrics["auth_failed"],
            "registered_routes": len(self._routes),
        }

    async def _check_rate_limit(
        self,
        client_id: str,
        route_limit: int | None = None,
    ) -> bool:
        """レート制限をチェック"""
        now = time.time()
        limit = route_limit or (self._config.global_rate_limit if self._config else 1000)
        
        # 過去1分のリクエストを取得
        requests = self._rate_limits[client_id]
        requests = [t for t in requests if now - t < 60]
        self._rate_limits[client_id] = requests
        
        if len(requests) >= limit:
            return False
        
        requests.append(now)
        return True


def create_strands_gateway() -> StrandsGatewayAdapter:
    """ファクトリ関数"""
    return StrandsGatewayAdapter()

