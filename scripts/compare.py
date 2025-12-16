#!/usr/bin/env python3
"""
Comparison Script - Strands Agents vs LangChain Results Analysis

両実装のベンチマーク結果を比較分析するスクリプト
"""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ComparisonMetric:
    """比較メトリクス"""
    metric_name: str
    strands_value: float
    langchain_value: float
    difference: float
    winner: str
    notes: str = ""


def load_benchmark_results(results_dir: Path = Path("benchmark_results")) -> dict[str, dict]:
    """ベンチマーク結果をロード"""
    results = {"strands": None, "langchain": None}

    for file in sorted(results_dir.glob("*.json"), reverse=True):
        with open(file, encoding="utf-8") as f:
            data = json.load(f)
            agent_type = data["summary"]["agent_type"]

            if agent_type in results and results[agent_type] is None:
                results[agent_type] = data

    return results


def compare_metrics(strands_data: dict, langchain_data: dict) -> list[ComparisonMetric]:
    """メトリクスを比較"""
    metrics = []

    s = strands_data["summary"]
    lc = langchain_data["summary"]

    # レイテンシ比較
    metrics.append(ComparisonMetric(
        metric_name="Average Latency (ms)",
        strands_value=s["avg_latency_ms"],
        langchain_value=lc["avg_latency_ms"],
        difference=s["avg_latency_ms"] - lc["avg_latency_ms"],
        winner="Strands" if s["avg_latency_ms"] < lc["avg_latency_ms"] else "LangChain",
        notes="Lower is better",
    ))

    metrics.append(ComparisonMetric(
        metric_name="P50 Latency (ms)",
        strands_value=s["p50_latency_ms"],
        langchain_value=lc["p50_latency_ms"],
        difference=s["p50_latency_ms"] - lc["p50_latency_ms"],
        winner="Strands" if s["p50_latency_ms"] < lc["p50_latency_ms"] else "LangChain",
        notes="Lower is better",
    ))

    metrics.append(ComparisonMetric(
        metric_name="P95 Latency (ms)",
        strands_value=s["p95_latency_ms"],
        langchain_value=lc["p95_latency_ms"],
        difference=s["p95_latency_ms"] - lc["p95_latency_ms"],
        winner="Strands" if s["p95_latency_ms"] < lc["p95_latency_ms"] else "LangChain",
        notes="Lower is better",
    ))

    # 成功率比較
    metrics.append(ComparisonMetric(
        metric_name="Success Rate (%)",
        strands_value=s["success_rate"],
        langchain_value=lc["success_rate"],
        difference=s["success_rate"] - lc["success_rate"],
        winner="Strands" if s["success_rate"] > lc["success_rate"] else "LangChain",
        notes="Higher is better",
    ))

    return metrics


def print_comparison_report(metrics: list[ComparisonMetric]):
    """比較レポートを出力"""
    print("\n" + "=" * 80)
    print("STRANDS AGENTS vs LANGCHAIN COMPARISON REPORT")
    print("=" * 80)

    header = f"{'Metric':<25} {'Strands':<15} {'LangChain':<15} {'Diff':<15} {'Winner':<10}"
    print(f"\n{header}")
    print("-" * 80)

    strands_wins = 0
    langchain_wins = 0

    for m in metrics:
        diff_str = f"{m.difference:+.1f}"
        row = (
            f"{m.metric_name:<25} {m.strands_value:<15.1f} "
            f"{m.langchain_value:<15.1f} {diff_str:<15} {m.winner:<10}"
        )
        print(row)

        if m.winner == "Strands":
            strands_wins += 1
        else:
            langchain_wins += 1

    print("-" * 80)
    print(f"\n📊 Overall Score: Strands {strands_wins} - {langchain_wins} LangChain")

    if strands_wins > langchain_wins:
        print("\n🏆 Winner: Strands Agents")
        print("   Recommendation: Use Strands Agents for AWS-native applications")
    elif langchain_wins > strands_wins:
        print("\n🏆 Winner: LangChain + LangGraph")
        print("   Recommendation: Use LangChain for complex workflows")
    else:
        print("\n🤝 Tie: Both implementations perform similarly")
        print("   Recommendation: Choose based on ecosystem and team expertise")


def generate_markdown_report(
    metrics: list[ComparisonMetric],
    strands_data: dict,
    langchain_data: dict,
) -> str:
    """Markdownレポートを生成"""
    report = """# AgentCore vs LangChain Comparison Report

## Executive Summary

This report compares AWS Bedrock AgentCore (Strands Agents) and LangChain.

## Performance Metrics

| Metric | Strands Agents | LangChain | Difference | Winner |
|--------|---------------|-----------|------------|--------|
"""

    for m in metrics:
        report += (
            f"| {m.metric_name} | {m.strands_value:.1f} | "
            f"{m.langchain_value:.1f} | {m.difference:+.1f} | {m.winner} |\n"
        )

    strands_wins = sum(1 for m in metrics if m.winner == "Strands")
    langchain_wins = len(metrics) - strands_wins

    report += f"""
## Test Results Summary

### Strands Agents
- Total Tests: {strands_data['summary']['total_tests']}
- Success Rate: {strands_data['summary']['success_rate']:.1f}%

### LangChain + LangGraph
- Total Tests: {langchain_data['summary']['total_tests']}
- Success Rate: {langchain_data['summary']['success_rate']:.1f}%

## Recommendation

"""

    if strands_wins > langchain_wins:
        report += """**Recommended: Strands Agents (AWS Bedrock AgentCore)**

Best for:
- AWS-native deployments
- Low-latency requirements
- Simple agent workflows
- Cost-sensitive applications
"""
    else:
        report += """**Recommended: LangChain + LangGraph**

Best for:
- Complex multi-agent workflows
- LangSmith/LangFuse observability needs
- Multi-provider support requirements
- Advanced state management
"""

    return report


def main():
    """メイン処理"""
    results_dir = Path("benchmark_results")

    if not results_dir.exists():
        print("Error: No benchmark results found.")
        print("Run benchmark.py first for both Strands and LangChain implementations.")
        return

    results = load_benchmark_results(results_dir)

    if not results["strands"]:
        print("Error: No Strands Agents benchmark results found.")
        print("Run: AGENT_TYPE=strands python scripts/benchmark.py")
        return

    if not results["langchain"]:
        print("Error: No LangChain benchmark results found.")
        print("Run: AGENT_TYPE=langchain python scripts/benchmark.py")
        return

    # 比較実行
    metrics = compare_metrics(results["strands"], results["langchain"])
    print_comparison_report(metrics)

    # Markdownレポート生成
    report = generate_markdown_report(metrics, results["strands"], results["langchain"])
    report_file = results_dir / "comparison_report.md"

    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n📄 Markdown report saved to: {report_file}")


if __name__ == "__main__":
    main()
