"use client";

import { ServiceTest } from "@/widgets/service-test";

const testCases = [
  {
    id: "browser-state",
    name: "ページ状態取得",
    endpoint: "/services/browser/state",
    method: "GET" as const,
    expectedBehavior: "現在のページ状態を取得",
  },
  {
    id: "browser-navigate",
    name: "ナビゲーション",
    endpoint: "/services/browser/navigate",
    method: "POST" as const,
    body: { url: "https://example.com" },
    expectedBehavior: "指定URLに移動",
  },
  {
    id: "browser-text",
    name: "テキスト抽出",
    endpoint: "/services/browser/text",
    method: "GET" as const,
    expectedBehavior: "ページからテキストを抽出",
  },
];

export default function BrowserPage() {
  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-2 text-sm text-slate-400 mb-2">
          <span>Services</span>
          <span>/</span>
          <span className="text-white">Browser</span>
        </div>
        <h1 className="text-2xl font-bold text-white">Browser Service</h1>
      </div>

      <ServiceTest
        serviceName="Browser"
        serviceKey="browser"
        serviceDescription="ブラウザ自動化とWebスクレイピング。Playwrightベースの安全な実行環境。"
        testCases={testCases}
        strandsFeatures={[
          "AgentCore Browser統合",
          "自動スクリーンショット",
          "DOM操作",
          "JavaScript実行",
        ]}
        langchainFeatures={[
          "Playwright Tool",
          "Browser Use Agent",
          "BeautifulSoup統合",
          "Selenium対応",
        ]}
        strandsExample={`from strands import Agent
from strands.tools import browser

agent = Agent(
    model=model,
    tools=[browser]
)

# Web検索を含むタスク
response = agent(
    "example.comにアクセスして内容を要約して"
)`}
        langchainExample={`from playwright.async_api import async_playwright

async def browse(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)
        content = await page.content()
        await browser.close()
        return content

# Browser Use Agent
from browser_use import Agent
agent = Agent(task="Navigate and extract")`}
      />
    </div>
  );
}
