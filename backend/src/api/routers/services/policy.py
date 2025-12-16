"""Policy Service Router - ガバナンス制御"""

from .base import create_service_router

router = create_service_router(
    service_name="Policy",
    service_description="エージェント動作のガバナンス制御。セキュリティポリシー・コンプライアンス管理。",
)
