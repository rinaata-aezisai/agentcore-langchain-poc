"""Browser Service Router - クラウドブラウザ環境"""

from .base import create_service_router

router = create_service_router(
    service_name="Browser",
    service_description="クラウドベースのブラウザ自動化環境。Webスクレイピングや自動操作。",
)
