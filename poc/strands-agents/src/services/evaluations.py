"""Strands Evaluations Adapter

AgentCore Evaluations サービスの実装。
エージェント評価、ベンチマーク、品質測定。
"""

import asyncio
import time
from datetime import datetime
from typing import Any
import uuid

import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent.parent.parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_path))

from application.ports.evaluations_port import (
    EvaluationsPort,
    EvaluationConfig,
    EvaluationType,
    EvaluationStatus,
    EvaluationCase,
    EvaluationScore,
    EvaluationResult,
    EvaluationSummary,
)


class StrandsEvaluationsAdapter(EvaluationsPort):
    """Strands Agents Evaluations アダプター
    
    AgentCore Evaluationsの機能:
    - 自動評価
    - LLM-as-a-Judge
    - ベンチマーク実行
    - 品質メトリクス
    """

    def __init__(self):
        self._config: EvaluationConfig | None = None
        self._datasets: dict[str, list[EvaluationCase]] = {}
        self._results: dict[str, EvaluationResult] = {}

    async def initialize(self, config: EvaluationConfig) -> bool:
        """評価サービスを初期化"""
        self._config = config
        return True

    async def create_dataset(
        self,
        name: str,
        cases: list[EvaluationCase],
    ) -> str:
        """評価データセットを作成"""
        dataset_id = str(uuid.uuid4())
        self._datasets[dataset_id] = cases
        return dataset_id

    async def add_case(
        self,
        dataset_id: str,
        case: EvaluationCase,
    ) -> bool:
        """ケースを追加"""
        if dataset_id not in self._datasets:
            return False
        self._datasets[dataset_id].append(case)
        return True

    async def evaluate_single(
        self,
        case: EvaluationCase,
        evaluation_types: list[EvaluationType] | None = None,
    ) -> EvaluationResult:
        """単一ケースを評価"""
        start_time = time.time()
        types = evaluation_types or (
            self._config.evaluation_types if self._config else [EvaluationType.ACCURACY]
        )
        
        scores = []
        for eval_type in types:
            score = await self._evaluate_by_type(case, eval_type)
            scores.append(score)
        
        result_id = str(uuid.uuid4())
        result = EvaluationResult(
            result_id=result_id,
            case=case,
            scores=scores,
            status=EvaluationStatus.COMPLETED,
            execution_time_ms=int((time.time() - start_time) * 1000),
        )
        
        self._results[result_id] = result
        return result

    async def evaluate_dataset(
        self,
        dataset_id: str,
        evaluation_types: list[EvaluationType] | None = None,
    ) -> EvaluationSummary:
        """データセットを評価"""
        cases = self._datasets.get(dataset_id, [])
        if not cases:
            raise ValueError(f"Dataset not found: {dataset_id}")
        
        start_time = time.time()
        all_results = []
        
        for case in cases:
            result = await self.evaluate_single(case, evaluation_types)
            all_results.append(result)
        
        # サマリーを計算
        passed = sum(1 for r in all_results if self._is_passed(r))
        failed = len(all_results) - passed
        
        # タイプごとの平均スコアを計算
        average_scores = {}
        for eval_type in (evaluation_types or [EvaluationType.ACCURACY]):
            type_scores = []
            for r in all_results:
                for s in r.scores:
                    if s.evaluation_type == eval_type:
                        type_scores.append(s.score)
            if type_scores:
                average_scores[eval_type.value] = sum(type_scores) / len(type_scores)
        
        return EvaluationSummary(
            total_cases=len(cases),
            passed_cases=passed,
            failed_cases=failed,
            average_scores=average_scores,
            execution_time_ms=int((time.time() - start_time) * 1000),
        )

    async def evaluate_with_llm_judge(
        self,
        case: EvaluationCase,
        criteria: str,
        rubric: str | None = None,
    ) -> EvaluationResult:
        """LLM-as-a-Judgeで評価"""
        start_time = time.time()
        
        # LLMによる評価（簡易実装）
        # 本番では実際にLLMを呼び出してスコアリング
        score = await self._llm_judge_evaluate(case, criteria, rubric)
        
        result_id = str(uuid.uuid4())
        result = EvaluationResult(
            result_id=result_id,
            case=case,
            scores=[
                EvaluationScore(
                    evaluation_type=EvaluationType.CUSTOM,
                    score=score,
                    details=f"LLM Judge評価: {criteria}",
                    metadata={"criteria": criteria, "rubric": rubric},
                )
            ],
            status=EvaluationStatus.COMPLETED,
            execution_time_ms=int((time.time() - start_time) * 1000),
        )
        
        self._results[result_id] = result
        return result

    async def get_result(self, result_id: str) -> EvaluationResult | None:
        """評価結果を取得"""
        return self._results.get(result_id)

    async def list_results(
        self,
        dataset_id: str | None = None,
        limit: int = 100,
    ) -> list[EvaluationResult]:
        """評価結果一覧を取得"""
        results = list(self._results.values())
        results.sort(key=lambda r: r.created_at, reverse=True)
        return results[:limit]

    async def get_summary(
        self,
        dataset_id: str,
    ) -> EvaluationSummary | None:
        """サマリーを取得"""
        # キャッシュされたサマリーがあれば返す
        # なければ再計算
        return await self.evaluate_dataset(dataset_id)

    async def compare_runs(
        self,
        run_ids: list[str],
    ) -> dict[str, Any]:
        """複数ランを比較"""
        comparison = {}
        
        for run_id in run_ids:
            result = self._results.get(run_id)
            if result:
                comparison[run_id] = {
                    "scores": {s.evaluation_type.value: s.score for s in result.scores},
                    "status": result.status.value,
                    "execution_time_ms": result.execution_time_ms,
                }
        
        return comparison

    async def _evaluate_by_type(
        self,
        case: EvaluationCase,
        eval_type: EvaluationType,
    ) -> EvaluationScore:
        """タイプ別評価を実行"""
        score = 0.0
        details = ""
        
        if eval_type == EvaluationType.ACCURACY:
            score, details = await self._evaluate_accuracy(case)
        elif eval_type == EvaluationType.RELEVANCE:
            score, details = await self._evaluate_relevance(case)
        elif eval_type == EvaluationType.COHERENCE:
            score, details = await self._evaluate_coherence(case)
        elif eval_type == EvaluationType.LATENCY:
            score, details = await self._evaluate_latency(case)
        elif eval_type == EvaluationType.COST:
            score, details = await self._evaluate_cost(case)
        else:
            score = 0.5
            details = "Custom evaluation not implemented"
        
        return EvaluationScore(
            evaluation_type=eval_type,
            score=score,
            details=details,
        )

    async def _evaluate_accuracy(self, case: EvaluationCase) -> tuple[float, str]:
        """正確性を評価"""
        if case.expected_output and case.actual_output:
            # 簡易的な文字列比較
            expected = str(case.expected_output).lower()
            actual = str(case.actual_output).lower()
            
            if expected == actual:
                return 1.0, "完全一致"
            elif expected in actual or actual in expected:
                return 0.7, "部分一致"
            else:
                return 0.3, "不一致"
        return 0.5, "期待値なし"

    async def _evaluate_relevance(self, case: EvaluationCase) -> tuple[float, str]:
        """関連性を評価"""
        # 簡易実装: キーワードベースの関連性
        return 0.8, "関連性評価（簡易）"

    async def _evaluate_coherence(self, case: EvaluationCase) -> tuple[float, str]:
        """一貫性を評価"""
        return 0.75, "一貫性評価（簡易）"

    async def _evaluate_latency(self, case: EvaluationCase) -> tuple[float, str]:
        """レイテンシを評価"""
        # レイテンシがコンテキストにあれば使用
        latency = case.context.get("latency_ms", 1000)
        if latency < 500:
            return 1.0, f"高速: {latency}ms"
        elif latency < 2000:
            return 0.7, f"標準: {latency}ms"
        else:
            return 0.3, f"低速: {latency}ms"

    async def _evaluate_cost(self, case: EvaluationCase) -> tuple[float, str]:
        """コストを評価"""
        cost = case.context.get("cost_usd", 0.01)
        if cost < 0.001:
            return 1.0, f"低コスト: ${cost:.4f}"
        elif cost < 0.01:
            return 0.7, f"標準コスト: ${cost:.4f}"
        else:
            return 0.3, f"高コスト: ${cost:.4f}"

    async def _llm_judge_evaluate(
        self,
        case: EvaluationCase,
        criteria: str,
        rubric: str | None,
    ) -> float:
        """LLMによる評価（簡易実装）"""
        # 本番ではStrands Agentを使って評価
        return 0.8

    def _is_passed(self, result: EvaluationResult) -> bool:
        """合格判定"""
        thresholds = self._config.threshold_scores if self._config else {}
        default_threshold = 0.5
        
        for score in result.scores:
            threshold = thresholds.get(score.evaluation_type.value, default_threshold)
            if score.score < threshold:
                return False
        return True


def create_strands_evaluations() -> StrandsEvaluationsAdapter:
    """ファクトリ関数"""
    return StrandsEvaluationsAdapter()

