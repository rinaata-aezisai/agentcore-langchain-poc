"""Browser Service Router - ブラウザ環境比較

AgentCore Browser vs サードパーティ の比較:

AgentCore Browser:
- クラウドブラウザ
- VPC対応
- 自動化サポート
- Playwright統合

LangChain:
- サードパーティ統合必要
- Playwright/Selenium
"""

from .base import create_service_router

router = create_service_router(
    service_name="Browser",
    service_description="クラウドベースのブラウザ自動化環境。Webスクレイピングや自動操作。",
    strands_features=[
        "cloud_browser",
        "vpc_support",
        "automation_support",
        "playwright_integration",
        "browseruse_support",
        "managed_service",
    ],
    langchain_features=[
        "third_party_required",
        "playwright_integration",
        "selenium_support",
        "custom_browser_tools",
    ],
)
