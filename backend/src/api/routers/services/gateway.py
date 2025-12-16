"""Gateway Service Router - MCP対応ツール変換"""

from .base import create_service_router

router = create_service_router(
    service_name="Gateway",
    service_description="MCPプロトコル対応のツール変換ゲートウェイ。外部サービス連携を簡素化。",
)
