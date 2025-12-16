"use client";

import { ServiceTest } from "@/widgets/service-test";

const testCases = [
  {
    id: "eval-results",
    name: "評価結果一覧",
    endpoint: "/services/evaluations/results",
    method: "GET" as const,
    expectedBehavior: "過去の評価結果を取得",
  },
  {
    id: "eval-single",
    name: "単一ケース評価",
    endpoint: "/services/evaluations/evaluate/single",
    method: "POST" as const,
    body: { 
      case: {
        case_id: "test-1",
        input_data: "What is 2+2?",
        expected_output: "4",
        actual_output: "4"
      }
    },
    expectedBehavior: "単一テストケースを評価",
  },
  {
    id: "eval-llm-judge",
    name: "LLM-as-a-Judge",
    endpoint: "/services/evaluations/evaluate/llm-judge",
    method: "POST" as const,
    body: { 
      case: { case_id: "judge-1", input_data: "test", actual_output: "response" },
      criteria: "回答の正確性と有用性"
    },
    expectedBehavior: "LLMによる評価を実行",
  },
];

export default function EvaluationsPage() {
  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-2 text-sm text-slate-400 mb-2">
          <span>Services</span>
          <span>/</span>
          <span className="text-white">Evaluations</span>
        </div>
        <h1 className="text-2xl font-bold text-white">Evaluations Service</h1>
      </div>

      <ServiceTest
        serviceName="Evaluations"
        serviceKey="evaluations"
        serviceDescription="エージェント品質評価、ベンチマーク、LLM-as-a-Judge。継続的品質監視。"
        testCases={testCases}
        strandsFeatures={[
          "AgentCore Evaluations",
          "自動品質チェック",
          "Bedrock評価統合",
          "カスタムメトリクス",
        ]}
        langchainFeatures={[
          "LangSmith Evaluations",
          "RAGAS統合",
          "カスタムEvaluators",
          "A/Bテスト",
        ]}
        strandsExample={`# AgentCore Evaluations
# Bedrock Model Evaluationと統合

# 評価ジョブの作成
evaluation_job = bedrock.create_evaluation_job(
    modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
    evaluationConfig={
        "automated": {
            "datasetMetricConfigs": [...]
        }
    }
)`}
        langchainExample={`from langsmith import Client
from langsmith.evaluation import evaluate

client = Client()

# データセット評価
results = evaluate(
    lambda inputs: model.invoke(inputs["question"]),
    data="my-dataset",
    evaluators=[
        "qa",
        "context_recall",
    ],
)

# RAGAS
from ragas import evaluate
from ragas.metrics import faithfulness`}
      />
    </div>
  );
}
