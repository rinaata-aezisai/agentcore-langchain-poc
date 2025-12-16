#!/usr/bin/env python3
"""AgentCore vs LangChain ベンチマークスクリプト

本格的な比較検証を実行するベンチマーク。
各フレームワークの特徴を活かした実行を行い、
客観的な比較データを収集する。
"""

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

# プロジェクトパスを追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "backend" / "src"))
sys.path.insert(0, str(project_root / "poc" / "strands-agents"))
sys.path.insert(0, str(project_root / "poc" / "langchain"))


@dataclass
class TestCase:
    """テストケース定義"""
    id: str
    name: str
    prompt: str
    category: str
    use_tools: bool = False
    expected_tool: str | None = None
    description: str = ""


@dataclass
class BenchmarkResult:
    """ベンチマーク結果"""
    test_id: str
    test_name: str
    category: str
    strands_latency_ms: int
    langchain_latency_ms: int
    strands_success: bool
    langchain_success: bool
    strands_response: str = ""
    langchain_response: str = ""
    strands_tool_calls: int = 0
    langchain_tool_calls: int = 0
    strands_memory_size: int = 0
    langchain_memory_size: int = 0
    strands_features: list[str] = field(default_factory=list)
    langchain_features: list[str] = field(default_factory=list)
    latency_diff_ms: int = 0
    faster_framework: str = ""
    timestamp: str = ""


@dataclass
class BenchmarkSummary:
    """ベンチマーク集計結果"""
    total_tests: int
    strands_wins: int
    langchain_wins: int
    strands_avg_latency_ms: float
    langchain_avg_latency_ms: float
    strands_success_rate: float
    langchain_success_rate: float
    strands_total_tool_calls: int
    langchain_total_tool_calls: int
    by_category: dict[str, dict[str, Any]] = field(default_factory=dict)


# テストケース定義
TEST_CASES: list[TestCase] = [
    # 基本応答テスト
    TestCase(
        id="basic-greeting",
        name="基本挨拶",
        prompt="こんにちは！自己紹介をしてください。",
        category="basic",
        description="シンプルな応答テスト",
    ),
    TestCase(
        id="basic-qa",
        name="基本Q&A",
        prompt="Pythonのリスト内包表記について簡潔に説明してください。",
        category="basic",
        description="知識ベースの応答テスト",
    ),

    # メモリテスト
    TestCase(
        id="memory-context",
        name="コンテキスト保持",
        prompt="私の名前は田中太郎です。覚えておいてください。",
        category="memory",
        description="メモリ機能のテスト",
    ),
    TestCase(
        id="memory-recall",
        name="コンテキスト想起",
        prompt="私の名前を覚えていますか？",
        category="memory",
        description="メモリからの想起テスト",
    ),

    # ツール使用テスト
    TestCase(
        id="tool-weather",
        name="天気取得",
        prompt="東京の今日の天気を教えてください。",
        category="tool_use",
        use_tools=True,
        expected_tool="get_current_weather",
        description="天気ツール呼び出しテスト",
    ),
    TestCase(
        id="tool-calculate",
        name="計算",
        prompt="123 * 456 + 789 を計算してください。",
        category="tool_use",
        use_tools=True,
        expected_tool="calculate",
        description="計算ツール呼び出しテスト",
    ),
    TestCase(
        id="tool-search",
        name="ドキュメント検索",
        prompt="AIエージェントについてドキュメントを検索してください。",
        category="tool_use",
        use_tools=True,
        expected_tool="search_documents",
        description="検索ツール呼び出しテスト",
    ),
    TestCase(
        id="tool-multi",
        name="複数ツール",
        prompt="タスク「プロジェクト計画の作成」を作成し、その後ニューヨークの天気を確認してください。",
        category="multi_tool",
        use_tools=True,
        description="複数ツール連続呼び出しテスト",
    ),

    # 長文テスト
    TestCase(
        id="long-response",
        name="長文生成",
        prompt="AIエージェントの未来について、500文字程度のエッセイを書いてください。",
        category="long_form",
        description="長文生成能力テスト",
    ),

    # エラーハンドリングテスト
    TestCase(
        id="error-handling",
        name="エラーハンドリング",
        prompt="存在しない都市「ムーンシティ」の天気を教えてください。",
        category="error",
        use_tools=True,
        description="不正入力時のエラーハンドリング",
    ),
]


class Benchmark:
    """ベンチマーク実行クラス"""

    def __init__(self, iterations: int = 3):
        self.iterations = iterations
        self.results: list[BenchmarkResult] = []
        self._strands_adapter = None
        self._langchain_adapter = None

    def _get_strands_adapter(self):
        """Strandsアダプターを取得"""
        if self._strands_adapter is None:
            from strands_poc.adapter import create_strands_adapter
            self._strands_adapter = create_strands_adapter()
        return self._strands_adapter

    def _get_langchain_adapter(self):
        """LangChainアダプターを取得"""
        if self._langchain_adapter is None:
            from langchain_poc.adapter import create_langchain_adapter
            self._langchain_adapter = create_langchain_adapter()
        return self._langchain_adapter

    async def run_strands_test(self, test_case: TestCase) -> dict[str, Any]:
        """Strands Agentsでテスト実行"""
        adapter = self._get_strands_adapter()
        start_time = time.time()

        try:
            if test_case.use_tools:
                response = await adapter.execute_with_tools(
                    context=[],
                    instruction=test_case.prompt,
                )
            else:
                response = await adapter.execute(
                    context=[],
                    instruction=test_case.prompt,
                )

            latency_ms = int((time.time() - start_time) * 1000)

            return {
                "success": True,
                "latency_ms": latency_ms,
                "content": response.content[:500] if response.content else "",
                "tool_calls": len(response.tool_calls) if response.tool_calls else 0,
                "memory_size": response.metadata.get("memory_size", 0) if response.metadata else 0,
                "features": response.metadata.get("framework_features", []) if response.metadata else [],
                "error": None,
            }
        except Exception as e:
            return {
                "success": False,
                "latency_ms": int((time.time() - start_time) * 1000),
                "content": "",
                "tool_calls": 0,
                "memory_size": 0,
                "features": [],
                "error": str(e),
            }

    async def run_langchain_test(self, test_case: TestCase) -> dict[str, Any]:
        """LangChainでテスト実行"""
        adapter = self._get_langchain_adapter()
        start_time = time.time()

        try:
            if test_case.use_tools:
                response = await adapter.execute_with_tools(
                    context=[],
                    instruction=test_case.prompt,
                )
            else:
                response = await adapter.execute(
                    context=[],
                    instruction=test_case.prompt,
                )

            latency_ms = int((time.time() - start_time) * 1000)

            return {
                "success": True,
                "latency_ms": latency_ms,
                "content": response.content[:500] if response.content else "",
                "tool_calls": len(response.tool_calls) if response.tool_calls else 0,
                "memory_size": response.metadata.get("memory_size", 0) if response.metadata else 0,
                "features": response.metadata.get("framework_features", []) if response.metadata else [],
                "error": None,
            }
        except Exception as e:
            return {
                "success": False,
                "latency_ms": int((time.time() - start_time) * 1000),
                "content": "",
                "tool_calls": 0,
                "memory_size": 0,
                "features": [],
                "error": str(e),
            }

    async def run_test_case(self, test_case: TestCase) -> BenchmarkResult:
        """単一テストケースを実行"""
        print(f"  Running: {test_case.name} ({test_case.category})")

        # 複数回実行して平均を取る
        strands_latencies = []
        langchain_latencies = []
        strands_result = None
        langchain_result = None

        for i in range(self.iterations):
            # Strands実行
            strands_result = await self.run_strands_test(test_case)
            strands_latencies.append(strands_result["latency_ms"])

            # LangChain実行
            langchain_result = await self.run_langchain_test(test_case)
            langchain_latencies.append(langchain_result["latency_ms"])

        # 平均レイテンシを計算
        strands_avg = int(sum(strands_latencies) / len(strands_latencies))
        langchain_avg = int(sum(langchain_latencies) / len(langchain_latencies))

        # 結果を構築
        latency_diff = strands_avg - langchain_avg
        faster = "strands" if strands_avg < langchain_avg else "langchain"

        return BenchmarkResult(
            test_id=test_case.id,
            test_name=test_case.name,
            category=test_case.category,
            strands_latency_ms=strands_avg,
            langchain_latency_ms=langchain_avg,
            strands_success=strands_result["success"] if strands_result else False,
            langchain_success=langchain_result["success"] if langchain_result else False,
            strands_response=strands_result["content"] if strands_result else "",
            langchain_response=langchain_result["content"] if langchain_result else "",
            strands_tool_calls=strands_result["tool_calls"] if strands_result else 0,
            langchain_tool_calls=langchain_result["tool_calls"] if langchain_result else 0,
            strands_memory_size=strands_result["memory_size"] if strands_result else 0,
            langchain_memory_size=langchain_result["memory_size"] if langchain_result else 0,
            strands_features=strands_result["features"] if strands_result else [],
            langchain_features=langchain_result["features"] if langchain_result else [],
            latency_diff_ms=latency_diff,
            faster_framework=faster,
            timestamp=datetime.now(UTC).isoformat(),
        )

    async def run_all(self) -> BenchmarkSummary:
        """全テストケースを実行"""
        print(f"Starting benchmark with {len(TEST_CASES)} test cases, {self.iterations} iterations each")
        print("=" * 60)

        for test_case in TEST_CASES:
            result = await self.run_test_case(test_case)
            self.results.append(result)

            # 結果を表示
            status = "✓" if result.strands_success and result.langchain_success else "✗"
            print(f"    {status} Strands: {result.strands_latency_ms}ms, LangChain: {result.langchain_latency_ms}ms")
            print(f"      → Faster: {result.faster_framework} (diff: {abs(result.latency_diff_ms)}ms)")

        print("=" * 60)
        return self._calculate_summary()

    def _calculate_summary(self) -> BenchmarkSummary:
        """集計結果を計算"""
        total = len(self.results)
        strands_wins = sum(1 for r in self.results if r.faster_framework == "strands")
        langchain_wins = total - strands_wins

        strands_latencies = [r.strands_latency_ms for r in self.results if r.strands_success]
        langchain_latencies = [r.langchain_latency_ms for r in self.results if r.langchain_success]

        strands_avg = sum(strands_latencies) / len(strands_latencies) if strands_latencies else 0
        langchain_avg = sum(langchain_latencies) / len(langchain_latencies) if langchain_latencies else 0

        strands_success_rate = sum(1 for r in self.results if r.strands_success) / total * 100
        langchain_success_rate = sum(1 for r in self.results if r.langchain_success) / total * 100

        strands_tool_calls = sum(r.strands_tool_calls for r in self.results)
        langchain_tool_calls = sum(r.langchain_tool_calls for r in self.results)

        # カテゴリ別集計
        by_category: dict[str, dict[str, Any]] = {}
        for result in self.results:
            cat = result.category
            if cat not in by_category:
                by_category[cat] = {
                    "count": 0,
                    "strands_wins": 0,
                    "strands_avg_latency": [],
                    "langchain_avg_latency": [],
                }
            by_category[cat]["count"] += 1
            if result.faster_framework == "strands":
                by_category[cat]["strands_wins"] += 1
            by_category[cat]["strands_avg_latency"].append(result.strands_latency_ms)
            by_category[cat]["langchain_avg_latency"].append(result.langchain_latency_ms)

        # カテゴリ別平均を計算
        for cat, data in by_category.items():
            data["strands_avg_latency"] = (
                sum(data["strands_avg_latency"]) / len(data["strands_avg_latency"])
                if data["strands_avg_latency"] else 0
            )
            data["langchain_avg_latency"] = (
                sum(data["langchain_avg_latency"]) / len(data["langchain_avg_latency"])
                if data["langchain_avg_latency"] else 0
            )

        return BenchmarkSummary(
            total_tests=total,
            strands_wins=strands_wins,
            langchain_wins=langchain_wins,
            strands_avg_latency_ms=strands_avg,
            langchain_avg_latency_ms=langchain_avg,
            strands_success_rate=strands_success_rate,
            langchain_success_rate=langchain_success_rate,
            strands_total_tool_calls=strands_tool_calls,
            langchain_total_tool_calls=langchain_tool_calls,
            by_category=by_category,
        )

    def save_results(self, output_dir: Path) -> None:
        """結果を保存"""
        output_dir.mkdir(parents=True, exist_ok=True)

        # 詳細結果
        results_path = output_dir / "benchmark-results.json"
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "generated_at": datetime.now(UTC).isoformat(),
                    "iterations": self.iterations,
                    "results": [asdict(r) for r in self.results],
                    "summary": asdict(self._calculate_summary()),
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
        print(f"Results saved to: {results_path}")

        # Markdown レポート
        report_path = output_dir / "benchmark-report.md"
        self._generate_markdown_report(report_path)
        print(f"Report saved to: {report_path}")

    def _generate_markdown_report(self, path: Path) -> None:
        """Markdownレポートを生成"""
        summary = self._calculate_summary()

        report = f"""# AgentCore vs LangChain ベンチマーク結果

**生成日時**: {datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")}
**反復回数**: {self.iterations}

## サマリー

| 項目 | Strands Agents | LangChain |
|------|----------------|-----------|
| 勝利数 | {summary.strands_wins} | {summary.langchain_wins} |
| 平均レイテンシ | {summary.strands_avg_latency_ms:.0f}ms | {summary.langchain_avg_latency_ms:.0f}ms |
| 成功率 | {summary.strands_success_rate:.1f}% | {summary.langchain_success_rate:.1f}% |
| 総ツール呼出 | {summary.strands_total_tool_calls} | {summary.langchain_total_tool_calls} |

## カテゴリ別結果

| カテゴリ | テスト数 | Strands勝利 | Strands平均 | LangChain平均 |
|----------|----------|-------------|-------------|---------------|
"""

        for cat, data in summary.by_category.items():
            report += f"| {cat} | {data['count']} | {data['strands_wins']} | "
            report += f"{data['strands_avg_latency']:.0f}ms | {data['langchain_avg_latency']:.0f}ms |\n"

        report += """
## 詳細結果

| テスト名 | カテゴリ | Strands | LangChain | 勝者 | 差分 |
|----------|----------|---------|-----------|------|------|
"""

        for r in self.results:
            strands_status = "✓" if r.strands_success else "✗"
            langchain_status = "✓" if r.langchain_success else "✗"
            winner = "🔵" if r.faster_framework == "strands" else "🟣"

            report += f"| {r.test_name} | {r.category} | "
            report += f"{strands_status} {r.strands_latency_ms}ms | "
            report += f"{langchain_status} {r.langchain_latency_ms}ms | "
            report += f"{winner} {r.faster_framework} | {abs(r.latency_diff_ms)}ms |\n"

        report += """
## フレームワーク機能比較

### Strands Agents (AgentCore)
"""
        # 最初の結果からフィーチャーを取得
        if self.results and self.results[0].strands_features:
            for feature in self.results[0].strands_features:
                report += f"- {feature}\n"

        report += """
### LangChain + LangGraph
"""
        if self.results and self.results[0].langchain_features:
            for feature in self.results[0].langchain_features:
                report += f"- {feature}\n"

        report += """
---
*このレポートは `scripts/benchmark.py` により自動生成されました。*
"""

        with open(path, "w", encoding="utf-8") as f:
            f.write(report)


async def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="AgentCore vs LangChain ベンチマーク"
    )
    parser.add_argument(
        "--iterations", "-i",
        type=int,
        default=3,
        help="各テストの反復回数 (default: 3)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="docs/reports",
        help="出力ディレクトリ (default: docs/reports)"
    )
    args = parser.parse_args()

    # ベンチマーク実行
    benchmark = Benchmark(iterations=args.iterations)

    try:
        summary = await benchmark.run_all()

        # 結果を表示
        print("\n📊 Summary:")
        print(f"  Total tests: {summary.total_tests}")
        print(f"  Strands wins: {summary.strands_wins}")
        print(f"  LangChain wins: {summary.langchain_wins}")
        print(f"  Strands avg latency: {summary.strands_avg_latency_ms:.0f}ms")
        print(f"  LangChain avg latency: {summary.langchain_avg_latency_ms:.0f}ms")

        # 結果を保存
        output_dir = Path(args.output)
        benchmark.save_results(output_dir)

        print("\n✅ Benchmark completed!")

    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
