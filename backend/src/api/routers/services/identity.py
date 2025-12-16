"""Identity Service Router - アイデンティティ管理"""

from .base import create_service_router

router = create_service_router(
    service_name="Identity",
    service_description="エージェントと人間のアイデンティティ管理。認証・認可の統合管理。",
)
