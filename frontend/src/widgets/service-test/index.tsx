"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { backendServiceApi, ServiceExecuteResponse } from "@/shared/api/backend-client";
import { cn } from "@/shared/lib/utils";

interface ServiceTestProps {
  serviceName: string;
  serviceDescription: string;
  testCases: TestCase[];
  strandsFeatures: string[];
  langchainFeatures: string[];
  strandsExample?: string;
  langchainExample?: string;
}

interface TestCase {
  id: string;
  name: string;
  prompt: string;
  expectedBehavior: string;
}

interface TestResult {
  testId: string;
  agentType: "strands" | "langchain";
  success: boolean;
  response: string;
  latencyMs: number;
  error?: string;
}

type ServiceKey = keyof typeof backendServiceApi;

export function ServiceTest({
  serviceName,
  serviceDescription,
  testCases,
  strandsFeatures,
  langchainFeatures,
  strandsExample,
  langchainExample,
}: ServiceTestProps) {
  const [results, setResults] = useState<TestResult[]>([]);
  const [selectedTest, setSelectedTest] = useState<string | null>(null);
  const [selectedAgentType, setSelectedAgentType] = useState<"strands" | "langchain" | null>(null);

  // サービス名からAPIキーを取得
  const getServiceKey = (name: string): ServiceKey => {
    const keyMap: Record<string, ServiceKey> = {
      "Runtime": "runtime",
      "Memory": "memory",
      "Gateway": "gateway",
      "Identity": "identity",
      "Code Interpreter": "codeInterpreter",
      "Browser": "browser",
      "Observability": "observability",
      "Evaluations": "evaluations",
      "Policy": "policy",
    };
    return keyMap[name] || "runtime";
  };

  // テスト実行
  const runTest = useMutation({
    mutationFn: async ({
      testCase,
      agentType,
    }: {
      testCase: TestCase;
      agentType: "strands" | "langchain";
    }): Promise<ServiceExecuteResponse> => {
      const serviceKey = getServiceKey(serviceName);
      const api = backendServiceApi[serviceKey];
      return api.execute({
        instruction: testCase.prompt,
        agent_type: agentType,
      });
    },
    onSuccess: (data, { testCase, agentType }) => {
      setResults((prev) => [
        ...prev.filter((r) => !(r.testId === testCase.id && r.agentType === agentType)),
        {
          testId: testCase.id,
          agentType,
          success: true,
          response: data.content,
          latencyMs: data.latency_ms,
        },
      ]);
    },
    onError: (error, { testCase, agentType }) => {
      setResults((prev) => [
        ...prev.filter((r) => !(r.testId === testCase.id && r.agentType === agentType)),
        {
          testId: testCase.id,
          agentType,
          success: false,
          response: "",
          latencyMs: 0,
          error: error instanceof Error ? error.message : "Unknown error",
        },
      ]);
    },
  });

  const getResultForTest = (testId: string, agentType: "strands" | "langchain") =>
    results.find((r) => r.testId === testId && r.agentType === agentType);

  // 全テスト実行
  const runAllTests = useMutation({
    mutationFn: async (agentType: "strands" | "langchain") => {
      const serviceKey = getServiceKey(serviceName);
      const api = backendServiceApi[serviceKey];
      
      const results = [];
      for (const testCase of testCases) {
        try {
          const result = await api.execute({
            instruction: testCase.prompt,
            agent_type: agentType,
          });
          results.push({
            testId: testCase.id,
            agentType,
            success: true,
            response: result.content,
            latencyMs: result.latency_ms,
          });
        } catch (error) {
          results.push({
            testId: testCase.id,
            agentType,
            success: false,
            response: "",
            latencyMs: 0,
            error: error instanceof Error ? error.message : "Unknown error",
          });
        }
      }
      return results;
    },
    onSuccess: (newResults) => {
      setResults((prev) => {
        const agentType = newResults[0]?.agentType;
        const filtered = prev.filter((r) => r.agentType !== agentType);
        return [...filtered, ...newResults];
      });
    },
  });

  return (
    <div className="space-y-8">
      {/* Service Info */}
      <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
        <h2 className="text-xl font-semibold text-white mb-2">{serviceName}</h2>
        <p className="text-slate-400 mb-4">{serviceDescription}</p>

        {/* Feature Comparison */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <h3 className="text-sm font-medium text-blue-400 mb-2">Strands Agents (AgentCore)</h3>
            <ul className="space-y-1">
              {strandsFeatures.map((feature, i) => (
                <li key={i} className="text-sm text-slate-300 flex items-center gap-2">
                  <span className="text-green-400">✓</span> {feature}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="text-sm font-medium text-purple-400 mb-2">LangChain + LangGraph</h3>
            <ul className="space-y-1">
              {langchainFeatures.map((feature, i) => (
                <li key={i} className="text-sm text-slate-300 flex items-center gap-2">
                  <span className="text-green-400">✓</span> {feature}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* Bulk Test Buttons */}
      <div className="flex gap-4">
        <button
          onClick={() => runAllTests.mutate("strands")}
          disabled={runAllTests.isPending}
          className={cn(
            "flex-1 py-3 rounded-lg font-medium transition-colors",
            "bg-blue-600 hover:bg-blue-700 text-white",
            runAllTests.isPending && "opacity-50 cursor-not-allowed"
          )}
        >
          {runAllTests.isPending ? "実行中..." : "🚀 Strands 全テスト実行"}
        </button>
        <button
          onClick={() => runAllTests.mutate("langchain")}
          disabled={runAllTests.isPending}
          className={cn(
            "flex-1 py-3 rounded-lg font-medium transition-colors",
            "bg-purple-600 hover:bg-purple-700 text-white",
            runAllTests.isPending && "opacity-50 cursor-not-allowed"
          )}
        >
          {runAllTests.isPending ? "実行中..." : "🔗 LangChain 全テスト実行"}
        </button>
      </div>

      {/* Test Cases */}
      <div>
        <h3 className="text-lg font-semibold text-white mb-4">検証テストケース</h3>
        <div className="space-y-4">
          {testCases.map((test) => {
            const strandsResult = getResultForTest(test.id, "strands");
            const langchainResult = getResultForTest(test.id, "langchain");
            const isRunning = runTest.isPending && selectedTest === test.id;

            return (
              <div
                key={test.id}
                className={cn(
                  "bg-slate-800/50 border rounded-xl p-4 transition-all",
                  selectedTest === test.id ? "border-blue-500" : "border-slate-700"
                )}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <h4 className="font-medium text-white">{test.name}</h4>
                    <p className="text-sm text-slate-400 mt-1">{test.expectedBehavior}</p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => {
                        setSelectedTest(test.id);
                        setSelectedAgentType("strands");
                        runTest.mutate({ testCase: test, agentType: "strands" });
                      }}
                      disabled={isRunning && selectedAgentType === "strands"}
                      className={cn(
                        "px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
                        strandsResult?.success
                          ? "bg-green-600/20 text-green-400 border border-green-600"
                          : strandsResult?.error
                          ? "bg-red-600/20 text-red-400 border border-red-600"
                          : "bg-blue-600 hover:bg-blue-700 text-white",
                        isRunning && selectedAgentType === "strands" && "opacity-50"
                      )}
                    >
                      {isRunning && selectedAgentType === "strands"
                        ? "実行中..."
                        : strandsResult?.success
                        ? `✓ Strands ${strandsResult.latencyMs}ms`
                        : strandsResult?.error
                        ? "✗ Strands"
                        : "Strands"}
                    </button>
                    <button
                      onClick={() => {
                        setSelectedTest(test.id);
                        setSelectedAgentType("langchain");
                        runTest.mutate({ testCase: test, agentType: "langchain" });
                      }}
                      disabled={isRunning && selectedAgentType === "langchain"}
                      className={cn(
                        "px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
                        langchainResult?.success
                          ? "bg-green-600/20 text-green-400 border border-green-600"
                          : langchainResult?.error
                          ? "bg-red-600/20 text-red-400 border border-red-600"
                          : "bg-purple-600 hover:bg-purple-700 text-white",
                        isRunning && selectedAgentType === "langchain" && "opacity-50"
                      )}
                    >
                      {isRunning && selectedAgentType === "langchain"
                        ? "実行中..."
                        : langchainResult?.success
                        ? `✓ LangChain ${langchainResult.latencyMs}ms`
                        : langchainResult?.error
                        ? "✗ LangChain"
                        : "LangChain"}
                    </button>
                  </div>
                </div>

                <div className="p-3 bg-slate-900/50 rounded-lg">
                  <p className="text-xs text-slate-500 mb-1">Prompt:</p>
                  <p className="text-sm text-slate-300 font-mono">{test.prompt}</p>
                </div>

                {/* Results Comparison */}
                {(strandsResult || langchainResult) && (
                  <div className="grid grid-cols-2 gap-3 mt-3">
                    {/* Strands Result */}
                    <div
                      className={cn(
                        "p-3 rounded-lg",
                        strandsResult?.success
                          ? "bg-green-900/20 border border-green-800"
                          : strandsResult?.error
                          ? "bg-red-900/20 border border-red-800"
                          : "bg-slate-900/30 border border-slate-700"
                      )}
                    >
                      <p className="text-xs text-blue-400 mb-1 font-medium">Strands Agents</p>
                      {strandsResult ? (
                        <>
                          <p className="text-sm text-slate-300">
                            {strandsResult.success ? strandsResult.response : strandsResult.error}
                          </p>
                          {strandsResult.success && (
                            <p className="text-xs text-slate-500 mt-2">
                              Latency: {strandsResult.latencyMs}ms
                            </p>
                          )}
                        </>
                      ) : (
                        <p className="text-xs text-slate-500">未実行</p>
                      )}
                    </div>

                    {/* LangChain Result */}
                    <div
                      className={cn(
                        "p-3 rounded-lg",
                        langchainResult?.success
                          ? "bg-green-900/20 border border-green-800"
                          : langchainResult?.error
                          ? "bg-red-900/20 border border-red-800"
                          : "bg-slate-900/30 border border-slate-700"
                      )}
                    >
                      <p className="text-xs text-purple-400 mb-1 font-medium">LangChain</p>
                      {langchainResult ? (
                        <>
                          <p className="text-sm text-slate-300">
                            {langchainResult.success ? langchainResult.response : langchainResult.error}
                          </p>
                          {langchainResult.success && (
                            <p className="text-xs text-slate-500 mt-2">
                              Latency: {langchainResult.latencyMs}ms
                            </p>
                          )}
                        </>
                      ) : (
                        <p className="text-xs text-slate-500">未実行</p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Code Examples */}
      {(strandsExample || langchainExample) && (
        <div className="grid grid-cols-2 gap-4">
          {strandsExample && (
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
              <h4 className="text-sm font-medium text-blue-400 mb-3">Strands Agents 実装例</h4>
              <pre className="text-xs text-slate-300 overflow-x-auto p-3 bg-slate-900/50 rounded-lg">
                <code>{strandsExample}</code>
              </pre>
            </div>
          )}
          {langchainExample && (
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
              <h4 className="text-sm font-medium text-purple-400 mb-3">LangChain 実装例</h4>
              <pre className="text-xs text-slate-300 overflow-x-auto p-3 bg-slate-900/50 rounded-lg">
                <code>{langchainExample}</code>
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
