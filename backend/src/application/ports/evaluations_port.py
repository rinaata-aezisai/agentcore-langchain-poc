"""Evaluations Port - Evaluation Service Interface

AgentCore Evaluations / LangSmith Evaluations に対応。
エージェント評価、ベンチマーク、品質測定。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime
from enum import Enum


class EvaluationType(str, Enum):
    """評価タイプ"""
    ACCURACY = "accuracy"  # 正確性
    RELEVANCE = "relevance"  # 関連性
    COHERENCE = "coherence"  # 一貫性
    TOXICITY = "toxicity"  # 有害性
    LATENCY = "latency"  # レイテンシ
    COST = "cost"  # コスト
    CUSTOM = "custom"  # カスタム


class EvaluationStatus(str, Enum):
    """評価ステータス"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class EvaluationConfig:
    """評価設定"""
    evaluation_types: list[EvaluationType] = field(
        default_factory=lambda: [EvaluationType.ACCURACY, EvaluationType.RELEVANCE]
    )
    model_as_judge: str | None = None  # LLM-as-a-Judge用モデル
    threshold_scores: dict[str, float] = field(default_factory=dict)
    num_samples: int = 100
    parallel_workers: int = 4
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationCase:
    """評価ケース"""
    case_id: str
    input_data: Any
    expected_output: Any | None = None
    actual_output: Any | None = None
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationScore:
    """評価スコア"""
    evaluation_type: EvaluationType
    score: float  # 0.0 - 1.0
    details: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationResult:
    """評価結果"""
    result_id: str
    case: EvaluationCase
    scores: list[EvaluationScore]
    status: EvaluationStatus
    execution_time_ms: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationSummary:
    """評価サマリー"""
    total_cases: int
    passed_cases: int
    failed_cases: int
    average_scores: dict[str, float]
    execution_time_ms: int
    metadata: dict[str, Any] = field(default_factory=dict)


class EvaluationsPort(ABC):
    """Evaluations Port - 評価

    Strands Agents: AgentCore Evaluations
    LangChain: LangSmith Evaluations / RAGAS
    """

    @abstractmethod
    async def initialize(self, config: EvaluationConfig) -> bool:
        """評価サービスを初期化"""
        ...

    @abstractmethod
    async def create_dataset(
        self,
        name: str,
        cases: list[EvaluationCase],
    ) -> str:
        """評価データセットを作成"""
        ...

    @abstractmethod
    async def add_case(
        self,
        dataset_id: str,
        case: EvaluationCase,
    ) -> bool:
        """ケースを追加"""
        ...

    @abstractmethod
    async def evaluate_single(
        self,
        case: EvaluationCase,
        evaluation_types: list[EvaluationType] | None = None,
    ) -> EvaluationResult:
        """単一ケースを評価"""
        ...

    @abstractmethod
    async def evaluate_dataset(
        self,
        dataset_id: str,
        evaluation_types: list[EvaluationType] | None = None,
    ) -> EvaluationSummary:
        """データセットを評価"""
        ...

    @abstractmethod
    async def evaluate_with_llm_judge(
        self,
        case: EvaluationCase,
        criteria: str,
        rubric: str | None = None,
    ) -> EvaluationResult:
        """LLM-as-a-Judgeで評価"""
        ...

    @abstractmethod
    async def get_result(self, result_id: str) -> EvaluationResult | None:
        """評価結果を取得"""
        ...

    @abstractmethod
    async def list_results(
        self,
        dataset_id: str | None = None,
        limit: int = 100,
    ) -> list[EvaluationResult]:
        """評価結果一覧を取得"""
        ...

    @abstractmethod
    async def get_summary(
        self,
        dataset_id: str,
    ) -> EvaluationSummary | None:
        """サマリーを取得"""
        ...

    @abstractmethod
    async def compare_runs(
        self,
        run_ids: list[str],
    ) -> dict[str, Any]:
        """複数ランを比較"""
        ...

