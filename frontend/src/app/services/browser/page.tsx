"use client";

import { ServiceTest } from "@/widgets/service-test";

const testCases = [
  {
    id: "browser-navigate",
    name: "ページナビゲーション",
    prompt: "Googleのホームページにアクセスしてタイトルを取得してください。",
    expectedBehavior: "Webページへのアクセスとスクレイピング",
  },
  {
    id: "browser-form",
    name: "フォーム操作",
    prompt: "検索フォームに「AI Agent」と入力して検索を実行してください。",
    expectedBehavior: "フォーム入力と送信",
  },
  {
    id: "browser-screenshot",
    name: "スクリーンショット",
    prompt: "現在のページのスクリーンショットを撮影してください。",
    expectedBehavior: "画像キャプチャ",
  },
  {
    id: "browser-dynamic",
    name: "動的コンテンツ",
    prompt: "JavaScriptで動的に生成されるコンテンツを取得してください。",
    expectedBehavior: "SPAサイトの操作",
  },
];

export default function BrowserPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-8">
      <div className="mb-6">
        <div className="flex items-center gap-2 text-sm text-slate-400 mb-2">
          <span>Services</span>
          <span>/</span>
          <span className="text-white">Browser</span>
        </div>
        <h1 className="text-2xl font-bold text-white">Browser Service</h1>
      </div>

      <ServiceTest
        serviceName="Browser"
        serviceDescription="Webアプリケーション操作用のクラウドブラウザ環境。自動化タスク対応。"
        testCases={testCases}
        strandsFeatures={[
          "クラウドブラウザ環境",
          "セッション永続化",
          "ヘッドレス/ヘッドフル両対応",
          "認証セッション管理",
        ]}
        langchainFeatures={[
          "Playwright統合",
          "Browser Use",
          "Puppeteer対応",
          "カスタムブラウザツール",
        ]}
        strandsExample={`from strands import Agent
from strands.tools import Browser

browser = Browser(
    headless=True,
    session_persist=True
)
agent = Agent(
    model=model,
    tools=[browser]
)`}
        langchainExample={`from browser_use import Agent as BrowserAgent
from langchain_anthropic import ChatAnthropic

agent = BrowserAgent(
    task="Navigate to Google",
    llm=ChatAnthropic()
)`}
      />
    </div>
  );
}

