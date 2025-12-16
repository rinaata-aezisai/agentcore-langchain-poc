"""Strands Policy Adapter

AgentCore Policy サービスの実装。
入出力フィルタリング、ポリシー管理、安全性制御。
"""

import asyncio
import re
from typing import Any
import uuid

import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent.parent.parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_path))

from application.ports.policy_port import (
    PolicyPort,
    PolicyConfig,
    PolicyType,
    PolicyRule,
    Violation,
    ValidationStatus,
    ValidationResult,
    Severity,
)


class StrandsPolicyAdapter(PolicyPort):
    """Strands Agents Policy アダプター
    
    AgentCore Policy/Guardrailsの機能:
    - 入力フィルタリング
    - 出力フィルタリング
    - PII検出
    - コンテンツモデレーション
    """

    def __init__(self):
        self._config: PolicyConfig | None = None
        self._rules: dict[str, PolicyRule] = {}
        self._violation_stats: dict[str, int] = {}
        
        # デフォルトルールを設定
        self._default_rules: list[PolicyRule] = [
            PolicyRule(
                rule_id="pii-email",
                name="Email Detection",
                policy_type=PolicyType.PII_DETECTION,
                description="Detect email addresses",
                pattern=r'[\w\.-]+@[\w\.-]+\.\w+',
                severity=Severity.MEDIUM,
            ),
            PolicyRule(
                rule_id="pii-phone",
                name="Phone Detection",
                policy_type=PolicyType.PII_DETECTION,
                description="Detect phone numbers",
                pattern=r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
                severity=Severity.MEDIUM,
            ),
            PolicyRule(
                rule_id="pii-ssn",
                name="SSN Detection",
                policy_type=PolicyType.PII_DETECTION,
                description="Detect Social Security Numbers",
                pattern=r'\b\d{3}-\d{2}-\d{4}\b',
                severity=Severity.HIGH,
            ),
            PolicyRule(
                rule_id="content-profanity",
                name="Profanity Filter",
                policy_type=PolicyType.CONTENT_MODERATION,
                description="Detect profanity",
                pattern=r'\b(badword1|badword2)\b',  # 実際には適切な辞書を使用
                severity=Severity.MEDIUM,
            ),
            PolicyRule(
                rule_id="content-harmful",
                name="Harmful Content",
                policy_type=PolicyType.CONTENT_MODERATION,
                description="Detect potentially harmful content",
                pattern=r'(hack|exploit|attack)',
                severity=Severity.HIGH,
            ),
        ]

    async def initialize(self, config: PolicyConfig) -> bool:
        """Policyサービスを初期化"""
        self._config = config
        
        # デフォルトルールを追加
        for rule in self._default_rules:
            if rule.policy_type in config.enabled_policies:
                self._rules[rule.rule_id] = rule
        
        return True

    async def add_rule(self, rule: PolicyRule) -> bool:
        """ルールを追加"""
        self._rules[rule.rule_id] = rule
        return True

    async def remove_rule(self, rule_id: str) -> bool:
        """ルールを削除"""
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    async def list_rules(
        self,
        policy_type: PolicyType | None = None,
    ) -> list[PolicyRule]:
        """ルール一覧を取得"""
        rules = list(self._rules.values())
        if policy_type:
            rules = [r for r in rules if r.policy_type == policy_type]
        return rules

    async def validate_input(
        self,
        content: str,
        context: dict[str, Any] | None = None,
    ) -> ValidationResult:
        """入力を検証"""
        return await self._validate_content(
            content,
            [PolicyType.INPUT_FILTER, PolicyType.PII_DETECTION, PolicyType.TOPIC_RESTRICTION],
        )

    async def validate_output(
        self,
        content: str,
        context: dict[str, Any] | None = None,
    ) -> ValidationResult:
        """出力を検証"""
        return await self._validate_content(
            content,
            [PolicyType.OUTPUT_FILTER, PolicyType.CONTENT_MODERATION, PolicyType.PII_DETECTION],
        )

    async def detect_pii(self, content: str) -> list[Violation]:
        """PII（個人情報）を検出"""
        violations = []
        pii_rules = [r for r in self._rules.values() if r.policy_type == PolicyType.PII_DETECTION]
        
        for rule in pii_rules:
            if rule.pattern and rule.enabled:
                matches = list(re.finditer(rule.pattern, content, re.IGNORECASE))
                for match in matches:
                    violations.append(Violation(
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        policy_type=rule.policy_type,
                        severity=rule.severity,
                        matched_content=match.group(),
                        position=(match.start(), match.end()),
                        suggestion="Consider masking or removing this PII",
                    ))
        
        return violations

    async def moderate_content(
        self,
        content: str,
        categories: list[str] | None = None,
    ) -> ValidationResult:
        """コンテンツをモデレート"""
        return await self._validate_content(
            content,
            [PolicyType.CONTENT_MODERATION],
        )

    async def apply_guardrails(
        self,
        input_content: str,
        output_content: str,
        context: dict[str, Any] | None = None,
    ) -> tuple[ValidationResult, ValidationResult]:
        """入出力両方にGuardrailsを適用"""
        input_result = await self.validate_input(input_content, context)
        output_result = await self.validate_output(output_content, context)
        return input_result, output_result

    async def get_violation_stats(self) -> dict[str, Any]:
        """違反統計を取得"""
        return {
            "total_violations": sum(self._violation_stats.values()),
            "by_rule": dict(self._violation_stats),
            "rules_count": len(self._rules),
        }

    async def _validate_content(
        self,
        content: str,
        policy_types: list[PolicyType],
    ) -> ValidationResult:
        """コンテンツを検証"""
        violations = []
        modified_content = content
        
        for rule in self._rules.values():
            if rule.policy_type not in policy_types or not rule.enabled:
                continue
            
            if rule.pattern:
                matches = list(re.finditer(rule.pattern, content, re.IGNORECASE))
                for match in matches:
                    violations.append(Violation(
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        policy_type=rule.policy_type,
                        severity=rule.severity,
                        matched_content=match.group(),
                        position=(match.start(), match.end()),
                    ))
                    
                    # 統計を更新
                    self._violation_stats[rule.rule_id] = (
                        self._violation_stats.get(rule.rule_id, 0) + 1
                    )
                    
                    # アクションに応じて処理
                    if rule.action == "modify":
                        modified_content = re.sub(
                            rule.pattern,
                            "[REDACTED]",
                            modified_content,
                            flags=re.IGNORECASE,
                        )
        
        # ステータスを決定
        if not violations:
            status = ValidationStatus.PASSED
        elif any(v.severity == Severity.CRITICAL for v in violations):
            status = ValidationStatus.BLOCKED
        elif modified_content != content:
            status = ValidationStatus.MODIFIED
        elif self._config and self._config.block_on_violation:
            status = ValidationStatus.BLOCKED
        else:
            status = ValidationStatus.WARNING
        
        return ValidationResult(
            status=status,
            original_content=content,
            modified_content=modified_content if modified_content != content else None,
            violations=violations,
        )


def create_strands_policy() -> StrandsPolicyAdapter:
    """ファクトリ関数"""
    return StrandsPolicyAdapter()

