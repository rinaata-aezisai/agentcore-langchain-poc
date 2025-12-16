"""Observability Service Router - トレース・監視"""

from .base import create_service_router

router = create_service_router(
    service_name="Observability",
    service_description="エージェント実行のトレース・監視・ロギング。パフォーマンス分析。",
)
