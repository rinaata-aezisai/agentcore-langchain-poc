"use client";

import { ServiceTest } from "@/widgets/service-test";

const testCases = [
  {
    id: "code-python",
    name: "Python実行",
    prompt: "Pythonで1から100までの合計を計算するコードを実行してください。",
    expectedBehavior: "Pythonコードが実行され結果が返る",
  },
  {
    id: "code-data-analysis",
    name: "データ分析",
    prompt: "サンプルデータを生成して、統計分析を行ってください。",
    expectedBehavior: "データ処理と分析結果",
  },
  {
    id: "code-visualization",
    name: "可視化",
    prompt: "matplotlibでグラフを作成してください。",
    expectedBehavior: "グラフ生成（画像出力）",
  },
  {
    id: "code-long-running",
    name: "長時間実行",
    prompt: "10秒間スリープしてから結果を返すコードを実行してください。",
    expectedBehavior: "長時間実行のサポート確認（AgentCoreは最大8時間）",
  },
];

export default function CodeInterpreterPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-8">
      <div className="mb-6">
        <div className="flex items-center gap-2 text-sm text-slate-400 mb-2">
          <span>Services</span>
          <span>/</span>
          <span className="text-white">Code Interpreter</span>
        </div>
        <h1 className="text-2xl font-bold text-white">Code Interpreter Service</h1>
      </div>

      <ServiceTest
        serviceName="Code Interpreter"
        serviceDescription="コード実行用の隔離されたサンドボックス環境。最大8時間の連続実行対応。"
        testCases={testCases}
        strandsFeatures={[
          "最大8時間の実行時間",
          "完全隔離サンドボックス",
          "ファイルシステムアクセス",
          "パッケージインストール",
          "永続ストレージ",
        ]}
        langchainFeatures={[
          "Deep Agents Sandboxes",
          "リモートサンドボックス",
          "Docker/E2B統合",
          "カスタム環境設定",
        ]}
        strandsExample={`from strands import Agent
from strands.tools import CodeInterpreter

code_interpreter = CodeInterpreter(
    max_runtime_hours=8,
    packages=["pandas", "matplotlib"]
)
agent = Agent(
    model=model,
    tools=[code_interpreter]
)`}
        langchainExample={`from langchain_community.tools import E2BDataAnalysisTool

sandbox = E2BDataAnalysisTool()
# またはDeep Agents Sandboxes
from deepagents import Sandbox

sandbox = Sandbox(env="python-3.11")`}
      />
    </div>
  );
}

