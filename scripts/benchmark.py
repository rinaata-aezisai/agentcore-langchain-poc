#!/usr/bin/env python3
"""
PoC Benchmark Script - Strands Agents vs LangChain Comparison

両実装のパフォーマンス・品質を定量比較するベンチマークツール
"""

import asyncio
import json
import time
import statistics
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any
import httpx


@dataclass
class BenchmarkResult:
    """ベンチマーク結果"""
    
    agent_type: str
    test_name: str
    prompt: str
    response: str
    latency_ms: float
    success: bool
    error: str | None = None
    tool_calls: list[dict] | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class BenchmarkSummary:
    """ベンチマークサマリー"""
    
    agent_type: str
    total_tests: int
    successful_tests: int
    failed_tests: int
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    success_rate: float


class AgentBenchmark:
    """エージェントベンチマーク実行クラス"""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.results: list[BenchmarkResult] = []
        
    async def run_single_test(
        self,
        session_id: str,
        prompt: str,
        test_name: str,
        agent_type: str,
    ) -> BenchmarkResult:
        """単一テストを実行"""
        async with httpx.AsyncClient() as client:
            start_time = time.time()
            
            try:
                response = await client.post(
                    f"{self.api_url}/sessions/{session_id}/messages",
                    json={"instruction": prompt},
                    timeout=60.0,
                )
                response.raise_for_status()
                data = response.json()
                latency_ms = (time.time() - start_time) * 1000
                
                return BenchmarkResult(
                    agent_type=agent_type,
                    test_name=test_name,
                    prompt=prompt,
                    response=data.get("content", ""),
                    latency_ms=latency_ms,
                    success=True,
                    tool_calls=data.get("tool_calls"),
                    metadata=data.get("metadata", {}),
                )
                
            except Exception as e:
                latency_ms = (time.time() - start_time) * 1000
                return BenchmarkResult(
                    agent_type=agent_type,
                    test_name=test_name,
                    prompt=prompt,
                    response="",
                    latency_ms=latency_ms,
                    success=False,
                    error=str(e),
                )
    
    async def create_session(self) -> str:
        """セッションを作成"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/sessions",
                json={"user_id": "benchmark-user"},
            )
            response.raise_for_status()
            return response.json()["session_id"]
    
    async def get_agent_info(self) -> dict:
        """エージェント情報を取得"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/agents/info")
            response.raise_for_status()
            return response.json()
    
    def calculate_summary(self, results: list[BenchmarkResult]) -> BenchmarkSummary:
        """サマリーを計算"""
        if not results:
            return None
            
        agent_type = results[0].agent_type
        latencies = [r.latency_ms for r in results if r.success]
        successful = [r for r in results if r.success]
        
        if not latencies:
            latencies = [0]
            
        sorted_latencies = sorted(latencies)
        p50_idx = int(len(sorted_latencies) * 0.5)
        p95_idx = int(len(sorted_latencies) * 0.95)
        
        return BenchmarkSummary(
            agent_type=agent_type,
            total_tests=len(results),
            successful_tests=len(successful),
            failed_tests=len(results) - len(successful),
            avg_latency_ms=statistics.mean(latencies),
            min_latency_ms=min(latencies),
            max_latency_ms=max(latencies),
            p50_latency_ms=sorted_latencies[p50_idx] if p50_idx < len(sorted_latencies) else 0,
            p95_latency_ms=sorted_latencies[p95_idx] if p95_idx < len(sorted_latencies) else 0,
            success_rate=len(successful) / len(results) * 100 if results else 0,
        )


# ===========================================
# Test Cases
# ===========================================

TEST_CASES = [
    {
        "name": "simple_greeting",
        "prompt": "こんにちは。自己紹介をしてください。",
        "category": "basic",
    },
    {
        "name": "weather_query",
        "prompt": "東京の今日の天気を教えてください。",
        "category": "tool_use",
    },
    {
        "name": "calculation",
        "prompt": "125 * 48 + 3256 の計算結果を教えてください。",
        "category": "tool_use",
    },
    {
        "name": "document_search",
        "prompt": "AIエージェントに関するドキュメントを検索してください。",
        "category": "tool_use",
    },
    {
        "name": "complex_reasoning",
        "prompt": "クリーンアーキテクチャとヘキサゴナルアーキテクチャの違いを説明してください。",
        "category": "reasoning",
    },
    {
        "name": "multi_step_task",
        "prompt": "「プロジェクト計画の作成」というタスクを作成し、その後ニューヨークの天気を確認してください。",
        "category": "multi_tool",
    },
    {
        "name": "code_explanation",
        "prompt": "Pythonでasync/awaitを使う利点を3つ挙げて説明してください。",
        "category": "reasoning",
    },
    {
        "name": "japanese_understanding",
        "prompt": "「七転び八起き」ということわざの意味と、ビジネスでの活用例を教えてください。",
        "category": "language",
    },
]


async def run_benchmark(api_url: str = "http://localhost:8000", iterations: int = 1):
    """ベンチマークを実行"""
    benchmark = AgentBenchmark(api_url)
    
    print("=" * 60)
    print("AgentCore vs LangChain Benchmark")
    print("=" * 60)
    
    # エージェント情報取得
    try:
        agent_info = await benchmark.get_agent_info()
        print(f"\nAgent Type: {agent_info['agent_type']}")
        print(f"Model: {agent_info['model_id']}")
        print(f"Capabilities: {', '.join(agent_info['capabilities'])}")
    except Exception as e:
        print(f"Warning: Could not get agent info: {e}")
        agent_info = {"agent_type": "unknown"}
    
    print(f"\nRunning {len(TEST_CASES)} test cases x {iterations} iterations...")
    print("-" * 60)
    
    all_results = []
    
    for iteration in range(iterations):
        print(f"\n[Iteration {iteration + 1}/{iterations}]")
        
        # セッション作成
        session_id = await benchmark.create_session()
        print(f"Session: {session_id[:8]}...")
        
        for test_case in TEST_CASES:
            result = await benchmark.run_single_test(
                session_id=session_id,
                prompt=test_case["prompt"],
                test_name=test_case["name"],
                agent_type=agent_info.get("agent_type", "unknown"),
            )
            all_results.append(result)
            
            status = "✅" if result.success else "❌"
            print(f"  {status} {test_case['name']}: {result.latency_ms:.0f}ms")
    
    # サマリー計算
    summary = benchmark.calculate_summary(all_results)
    
    print("\n" + "=" * 60)
    print("BENCHMARK SUMMARY")
    print("=" * 60)
    print(f"Agent Type: {summary.agent_type}")
    print(f"Total Tests: {summary.total_tests}")
    print(f"Success Rate: {summary.success_rate:.1f}%")
    print(f"Avg Latency: {summary.avg_latency_ms:.0f}ms")
    print(f"P50 Latency: {summary.p50_latency_ms:.0f}ms")
    print(f"P95 Latency: {summary.p95_latency_ms:.0f}ms")
    print(f"Min Latency: {summary.min_latency_ms:.0f}ms")
    print(f"Max Latency: {summary.max_latency_ms:.0f}ms")
    
    # 結果をJSONで保存
    output_dir = Path("benchmark_results")
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"benchmark_{summary.agent_type}_{timestamp}.json"
    
    output_data = {
        "summary": asdict(summary),
        "results": [asdict(r) for r in all_results],
        "test_cases": TEST_CASES,
        "timestamp": timestamp,
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\nResults saved to: {output_file}")
    
    return summary, all_results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AgentCore vs LangChain Benchmark")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API URL")
    parser.add_argument("--iterations", type=int, default=1, help="Number of iterations")
    
    args = parser.parse_args()
    
    asyncio.run(run_benchmark(args.api_url, args.iterations))

