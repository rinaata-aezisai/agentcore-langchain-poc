"""Strands Browser Adapter

AgentCore Browser サービスの実装。
ブラウザ操作、スクレイピング、Web自動化。
"""

import asyncio
import base64
import time
from typing import Any

import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent.parent.parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_path))

from application.ports.browser_port import (
    BrowserPort,
    BrowserConfig,
    BrowserType,
    BrowserAction,
    ActionType,
    PageState,
    BrowserActionResult,
)


class StrandsBrowserAdapter(BrowserPort):
    """Strands Agents Browser アダプター
    
    AgentCore Browserの機能:
    - ブラウザ自動化
    - ページ操作
    - データ抽出
    - スクリーンショット
    
    実装: Playwrightベース
    """

    def __init__(self):
        self._config: BrowserConfig | None = None
        self._browser = None
        self._page = None
        self._current_state: PageState | None = None

    async def initialize(self, config: BrowserConfig) -> bool:
        """ブラウザを初期化"""
        try:
            from playwright.async_api import async_playwright
            
            self._config = config
            self._playwright = await async_playwright().start()
            
            # ブラウザタイプに応じて起動
            browser_launcher = {
                BrowserType.CHROMIUM: self._playwright.chromium,
                BrowserType.FIREFOX: self._playwright.firefox,
                BrowserType.WEBKIT: self._playwright.webkit,
            }.get(config.browser_type, self._playwright.chromium)
            
            self._browser = await browser_launcher.launch(
                headless=config.headless,
            )
            
            context_options = {
                "viewport": {
                    "width": config.viewport_width,
                    "height": config.viewport_height,
                },
            }
            if config.user_agent:
                context_options["user_agent"] = config.user_agent
            
            self._context = await self._browser.new_context(**context_options)
            self._page = await self._context.new_page()
            
            return True
        except ImportError:
            # Playwrightがインストールされていない場合はモック
            self._config = config
            return True
        except Exception as e:
            raise RuntimeError(f"Browser initialization failed: {e}")

    async def navigate(self, url: str) -> PageState:
        """URLに移動"""
        if self._page:
            await self._page.goto(url, timeout=self._config.timeout_ms)
            return await self.get_page_state()
        else:
            # モック実装
            self._current_state = PageState(
                url=url,
                title=f"Mock Page: {url}",
                text_content="Mock content",
            )
            return self._current_state

    async def execute_action(self, action: BrowserAction) -> BrowserActionResult:
        """アクションを実行"""
        start_time = time.time()
        
        try:
            if self._page:
                result = await self._execute_playwright_action(action)
            else:
                result = await self._execute_mock_action(action)
            
            result.execution_time_ms = int((time.time() - start_time) * 1000)
            return result
        except Exception as e:
            return BrowserActionResult(
                success=False,
                action=action,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

    async def _execute_playwright_action(self, action: BrowserAction) -> BrowserActionResult:
        """Playwrightアクションを実行"""
        if action.action_type == ActionType.CLICK:
            if action.selector:
                await self._page.click(action.selector)
        elif action.action_type == ActionType.TYPE:
            if action.selector and action.value:
                await self._page.fill(action.selector, action.value)
        elif action.action_type == ActionType.SCROLL:
            delta = action.options.get("delta", 500)
            await self._page.mouse.wheel(0, delta)
        elif action.action_type == ActionType.WAIT:
            wait_ms = action.options.get("ms", 1000)
            await asyncio.sleep(wait_ms / 1000)
        elif action.action_type == ActionType.SCREENSHOT:
            screenshot = await self._page.screenshot(
                full_page=action.options.get("full_page", False)
            )
            return BrowserActionResult(
                success=True,
                action=action,
                extracted_data=base64.b64encode(screenshot).decode(),
            )
        elif action.action_type == ActionType.EXTRACT:
            if action.selector:
                element = await self._page.query_selector(action.selector)
                if element:
                    text = await element.text_content()
                    return BrowserActionResult(
                        success=True,
                        action=action,
                        extracted_data=text,
                    )
        
        page_state = await self.get_page_state()
        return BrowserActionResult(
            success=True,
            action=action,
            page_state=page_state,
        )

    async def _execute_mock_action(self, action: BrowserAction) -> BrowserActionResult:
        """モックアクションを実行"""
        return BrowserActionResult(
            success=True,
            action=action,
            page_state=self._current_state,
            extracted_data=f"Mock result for {action.action_type.value}",
        )

    async def execute_actions(
        self,
        actions: list[BrowserAction],
    ) -> list[BrowserActionResult]:
        """複数アクションを実行"""
        results = []
        for action in actions:
            result = await self.execute_action(action)
            results.append(result)
            if not result.success:
                break  # エラー時は停止
        return results

    async def get_page_state(self) -> PageState:
        """現在のページ状態を取得"""
        if self._page:
            url = self._page.url
            title = await self._page.title()
            text_content = await self._page.text_content("body")
            cookies = await self._context.cookies()
            
            return PageState(
                url=url,
                title=title,
                text_content=text_content[:5000] if text_content else None,  # 制限
                cookies=cookies,
            )
        
        return self._current_state or PageState(url="", title="")

    async def screenshot(self, full_page: bool = False) -> str:
        """スクリーンショットを取得（base64）"""
        if self._page:
            screenshot = await self._page.screenshot(full_page=full_page)
            return base64.b64encode(screenshot).decode()
        return ""

    async def extract_text(self, selector: str | None = None) -> str:
        """テキストを抽出"""
        if self._page:
            if selector:
                element = await self._page.query_selector(selector)
                if element:
                    return await element.text_content() or ""
            else:
                return await self._page.text_content("body") or ""
        return "Mock text content"

    async def extract_data(
        self,
        schema: dict[str, Any],
        selector: str | None = None,
    ) -> dict[str, Any]:
        """構造化データを抽出"""
        # 簡易実装: スキーマに基づいてデータを抽出
        result = {}
        
        if self._page:
            for key, field_selector in schema.items():
                try:
                    element = await self._page.query_selector(field_selector)
                    if element:
                        result[key] = await element.text_content()
                except:
                    result[key] = None
        else:
            # モック
            result = {key: f"Mock value for {key}" for key in schema}
        
        return result

    async def close(self) -> bool:
        """ブラウザを閉じる"""
        try:
            if self._browser:
                await self._browser.close()
            if hasattr(self, '_playwright') and self._playwright:
                await self._playwright.stop()
            return True
        except:
            return False


def create_strands_browser() -> StrandsBrowserAdapter:
    """ファクトリ関数"""
    return StrandsBrowserAdapter()

