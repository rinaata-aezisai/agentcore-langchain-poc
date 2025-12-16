"use client";

import { ServiceTest } from "@/widgets/service-test";

const testCases = [
  {
    id: "code-env",
    name: "環境情報取得",
    endpoint: "/services/code-interpreter/environment",
    method: "GET" as const,
    expectedBehavior: "実行環境の情報を取得",
  },
  {
    id: "code-execute",
    name: "Pythonコード実行",
    endpoint: "/services/code-interpreter/execute",
    method: "POST" as const,
    body: { code: "print('Hello from Python!')", language: "python" },
    expectedBehavior: "Pythonコードを安全に実行",
  },
  {
    id: "code-files",
    name: "ファイル一覧",
    endpoint: "/services/code-interpreter/files",
    method: "GET" as const,
    expectedBehavior: "実行環境のファイル一覧を取得",
  },
];

export default function CodeInterpreterPage() {
  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-2 text-sm text-slate-400 mb-2">
          <span>Services</span>
          <span>/</span>
          <span className="text-white">Code Interpreter</span>
        </div>
        <h1 className="text-2xl font-bold text-white">Code Interpreter Service</h1>
      </div>

      <ServiceTest
        serviceName="Code Interpreter"
        serviceKey="code-interpreter"
        serviceDescription="安全なサンドボックス環境でのコード実行。Python, JavaScript, Bashをサポート。"
        testCases={testCases}
        strandsFeatures={[
          "AgentCore統合サンドボックス",
          "自動リソース制限",
          "ファイルI/O対応",
          "マルチ言語サポート",
        ]}
        langchainFeatures={[
          "PythonREPL Tool",
          "E2B Code Interpreter",
          "カスタム実行環境",
          "Jupyter統合",
        ]}
        strandsExample={`from strands import Agent
from strands.tools import code_interpreter

agent = Agent(
    model=model,
    tools=[code_interpreter]
)

# コード実行を含むタスク
response = agent(
    "フィボナッチ数列の最初の10項を計算して"
)`}
        langchainExample={`from langchain_experimental.utilities import PythonREPL
from langchain.tools import Tool

repl = PythonREPL()

python_tool = Tool(
    name="python_repl",
    description="Python code executor",
    func=repl.run,
)

# E2B Code Interpreter
from e2b_code_interpreter import CodeInterpreter

sandbox = CodeInterpreter()
execution = sandbox.notebook.exec_cell(code)`}
      />
    </div>
  );
}
