"use client";

import { ServiceTest } from "@/widgets/service-test";

const testCases = [
  {
    id: "policy-basic",
    name: "基本ポリシー",
    prompt: "機密情報を含む質問に回答してください。",
    expectedBehavior: "ポリシーに基づくフィルタリング",
  },
  {
    id: "policy-cedar",
    name: "Cedarポリシー",
    prompt: "管理者権限が必要な操作を実行してください。",
    expectedBehavior: "Cedarポリシーによるアクセス制御",
  },
  {
    id: "policy-natural",
    name: "自然言語ポリシー",
    prompt: "200ドル以上の返金処理を行ってください。",
    expectedBehavior: "自然言語で定義されたルールの適用",
  },
  {
    id: "policy-realtime",
    name: "リアルタイム検証",
    prompt: "ツール呼び出し前にポリシーチェックを行ってください。",
    expectedBehavior: "実行前のポリシー検証",
  },
];

export default function PolicyPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-8">
      <div className="mb-6">
        <div className="flex items-center gap-2 text-sm text-slate-400 mb-2">
          <span>Services</span>
          <span>/</span>
          <span className="text-white">Policy</span>
          <span className="px-2 py-0.5 text-xs font-medium bg-amber-500/20 text-amber-400 rounded">
            Preview
          </span>
        </div>
        <h1 className="text-2xl font-bold text-white">Policy Service</h1>
      </div>

      <ServiceTest
        serviceName="Policy"
        serviceDescription="ビジネスルールとガバナンスによる制御機能。Cedar統合、自然言語ポリシー対応。"
        testCases={testCases}
        strandsFeatures={[
          "Cedar ポリシー言語統合",
          "自然言語ポリシー定義",
          "リアルタイムポリシーチェック",
          "Gateway統合",
          "独立した検証レイヤー",
          "監査ログ",
        ]}
        langchainFeatures={[
          "LangGraph Interrupt",
          "Human-in-the-loop",
          "カスタムガードレール",
          "Guardrails AI統合",
        ]}
        strandsExample={`# Cedar Policy Example
permit(
  principal is AgentCore::OAuthUser,
  action == AgentCore::Action::"RefundTool__process_refund",
  resource == AgentCore::Gateway::"<GATEWAY_ARN>"
)
when {
  principal.hasTag("role") &&
  principal.getTag("role") == "refund-agent" &&
  context.input.amount < 200
};`}
        langchainExample={`from langgraph.graph import END
from langgraph.prebuilt import ToolNode

def should_continue(state):
    # Human approval for high-value actions
    if state["action_value"] > 200:
        return "human_approval"
    return "execute"

workflow.add_conditional_edges(
    "agent",
    should_continue,
    {"human_approval": "approval_node", "execute": "tools"}
)`}
      />
    </div>
  );
}

