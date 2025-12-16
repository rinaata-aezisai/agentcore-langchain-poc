"""Runtime Service Router - サーバーレス実行環境"""

from .base import create_service_router

router = create_service_router(
    service_name="Runtime",
    service_description="AIエージェントとツールをホストするサーバーレス実行環境。双方向ストリーミング対応。",
)
