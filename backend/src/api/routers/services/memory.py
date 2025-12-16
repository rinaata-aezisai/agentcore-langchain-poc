"""Memory Service Router - メモリ管理"""

from .base import create_service_router

router = create_service_router(
    service_name="Memory",
    service_description="短期・長期メモリのマネージドサービス。会話履歴やコンテキストの保持・検索。",
)
