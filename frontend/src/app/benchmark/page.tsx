"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { sessionApi } from "@/shared/api/client";
import { cn } from "@/shared/lib/utils";

const BENCHMARK_TESTS = [
  { id: "greeting", name: "基本挨拶", prompt: "こんにちは。自己紹介をしてください。" },
  { id: "weather", name: "天気照会", prompt: "東京の今日の天気を教えてください。" },
  { id: "calculation", name: "計算", prompt: "125 * 48 + 3256 の計算結果を教えてください。" },
  { id: "search", name: "検索", prompt: "AIエージェントに関するドキュメントを検索してください。" },
  { id: "reasoning", name: "推論", prompt: "クリーンアーキテクチャとヘキサゴナルアーキテクチャの違いを説明してください。" },
  { id: "multi_tool", name: "複数ツール", prompt: "タスクを作成し、その後ニューヨークの天気を確認してください。" },
  { id: "code", name: "コード説明", prompt: "Pythonでasync/awaitを使う利点を3つ挙げて説明してください。" },
  { id: "japanese", name: "日本語理解", prompt: "「七転び八起き」ということわざの意味と、ビジネスでの活用例を教えてください。" },
];

interface BenchmarkResult {
  testId: string;
  latencyMs: number;
  success: boolean;
  response?: string;
  error?: string;
}

export default function BenchmarkPage() {
  const [results, setResults] = useState<BenchmarkResult[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [currentTest, setCurrentTest] = useState<string | null>(null);

  const runBenchmark = async () => {
    setIsRunning(true);
    setResults([]);

    try {
      const session = await sessionApi.create({ user_id: "benchmark" });

      for (const test of BENCHMARK_TESTS) {
        setCurrentTest(test.id);
        const startTime = Date.now();

        try {
          const response = await sessionApi.sendMessage(session.session_id, {
            instruction: test.prompt,
          });

          setResults((prev) => [
            ...prev,
            {
              testId: test.id,
              latencyMs: Date.now() - startTime,
              success: true,
              response: response.content,
            },
          ]);
        } catch (error) {
          setResults((prev) => [
            ...prev,
            {
              testId: test.id,
              latencyMs: Date.now() - startTime,
              success: false,
              error: error instanceof Error ? error.message : "Unknown error",
            },
          ]);
        }

        // 間隔を空ける
        await new Promise((resolve) => setTimeout(resolve, 500));
      }
    } finally {
      setIsRunning(false);
      setCurrentTest(null);
    }
  };

  const getResultForTest = (testId: string) =>
    results.find((r) => r.testId === testId);

  const completedTests = results.filter((r) => r.success).length;
  const avgLatency =
    results.length > 0
      ? Math.round(
          results.filter((r) => r.success).reduce((acc, r) => acc + r.latencyMs, 0) /
            completedTests || 0
        )
      : 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white mb-2">ベンチマーク</h1>
        <p className="text-slate-400">
          パフォーマンス測定 - 8テストケースの実行時間を計測
        </p>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-4 mb-8">
        <button
          onClick={runBenchmark}
          disabled={isRunning}
          className={cn(
            "px-6 py-3 rounded-lg font-medium transition-colors",
            isRunning
              ? "bg-slate-700 text-slate-400 cursor-not-allowed"
              : "bg-blue-600 hover:bg-blue-700 text-white"
          )}
        >
          {isRunning ? "実行中..." : "ベンチマーク実行"}
        </button>

        {results.length > 0 && (
          <div className="flex items-center gap-6 text-sm">
            <div>
              <span className="text-slate-400">完了: </span>
              <span className="text-white font-medium">
                {completedTests}/{BENCHMARK_TESTS.length}
              </span>
            </div>
            <div>
              <span className="text-slate-400">平均レイテンシ: </span>
              <span className="text-white font-medium">{avgLatency}ms</span>
            </div>
          </div>
        )}
      </div>

      {/* Results */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {BENCHMARK_TESTS.map((test) => {
          const result = getResultForTest(test.id);
          const isCurrent = currentTest === test.id;

          return (
            <div
              key={test.id}
              className={cn(
                "bg-slate-800/50 border rounded-xl p-4 transition-all",
                isCurrent
                  ? "border-blue-500 animate-pulse"
                  : result?.success
                  ? "border-green-500/50"
                  : result?.error
                  ? "border-red-500/50"
                  : "border-slate-700"
              )}
            >
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-medium text-white">{test.name}</h3>
                {result && (
                  <span
                    className={cn(
                      "px-2 py-1 rounded text-xs font-medium",
                      result.success
                        ? "bg-green-500/20 text-green-400"
                        : "bg-red-500/20 text-red-400"
                    )}
                  >
                    {result.success ? `${result.latencyMs}ms` : "Failed"}
                  </span>
                )}
                {isCurrent && (
                  <span className="px-2 py-1 rounded text-xs font-medium bg-blue-500/20 text-blue-400">
                    実行中...
                  </span>
                )}
              </div>
              <p className="text-sm text-slate-400 truncate">{test.prompt}</p>

              {result?.response && (
                <div className="mt-3 p-2 bg-slate-900/50 rounded text-xs text-slate-300 max-h-20 overflow-y-auto">
                  {result.response.slice(0, 200)}...
                </div>
              )}
              {result?.error && (
                <div className="mt-3 p-2 bg-red-900/20 rounded text-xs text-red-400">
                  {result.error}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Summary Chart (Placeholder) */}
      {results.length === BENCHMARK_TESTS.length && (
        <div className="mt-8 bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4">結果サマリー</h3>
          <div className="grid grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-3xl font-bold text-white">{completedTests}</div>
              <div className="text-sm text-slate-400">成功</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-white">
                {BENCHMARK_TESTS.length - completedTests}
              </div>
              <div className="text-sm text-slate-400">失敗</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-white">{avgLatency}ms</div>
              <div className="text-sm text-slate-400">平均</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-white">
                {Math.round((completedTests / BENCHMARK_TESTS.length) * 100)}%
              </div>
              <div className="text-sm text-slate-400">成功率</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


