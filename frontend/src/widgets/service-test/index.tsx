"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AgentType, apiClient } from "@/shared/api/client";
import { cn } from "@/shared/lib/utils";

interface ServiceTestProps {
  serviceName: string;
  serviceKey: string;
  serviceDescription: string;
  testCases: TestCase[];
  strandsFeatures: string[];
  langchainFeatures: string[];
  strandsExample?: string;
  langchainExample?: string;
  apiEndpoint?: string;
}

interface TestCase {
  id: string;
  name: string;
  endpoint: string;
  method: "GET" | "POST";
  body?: Record<string, unknown>;
  expectedBehavior: string;
}

interface TestResult {
  testId: string;
  agentType: AgentType;
  success: boolean;
  response: unknown;
  latencyMs: number;
  error?: string;
}

export function ServiceTest({
  serviceName,
  serviceKey,
  serviceDescription,
  testCases,
  strandsFeatures,
  langchainFeatures,
  strandsExample,
  langchainExample,
}: ServiceTestProps) {
  const [results, setResults] = useState<TestResult[]>([]);
  const [selectedTest, setSelectedTest] = useState<string | null>(null);
  const [runningAgent, setRunningAgent] = useState<AgentType | null>(null);

  // テスト実行
  const runTest = useMutation({
    mutationFn: async ({ testCase, agentType }: { testCase: TestCase; agentType: AgentType }) => {
      const startTime = Date.now();
      const url = `${testCase.endpoint}?agent_type=${agentType}`;
      
      const response = await apiClient<unknown>(url, {
        method: testCase.method,
        body: testCase.body ? JSON.stringify(testCase.body) : undefined,
      });
      
      return {
        response,
        latencyMs: Date.now() - startTime,
      };
    },
    onSuccess: (data, { testCase, agentType }) => {
      setResults((prev) => {
        // 同じテスト・エージェントタイプの結果を更新
        const filtered = prev.filter(
          (r) => !(r.testId === testCase.id && r.agentType === agentType)
        );
        return [
          ...filtered,
          {
            testId: testCase.id,
            agentType,
            success: true,
            response: data.response,
            latencyMs: data.latencyMs,
          },
        ];
      });
      setRunningAgent(null);
    },
    onError: (error, { testCase, agentType }) => {
      setResults((prev) => {
        const filtered = prev.filter(
          (r) => !(r.testId === testCase.id && r.agentType === agentType)
        );
        return [
          ...filtered,
          {
            testId: testCase.id,
            agentType,
            success: false,
            response: null,
            latencyMs: 0,
            error: error instanceof Error ? error.message : "Unknown error",
          },
        ];
      });
      setRunningAgent(null);
    },
  });

  // 両方のエージェントでテスト実行
  const runBothTests = async (testCase: TestCase) => {
    setSelectedTest(testCase.id);
    
    // Strands
    setRunningAgent("strands");
    await runTest.mutateAsync({ testCase, agentType: "strands" }).catch(() => {});
    
    // LangChain
    setRunningAgent("langchain");
    await runTest.mutateAsync({ testCase, agentType: "langchain" }).catch(() => {});
  };

  const getResultForTest = (testId: string, agentType: AgentType) =>
    results.find((r) => r.testId === testId && r.agentType === agentType);

  return (
    <div className="space-y-8">
      {/* Service Info */}
      <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-white">{serviceName}</h2>
          <span className="px-3 py-1 bg-slate-700 rounded-full text-xs text-slate-300">
            /services/{serviceKey}
          </span>
        </div>
        <p className="text-slate-400 mb-6">{serviceDescription}</p>
        
        {/* Feature Comparison */}
        <div className="grid grid-cols-2 gap-6">
          <div className="bg-blue-900/20 border border-blue-700/50 rounded-lg p-4">
            <h3 className="text-sm font-medium text-blue-400 mb-3 flex items-center gap-2">
              <span className="w-2 h-2 bg-blue-400 rounded-full"></span>
              AgentCore (Strands Agents)
            </h3>
            <ul className="space-y-2">
              {strandsFeatures.map((feature, i) => (
                <li key={i} className="text-sm text-slate-300 flex items-center gap-2">
                  <span className="text-green-400">✓</span> {feature}
                </li>
              ))}
            </ul>
          </div>
          <div className="bg-purple-900/20 border border-purple-700/50 rounded-lg p-4">
            <h3 className="text-sm font-medium text-purple-400 mb-3 flex items-center gap-2">
              <span className="w-2 h-2 bg-purple-400 rounded-full"></span>
              LangChain / LangGraph
            </h3>
            <ul className="space-y-2">
              {langchainFeatures.map((feature, i) => (
                <li key={i} className="text-sm text-slate-300 flex items-center gap-2">
                  <span className="text-green-400">✓</span> {feature}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* Test Cases */}
      <div>
        <h3 className="text-lg font-semibold text-white mb-4">検証テストケース</h3>
        <div className="space-y-4">
          {testCases.map((test) => {
            const strandsResult = getResultForTest(test.id, "strands");
            const langchainResult = getResultForTest(test.id, "langchain");
            const isRunning = selectedTest === test.id && runTest.isPending;
            
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
                    <p className="text-xs text-slate-500 mt-1 font-mono">
                      {test.method} {test.endpoint}
                    </p>
                  </div>
                  <button
                    onClick={() => runBothTests(test)}
                    disabled={isRunning}
                    className={cn(
                      "px-4 py-2 rounded-lg text-sm font-medium transition-colors",
                      "bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white",
                      isRunning && "opacity-50 cursor-wait"
                    )}
                  >
                    {isRunning ? "実行中..." : "両方でテスト"}
                  </button>
                </div>

                {/* Results Comparison */}
                {(strandsResult || langchainResult) && (
                  <div className="grid grid-cols-2 gap-4 mt-4">
                    {/* Strands Result */}
                    <div className={cn(
                      "p-3 rounded-lg border",
                      strandsResult?.success 
                        ? "bg-green-900/20 border-green-700/50" 
                        : strandsResult?.error 
                        ? "bg-red-900/20 border-red-700/50"
                        : "bg-slate-800 border-slate-700"
                    )}>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-medium text-blue-400">Strands</span>
                        {strandsResult && (
                          <span className={cn(
                            "text-xs",
                            strandsResult.success ? "text-green-400" : "text-red-400"
                          )}>
                            {strandsResult.success ? `✓ ${strandsResult.latencyMs}ms` : "✗ 失敗"}
                          </span>
                        )}
                        {isRunning && runningAgent === "strands" && (
                          <span className="text-xs text-yellow-400">実行中...</span>
                        )}
                      </div>
                      {strandsResult && (
                        <pre className="text-xs text-slate-300 overflow-x-auto max-h-32 overflow-y-auto">
                          {strandsResult.success 
                            ? JSON.stringify(strandsResult.response, null, 2)
                            : strandsResult.error
                          }
                        </pre>
                      )}
                    </div>

                    {/* LangChain Result */}
                    <div className={cn(
                      "p-3 rounded-lg border",
                      langchainResult?.success 
                        ? "bg-green-900/20 border-green-700/50" 
                        : langchainResult?.error 
                        ? "bg-red-900/20 border-red-700/50"
                        : "bg-slate-800 border-slate-700"
                    )}>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-medium text-purple-400">LangChain</span>
                        {langchainResult && (
                          <span className={cn(
                            "text-xs",
                            langchainResult.success ? "text-green-400" : "text-red-400"
                          )}>
                            {langchainResult.success ? `✓ ${langchainResult.latencyMs}ms` : "✗ 失敗"}
                          </span>
                        )}
                        {isRunning && runningAgent === "langchain" && (
                          <span className="text-xs text-yellow-400">実行中...</span>
                        )}
                      </div>
                      {langchainResult && (
                        <pre className="text-xs text-slate-300 overflow-x-auto max-h-32 overflow-y-auto">
                          {langchainResult.success 
                            ? JSON.stringify(langchainResult.response, null, 2)
                            : langchainResult.error
                          }
                        </pre>
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
        <div>
          <h3 className="text-lg font-semibold text-white mb-4">実装例</h3>
          <div className="grid grid-cols-2 gap-4">
            {strandsExample && (
              <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
                <h4 className="text-sm font-medium text-blue-400 mb-3">Strands Agents</h4>
                <pre className="text-xs text-slate-300 overflow-x-auto p-3 bg-slate-900/50 rounded-lg max-h-64 overflow-y-auto">
                  <code>{strandsExample}</code>
                </pre>
              </div>
            )}
            {langchainExample && (
              <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
                <h4 className="text-sm font-medium text-purple-400 mb-3">LangChain</h4>
                <pre className="text-xs text-slate-300 overflow-x-auto p-3 bg-slate-900/50 rounded-lg max-h-64 overflow-y-auto">
                  <code>{langchainExample}</code>
                </pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
