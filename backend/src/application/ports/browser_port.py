"""Browser Port - Browser Automation Service Interface

AgentCore Browser / Playwright に対応。
ブラウザ操作、スクレイピング、Web自動化。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class BrowserType(str, Enum):
    """ブラウザタイプ"""
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


class ActionType(str, Enum):
    """アクションタイプ"""
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"
    SCREENSHOT = "screenshot"
    EXTRACT = "extract"
    WAIT = "wait"


@dataclass
class BrowserConfig:
    """ブラウザ設定"""
    browser_type: BrowserType = BrowserType.CHROMIUM
    headless: bool = True
    viewport_width: int = 1920
    viewport_height: int = 1080
    timeout_ms: int = 30000
    user_agent: str | None = None
    proxy: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BrowserAction:
    """ブラウザアクション"""
    action_type: ActionType
    selector: str | None = None
    value: str | None = None
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class PageState:
    """ページ状態"""
    url: str
    title: str
    html: str | None = None
    text_content: str | None = None
    screenshot_base64: str | None = None
    cookies: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BrowserActionResult:
    """アクション結果"""
    success: bool
    action: BrowserAction
    page_state: PageState | None = None
    extracted_data: Any | None = None
    error: str | None = None
    execution_time_ms: int = 0


class BrowserPort(ABC):
    """Browser Port - ブラウザ操作

    Strands Agents: AgentCore Browser
    LangChain: Playwright / Browser Use
    """

    @abstractmethod
    async def initialize(self, config: BrowserConfig) -> bool:
        """ブラウザを初期化"""
        ...

    @abstractmethod
    async def navigate(self, url: str) -> PageState:
        """URLに移動"""
        ...

    @abstractmethod
    async def execute_action(self, action: BrowserAction) -> BrowserActionResult:
        """アクションを実行"""
        ...

    @abstractmethod
    async def execute_actions(
        self,
        actions: list[BrowserAction],
    ) -> list[BrowserActionResult]:
        """複数アクションを実行"""
        ...

    @abstractmethod
    async def get_page_state(self) -> PageState:
        """現在のページ状態を取得"""
        ...

    @abstractmethod
    async def screenshot(self, full_page: bool = False) -> str:
        """スクリーンショットを取得（base64）"""
        ...

    @abstractmethod
    async def extract_text(self, selector: str | None = None) -> str:
        """テキストを抽出"""
        ...

    @abstractmethod
    async def extract_data(
        self,
        schema: dict[str, Any],
        selector: str | None = None,
    ) -> dict[str, Any]:
        """構造化データを抽出"""
        ...

    @abstractmethod
    async def close(self) -> bool:
        """ブラウザを閉じる"""
        ...

