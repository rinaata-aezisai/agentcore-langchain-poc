"use client";

import { ServiceTest } from "@/widgets/service-test";

const testCases = [
  {
    id: "obs-traces",
    name: "トレース一覧",
    endpoint: "/services/observability/traces",
    method: "GET" as const,
    expectedBehavior: "記録されたトレースの一覧を取得",
  },
  {
    id: "obs-metrics",
    name: "メトリクス取得",
    endpoint: "/services/observability/metrics",
    method: "GET" as const,
    expectedBehavior: "システムメトリクスを取得",
  },
  {
    id: "obs-start-trace",
    name: "トレース開始",
    endpoint: "/services/observability/traces",
    method: "POST" as const,
    body: { name: "test-trace", metadata: { test: true } },
    expectedBehavior: "新しいトレースを開始",
  },
];

export default function ObservabilityPage() {
  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-2 text-sm text-slate-400 mb-2">
          <span>Services</span>
          <span>/</span>
          <span className="text-white">Observability</span>
        </div>
        <h1 className="text-2xl font-bold text-white">Observability Service</h1>
      </div>

      <ServiceTest
        serviceName="Observability"
        serviceKey="observability"
        serviceDescription="分散トレーシング、メトリクス収集、ログ管理。LLM実行の可視化。"
        testCases={testCases}
        strandsFeatures={[
          "AgentCore Observability",
          "CloudWatch統合",
          "X-Ray トレーシング",
          "自動計装",
        ]}
        langchainFeatures={[
          "LangFuse統合",
          "LangSmith統合",
          "Callbacks対応",
          "カスタムトレーサー",
        ]}
        strandsExample={`# AgentCore Observability
# CloudWatch + X-Ray自動統合

# 全てのAgent実行が自動トレース
agent = Agent(model=model)
response = agent("Hello!")  # 自動トレース

# CloudWatch Logs, X-Rayで確認可能`}
        langchainExample={`from langfuse.callback import CallbackHandler

# LangFuse Callback
handler = CallbackHandler(
    public_key="...",
    secret_key="...",
)

# 実行時にcallbackを指定
response = model.invoke(
    "Hello!",
    config={"callbacks": [handler]}
)

# LangSmith
import langsmith
langsmith.configure(api_key="...")`}
      />
    </div>
  );
}
