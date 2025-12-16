"""Code Interpreter Service Router - コード実行サンドボックス"""

from .base import create_service_router

router = create_service_router(
    service_name="Code Interpreter",
    service_description="セキュアなサンドボックス環境でのコード実行。多言語対応のインタプリタ。",
)
