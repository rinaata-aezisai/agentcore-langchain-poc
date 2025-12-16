"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { sessionApi } from "@/shared/api/client";
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
  success: boolean;
  response: string;
  latencyMs: number;
  error?: string;
}

export function ServiceTest({
  serviceName,
  serviceDescription,
  testCases,
  strandsFeatures,
  langchainFeatures,
  strandsExample,
  langchainExample,
}: ServiceTestProps) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [results, setResults] = useState<TestResult[]>([]);
  const [selectedTest, setSelectedTest] = useState<string | null>(null);

  // セッション作成
  const createSession = useMutation({
    mutationFn: () => sessionApi.create({ user_id: "test-user" }),
    onSuccess: (data) => setSessionId(data.session_id),
  });

  // テスト実行
  const runTest = useMutation({
    mutationFn: async (testCase: TestCase) => {
      if (!sessionId) {
        const session = await sessionApi.create({ user_id: "test-user" });
        setSessionId(session.session_id);
        return sessionApi.sendMessage(session.session_id, { instruction: testCase.prompt });
      }
      return sessionApi.sendMessage(sessionId, { instruction: testCase.prompt });
    },
    onSuccess: (data, testCase) => {
      setResults((prev) => [
        ...prev,
        {
          testId: testCase.id,
          success: true,
          response: data.content,
          latencyMs: data.latency_ms,
        },
      ]);
    },
    onError: (error, testCase) => {
      setResults((prev) => [
        ...prev,
        {
          testId: testCase.id,
          success: false,
          response: "",
          latencyMs: 0,
          error: error instanceof Error ? error.message : "Unknown error",
        },
      ]);
    },
  });

  const getResultForTest = (testId: string) => results.find((r) => r.testId === testId);

  return (
    <div className="space-y-8">
      {/* Service Info */}
      <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
        <h2 className="text-xl font-semibold text-white mb-2">{serviceName}</h2>
        <p className="text-slate-400 mb-4">{serviceDescription}</p>
        
        {/* Feature Comparison */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <h3 className="text-sm font-medium text-blue-400 mb-2">Strands Agents</h3>
            <ul className="space-y-1">
              {strandsFeatures.map((feature, i) => (
                <li key={i} className="text-sm text-slate-300 flex items-center gap-2">
                  <span className="text-green-400">✓</span> {feature}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="text-sm font-medium text-purple-400 mb-2">LangChain</h3>
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

      {/* Test Cases */}
      <div>
        <h3 className="text-lg font-semibold text-white mb-4">検証テストケース</h3>
        <div className="space-y-3">
          {testCases.map((test) => {
            const result = getResultForTest(test.id);
            return (
              <div
                key={test.id}
                className={cn(
                  "bg-slate-800/50 border rounded-xl p-4 transition-all",
                  selectedTest === test.id ? "border-blue-500" : "border-slate-700"
                )}
              >
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h4 className="font-medium text-white">{test.name}</h4>
                    <p className="text-sm text-slate-400 mt-1">{test.expectedBehavior}</p>
                  </div>
                  <button
                    onClick={() => {
                      setSelectedTest(test.id);
                      runTest.mutate(test);
                    }}
                    disabled={runTest.isPending && selectedTest === test.id}
                    className={cn(
                      "px-4 py-2 rounded-lg text-sm font-medium transition-colors",
                      result?.success
                        ? "bg-green-600 text-white"
                        : result?.error
                        ? "bg-red-600 text-white"
                        : "bg-blue-600 hover:bg-blue-700 text-white",
                      runTest.isPending && selectedTest === test.id && "opacity-50"
                    )}
                  >
                    {runTest.isPending && selectedTest === test.id
                      ? "実行中..."
                      : result?.success
                      ? `✓ ${result.latencyMs}ms`
                      : result?.error
                      ? "✗ 失敗"
                      : "テスト実行"}
                  </button>
                </div>
                
                <div className="mt-3 p-3 bg-slate-900/50 rounded-lg">
                  <p className="text-xs text-slate-500 mb-1">Prompt:</p>
                  <p className="text-sm text-slate-300 font-mono">{test.prompt}</p>
                </div>

                {result && (
                  <div className={cn(
                    "mt-3 p-3 rounded-lg",
                    result.success ? "bg-green-900/20" : "bg-red-900/20"
                  )}>
                    <p className="text-xs text-slate-500 mb-1">Response:</p>
                    <p className="text-sm text-slate-300">
                      {result.success ? result.response : result.error}
                    </p>
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
              <h4 className="text-sm font-medium text-blue-400 mb-3">Strands 実装例</h4>
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

