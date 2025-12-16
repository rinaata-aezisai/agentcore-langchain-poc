"""Evaluations Service Router

評価サービスAPIエンドポイント。
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any
from enum import Enum

router = APIRouter(prefix="/evaluations", tags=["Evaluations"])


class AgentType(str, Enum):
    STRANDS = "strands"
    LANGCHAIN = "langchain"


class EvaluationType(str, Enum):
    ACCURACY = "accuracy"
    RELEVANCE = "relevance"
    COHERENCE = "coherence"
    TOXICITY = "toxicity"
    LATENCY = "latency"
    COST = "cost"


class EvaluationConfigRequest(BaseModel):
    agent_type: AgentType = AgentType.STRANDS
    evaluation_types: list[EvaluationType] = [EvaluationType.ACCURACY, EvaluationType.RELEVANCE]
    model_as_judge: str | None = None


class EvaluationCase(BaseModel):
    case_id: str
    input_data: Any
    expected_output: Any | None = None
    actual_output: Any | None = None
    context: dict[str, Any] | None = None


class CreateDatasetRequest(BaseModel):
    name: str
    cases: list[EvaluationCase]


class EvaluateSingleRequest(BaseModel):
    case: EvaluationCase
    evaluation_types: list[EvaluationType] | None = None


class LLMJudgeRequest(BaseModel):
    case: EvaluationCase
    criteria: str
    rubric: str | None = None


@router.post("/initialize")
async def initialize_evaluations(config: EvaluationConfigRequest):
    """評価サービスを初期化"""
    return {
        "initialized": True,
        "evaluation_types": [t.value for t in config.evaluation_types],
        "agent_type": config.agent_type.value,
    }


@router.post("/datasets")
async def create_dataset(request: CreateDatasetRequest, agent_type: AgentType = AgentType.STRANDS):
    """評価データセットを作成"""
    return {
        "dataset_id": "ds-123",
        "name": request.name,
        "case_count": len(request.cases),
        "agent_type": agent_type.value,
    }


@router.post("/datasets/{dataset_id}/cases")
async def add_case(dataset_id: str, case: EvaluationCase, agent_type: AgentType = AgentType.STRANDS):
    """ケースを追加"""
    return {
        "dataset_id": dataset_id,
        "case_id": case.case_id,
        "added": True,
        "agent_type": agent_type.value,
    }


@router.post("/evaluate/single")
async def evaluate_single(request: EvaluateSingleRequest, agent_type: AgentType = AgentType.STRANDS):
    """単一ケースを評価"""
    return {
        "result_id": "result-123",
        "case_id": request.case.case_id,
        "scores": {
            "accuracy": 0.8,
            "relevance": 0.75,
        },
        "status": "completed",
        "agent_type": agent_type.value,
    }


@router.post("/evaluate/dataset/{dataset_id}")
async def evaluate_dataset(dataset_id: str, evaluation_types: list[EvaluationType] | None = None, agent_type: AgentType = AgentType.STRANDS):
    """データセットを評価"""
    return {
        "dataset_id": dataset_id,
        "total_cases": 0,
        "passed_cases": 0,
        "failed_cases": 0,
        "average_scores": {},
        "agent_type": agent_type.value,
    }


@router.post("/evaluate/llm-judge")
async def evaluate_with_llm_judge(request: LLMJudgeRequest, agent_type: AgentType = AgentType.STRANDS):
    """LLM-as-a-Judgeで評価"""
    return {
        "result_id": "result-llm-123",
        "case_id": request.case.case_id,
        "score": 0.8,
        "criteria": request.criteria,
        "agent_type": agent_type.value,
    }


@router.get("/results/{result_id}")
async def get_result(result_id: str, agent_type: AgentType = AgentType.STRANDS):
    """評価結果を取得"""
    return {
        "result_id": result_id,
        "scores": {},
        "status": "completed",
        "agent_type": agent_type.value,
    }


@router.get("/results")
async def list_results(dataset_id: str | None = None, limit: int = 100, agent_type: AgentType = AgentType.STRANDS):
    """評価結果一覧を取得"""
    return {
        "results": [],
        "agent_type": agent_type.value,
    }


@router.get("/summary/{dataset_id}")
async def get_summary(dataset_id: str, agent_type: AgentType = AgentType.STRANDS):
    """サマリーを取得"""
    return {
        "dataset_id": dataset_id,
        "total_cases": 0,
        "passed_cases": 0,
        "failed_cases": 0,
        "average_scores": {},
        "agent_type": agent_type.value,
    }


@router.post("/compare")
async def compare_runs(run_ids: list[str], agent_type: AgentType = AgentType.STRANDS):
    """複数ランを比較"""
    return {
        "comparison": {},
        "agent_type": agent_type.value,
    }

