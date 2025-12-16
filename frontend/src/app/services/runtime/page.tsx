"use client";

import { ServiceTest } from "@/widgets/service-test";

const testCases = [
  {
    id: "runtime-status",
    name: "ステータス取得",
    endpoint: "/services/runtime/status",
    method: "GET" as const,
    expectedBehavior: "現在のランタイムステータスを取得",
  },
  {
    id: "runtime-execute",
    name: "基本実行テスト",
    endpoint: "/services/runtime/execute",
    method: "POST" as const,
    body: { instruction: "Hello, World!と応答してください。" },
    expectedBehavior: "シンプルな応答が返る",
  },
  {
    id: "runtime-execute-context",
    name: "コンテキスト付き実行",
    endpoint: "/services/runtime/execute",
    method: "POST" as const,
    body: { 
      instruction: "前の発言を要約してください",
      context: [{ role: "user", content: "私の名前は田中です" }]
    },
    expectedBehavior: "コンテキストを考慮した応答",
  },
];

export default function RuntimePage() {
  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-2 text-sm text-slate-400 mb-2">
          <span>Services</span>
          <span>/</span>
          <span className="text-white">Runtime</span>
        </div>
        <h1 className="text-2xl font-bold text-white">Runtime Service</h1>
      </div>

      <ServiceTest
        serviceName="Runtime"
        serviceKey="runtime"
        serviceDescription="AIエージェントとツールをホストするサーバーレス実行環境。双方向ストリーミング対応。"
        testCases={testCases}
        strandsFeatures={[
          "Bedrock完全統合",
          "双方向音声ストリーミング (Bidirectional)",
          "自動スケーリング",
          "低レイテンシ実行",
        ]}
        langchainFeatures={[
          "LangServe / LangGraph Cloud",
          "カスタムデプロイオプション",
          "マルチプロバイダー対応",
          "柔軟なホスティング",
        ]}
        strandsExample={`from strands import Agent
from strands.models import BedrockModel

model = BedrockModel(
    model_id="anthropic.claude-3-5-sonnet-20241022-v2:0"
)
agent = Agent(model=model)
response = agent("Hello!")`}
        langchainExample={`from langchain_aws import ChatBedrock

model = ChatBedrock(
    model_id="anthropic.claude-3-5-sonnet-20241022-v2:0"
)
response = await model.ainvoke("Hello!")`}
      />
    </div>
  );
}
