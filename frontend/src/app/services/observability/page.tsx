"use client";

import { ServiceTest } from "@/widgets/service-test";

const testCases = [
  {
    id: "obs-trace",
    name: "トレース",
    prompt: "現在の会話のトレースIDを教えてください。",
    expectedBehavior: "トレーシング情報の取得",
  },
  {
    id: "obs-metrics",
    name: "メトリクス",
    prompt: "レスポンス時間とトークン使用量を確認してください。",
    expectedBehavior: "パフォーマンスメトリクス",
  },
  {
    id: "obs-logs",
    name: "ログ",
    prompt: "デバッグログを出力してください。",
    expectedBehavior: "ログ出力の確認",
  },
  {
    id: "obs-cost",
    name: "コスト追跡",
    prompt: "この会話のコストを計算してください。",
    expectedBehavior: "コスト情報の取得",
  },
];

export default function ObservabilityPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-8">
      <div className="mb-6">
        <div className="flex items-center gap-2 text-sm text-slate-400 mb-2">
          <span>Services</span>
          <span>/</span>
          <span className="text-white">Observability</span>
        </div>
        <h1 className="text-2xl font-bold text-white">Observability Service</h1>
      </div>

      <ServiceTest
        serviceName="Observability"
        serviceDescription="統合されたトレース、デバッグ、監視機能。CloudWatch/Evaluations統合。"
        testCases={testCases}
        strandsFeatures={[
          "CloudWatch統合",
          "X-Rayトレーシング",
          "リアルタイムメトリクス",
          "Evaluations連携",
          "コストダッシュボード",
        ]}
        langchainFeatures={[
          "LangSmith",
          "LangFuse",
          "Unified Cost Tracking",
          "カスタムコールバック",
          "OpenTelemetry対応",
        ]}
        strandsExample={`from strands import Agent
from strands.observability import CloudWatchTracer

tracer = CloudWatchTracer(
    log_group="/agentcore/poc"
)
agent = Agent(
    model=model,
    tracer=tracer
)`}
        langchainExample={`from langfuse.callback import CallbackHandler

handler = CallbackHandler(
    public_key="...",
    secret_key="..."
)
response = await model.ainvoke(
    "Hello",
    config={"callbacks": [handler]}
)`}
      />
    </div>
  );
}

