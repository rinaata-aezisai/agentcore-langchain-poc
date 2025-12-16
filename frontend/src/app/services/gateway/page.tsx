"use client";

import { ServiceTest } from "@/widgets/service-test";

const testCases = [
  {
    id: "gateway-tool-call",
    name: "ツール呼び出し",
    prompt: "東京の天気を調べてください。",
    expectedBehavior: "天気ツールが呼び出される",
  },
  {
    id: "gateway-multi-tool",
    name: "複数ツール連携",
    prompt: "東京の天気を調べて、その結果を元にタスクを作成してください。",
    expectedBehavior: "複数ツールが順序立てて呼び出される",
  },
  {
    id: "gateway-mcp",
    name: "MCPサーバー連携",
    prompt: "MCPプロトコルでツールを呼び出せますか？",
    expectedBehavior: "MCP対応状況の確認",
  },
  {
    id: "gateway-api-transform",
    name: "API変換",
    prompt: "外部APIの結果を自然言語で説明してください。",
    expectedBehavior: "APIレスポンスの適切な変換",
  },
];

export default function GatewayPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-8">
      <div className="mb-6">
        <div className="flex items-center gap-2 text-sm text-slate-400 mb-2">
          <span>Services</span>
          <span>/</span>
          <span className="text-white">Gateway</span>
        </div>
        <h1 className="text-2xl font-bold text-white">Gateway Service</h1>
      </div>

      <ServiceTest
        serviceName="Gateway"
        serviceDescription="API、Lambda関数をMCP対応ツールに変換。Model Context Protocol完全サポート。"
        testCases={testCases}
        strandsFeatures={[
          "MCP (Model Context Protocol) 完全対応",
          "Lambda関数の自動ツール化",
          "API Gateway統合",
          "自動スキーマ生成",
        ]}
        langchainFeatures={[
          "LangChain Tools",
          "@tool デコレータ",
          "ToolNode (LangGraph)",
          "カスタムツール定義",
        ]}
        strandsExample={`from strands import tool

@tool
def get_weather(location: str) -> dict:
    """Get weather for location"""
    return {"temp": 20, "condition": "sunny"}

agent = Agent(
    model=model,
    tools=[get_weather]
)`}
        langchainExample={`from langchain_core.tools import tool

@tool
def get_weather(location: str) -> dict:
    """Get weather for location"""
    return {"temp": 20, "condition": "sunny"}

model_with_tools = model.bind_tools([get_weather])`}
      />
    </div>
  );
}

