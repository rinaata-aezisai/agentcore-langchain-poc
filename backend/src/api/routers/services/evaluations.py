"""Evaluations Service Router - 品質評価システム"""

from .base import create_service_router

router = create_service_router(
    service_name="Evaluations",
    service_description="エージェント出力の品質評価システム。正確性・関連性・安全性の自動評価。",
)
