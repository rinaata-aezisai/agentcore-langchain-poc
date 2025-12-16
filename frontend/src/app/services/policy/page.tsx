"use client";

import { ServiceTest } from "@/widgets/service-test";

const testCases = [
  {
    id: "policy-rules",
    name: "ルール一覧",
    endpoint: "/services/policy/rules",
    method: "GET" as const,
    expectedBehavior: "登録済みポリシールールを取得",
  },
  {
    id: "policy-validate-input",
    name: "入力検証",
    endpoint: "/services/policy/validate/input",
    method: "POST" as const,
    body: { content: "test@example.com に連絡してください" },
    expectedBehavior: "入力内容のポリシー違反をチェック",
  },
  {
    id: "policy-detect-pii",
    name: "PII検出",
    endpoint: "/services/policy/detect/pii",
    method: "POST" as const,
    body: { content: "私の電話番号は090-1234-5678です" },
    expectedBehavior: "個人情報を検出",
  },
  {
    id: "policy-stats",
    name: "違反統計",
    endpoint: "/services/policy/stats",
    method: "GET" as const,
    expectedBehavior: "ポリシー違反の統計を取得",
  },
];

export default function PolicyPage() {
  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-2 text-sm text-slate-400 mb-2">
          <span>Services</span>
          <span>/</span>
          <span className="text-white">Policy</span>
        </div>
        <h1 className="text-2xl font-bold text-white">Policy Service</h1>
      </div>

      <ServiceTest
        serviceName="Policy (Guardrails)"
        serviceKey="policy"
        serviceDescription="入出力フィルタリング、PII検出、コンテンツモデレーション。安全なAI運用。"
        testCases={testCases}
        strandsFeatures={[
          "Bedrock Guardrails統合",
          "自動PII検出",
          "コンテンツフィルタ",
          "カスタムポリシー",
        ]}
        langchainFeatures={[
          "Guardrails AI統合",
          "NeMo Guardrails",
          "Output Parsers",
          "カスタムバリデータ",
        ]}
        strandsExample={`# Bedrock Guardrails
guardrail = bedrock.create_guardrail(
    name="content-filter",
    contentPolicyConfig={
        "filtersConfig": [
            {
                "type": "HATE",
                "inputStrength": "HIGH",
                "outputStrength": "HIGH"
            }
        ]
    },
    sensitiveInformationPolicyConfig={
        "piiEntitiesConfig": [
            {"type": "EMAIL", "action": "BLOCK"}
        ]
    }
)`}
        langchainExample={`import guardrails as gd
from nemoguardrails import RailsConfig, LLMRails

# Guardrails AI
guard = gd.Guard.from_pydantic(
    output_class=SafeResponse
)

# NeMo Guardrails
config = RailsConfig.from_path("./config")
rails = LLMRails(config)

response = rails.generate(
    messages=[{"role": "user", "content": prompt}]
)`}
      />
    </div>
  );
}
