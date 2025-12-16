"""Policy Port - Policy & Guardrails Service Interface

AgentCore Policy / Guardrails / NeMo Guardrails に対応。
入出力フィルタリング、ポリシー管理、安全性制御。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class PolicyType(str, Enum):
    """ポリシータイプ"""
    INPUT_FILTER = "input_filter"  # 入力フィルタ
    OUTPUT_FILTER = "output_filter"  # 出力フィルタ
    CONTENT_MODERATION = "content_moderation"  # コンテンツモデレーション
    PII_DETECTION = "pii_detection"  # PII検出
    TOPIC_RESTRICTION = "topic_restriction"  # トピック制限
    CUSTOM = "custom"  # カスタム


class ValidationStatus(str, Enum):
    """検証ステータス"""
    PASSED = "passed"
    BLOCKED = "blocked"
    WARNING = "warning"
    MODIFIED = "modified"


class Severity(str, Enum):
    """深刻度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PolicyConfig:
    """Policy設定"""
    enabled_policies: list[PolicyType] = field(
        default_factory=lambda: [PolicyType.CONTENT_MODERATION, PolicyType.PII_DETECTION]
    )
    block_on_violation: bool = True
    log_violations: bool = True
    custom_rules_path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyRule:
    """ポリシールール"""
    rule_id: str
    name: str
    policy_type: PolicyType
    description: str = ""
    pattern: str | None = None  # regex pattern
    severity: Severity = Severity.MEDIUM
    action: str = "block"  # "block", "warn", "modify", "log"
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Violation:
    """違反"""
    rule_id: str
    rule_name: str
    policy_type: PolicyType
    severity: Severity
    matched_content: str | None = None
    position: tuple[int, int] | None = None  # start, end
    suggestion: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """検証結果"""
    status: ValidationStatus
    original_content: str
    modified_content: str | None = None
    violations: list[Violation] = field(default_factory=list)
    execution_time_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class PolicyPort(ABC):
    """Policy Port - ポリシー・Guardrails

    Strands Agents: AgentCore Policy / Guardrails
    LangChain: Guardrails AI / NeMo Guardrails
    """

    @abstractmethod
    async def initialize(self, config: PolicyConfig) -> bool:
        """Policyサービスを初期化"""
        ...

    @abstractmethod
    async def add_rule(self, rule: PolicyRule) -> bool:
        """ルールを追加"""
        ...

    @abstractmethod
    async def remove_rule(self, rule_id: str) -> bool:
        """ルールを削除"""
        ...

    @abstractmethod
    async def list_rules(
        self,
        policy_type: PolicyType | None = None,
    ) -> list[PolicyRule]:
        """ルール一覧を取得"""
        ...

    @abstractmethod
    async def validate_input(
        self,
        content: str,
        context: dict[str, Any] | None = None,
    ) -> ValidationResult:
        """入力を検証"""
        ...

    @abstractmethod
    async def validate_output(
        self,
        content: str,
        context: dict[str, Any] | None = None,
    ) -> ValidationResult:
        """出力を検証"""
        ...

    @abstractmethod
    async def detect_pii(self, content: str) -> list[Violation]:
        """PII（個人情報）を検出"""
        ...

    @abstractmethod
    async def moderate_content(
        self,
        content: str,
        categories: list[str] | None = None,
    ) -> ValidationResult:
        """コンテンツをモデレート"""
        ...

    @abstractmethod
    async def apply_guardrails(
        self,
        input_content: str,
        output_content: str,
        context: dict[str, Any] | None = None,
    ) -> tuple[ValidationResult, ValidationResult]:
        """入出力両方にGuardrailsを適用"""
        ...

    @abstractmethod
    async def get_violation_stats(self) -> dict[str, Any]:
        """違反統計を取得"""
        ...

