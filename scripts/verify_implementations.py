#!/usr/bin/env python3
"""
Implementation Verification Script

Strands AgentsとLangChainの両実装を検証し、結果をレポート出力するスクリプト。
AWS Bedrockへの接続なしでもインポート検証は可能。
"""

import asyncio
import json
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class VerificationResult:
    """検証結果"""

    component: str
    check_name: str
    status: str  # "pass", "fail", "skip"
    message: str
    details: dict | None = None


class ImplementationVerifier:
    """実装検証クラス"""

    def __init__(self):
        self.results: list[VerificationResult] = []

    def add_result(
        self,
        component: str,
        check: str,
        status: str,
        message: str,
        details: dict | None = None,
    ):
        self.results.append(
            VerificationResult(component, check, status, message, details)
        )

    def verify_strands_imports(self) -> bool:
        """Strands Agents のインポート検証"""
        try:
            from strands import Agent  # noqa: F401
            from strands.models import BedrockModel  # noqa: F401

            self.add_result(
                "strands-agents",
                "core_imports",
                "pass",
                "Agent, BedrockModel インポート成功",
            )
            return True
        except ImportError as e:
            self.add_result(
                "strands-agents", "core_imports", "fail", f"インポートエラー: {e}"
            )
            return False

    def verify_langchain_imports(self) -> bool:
        """LangChain のインポート検証"""
        try:
            from langchain_aws import ChatBedrock  # noqa: F401
            from langchain_core.messages import (  # noqa: F401
                AIMessage,
                HumanMessage,
                SystemMessage,
            )
            from langgraph.graph import END, StateGraph  # noqa: F401

            self.add_result(
                "langchain",
                "core_imports",
                "pass",
                "ChatBedrock, LangGraph インポート成功",
            )
            return True
        except ImportError as e:
            self.add_result(
                "langchain", "core_imports", "fail", f"インポートエラー: {e}"
            )
            return False

    def verify_adapter_implementations(self) -> bool:
        """アダプター実装の検証"""
        all_pass = True

        # Strands adapter
        try:
            from strands_poc.adapter import (  # noqa: F401
                StrandsAgentAdapter,
                create_strands_adapter,
            )

            self.add_result(
                "strands-agents",
                "adapter_implementation",
                "pass",
                "StrandsAgentAdapter 実装確認",
            )
        except ImportError as e:
            self.add_result(
                "strands-agents",
                "adapter_implementation",
                "fail",
                f"アダプターインポートエラー: {e}",
            )
            all_pass = False

        # LangChain adapter
        try:
            from langchain_poc.adapter import (  # noqa: F401
                LangChainAgentAdapter,
                create_langchain_adapter,
            )

            self.add_result(
                "langchain",
                "adapter_implementation",
                "pass",
                "LangChainAgentAdapter 実装確認",
            )
        except ImportError as e:
            self.add_result(
                "langchain",
                "adapter_implementation",
                "fail",
                f"アダプターインポートエラー: {e}",
            )
            all_pass = False

        return all_pass

    def verify_backend_integration(self) -> bool:
        """バックエンド統合の検証"""
        try:
            from application.ports.agent_port import AgentPort, AgentResponse  # noqa: F401
            from domain.entities.message import Message  # noqa: F401
            from domain.entities.session import Session  # noqa: F401

            self.add_result(
                "backend", "core_domain", "pass", "ドメインモデル・ポート定義確認"
            )

            # AdapterがAgentPortを実装しているか確認
            from langchain_poc.adapter import LangChainAgentAdapter
            from strands_poc.adapter import StrandsAgentAdapter

            if issubclass(StrandsAgentAdapter, AgentPort):
                self.add_result(
                    "strands-agents",
                    "port_implementation",
                    "pass",
                    "AgentPort インターフェース実装確認",
                )
            else:
                self.add_result(
                    "strands-agents",
                    "port_implementation",
                    "fail",
                    "AgentPort 未実装",
                )

            if issubclass(LangChainAgentAdapter, AgentPort):
                self.add_result(
                    "langchain",
                    "port_implementation",
                    "pass",
                    "AgentPort インターフェース実装確認",
                )
            else:
                self.add_result(
                    "langchain", "port_implementation", "fail", "AgentPort 未実装"
                )

            return True
        except ImportError as e:
            self.add_result(
                "backend", "core_domain", "fail", f"インポートエラー: {e}"
            )
            return False

    async def verify_bedrock_connection(self) -> bool:
        """AWS Bedrock接続の検証（オプション）"""
        import os

        if not os.getenv("AWS_ACCESS_KEY_ID") and not os.getenv("AWS_PROFILE"):
            self.add_result(
                "aws",
                "bedrock_connection",
                "skip",
                "AWS認証情報未設定のためスキップ",
            )
            return True

        # Strands接続テスト
        try:
            from strands import Agent
            from strands.models import BedrockModel

            model = BedrockModel(
                model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
                region_name=os.getenv("AWS_REGION", "us-east-1"),
            )
            agent = Agent(model=model)
            response = agent("Hello! Respond with just 'OK'.")

            self.add_result(
                "strands-agents",
                "bedrock_connection",
                "pass",
                f"Bedrock接続成功: {str(response)[:50]}...",
            )
        except Exception as e:
            self.add_result(
                "strands-agents",
                "bedrock_connection",
                "fail",
                f"Bedrock接続エラー: {e}",
            )

        # LangChain接続テスト
        try:
            from langchain_aws import ChatBedrock
            from langchain_core.messages import HumanMessage

            model = ChatBedrock(
                model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
                region_name=os.getenv("AWS_REGION", "us-east-1"),
            )
            response = await model.ainvoke(
                [HumanMessage(content="Hello! Respond with just 'OK'.")]
            )

            self.add_result(
                "langchain",
                "bedrock_connection",
                "pass",
                f"Bedrock接続成功: {response.content[:50]}...",
            )
        except Exception as e:
            self.add_result(
                "langchain",
                "bedrock_connection",
                "fail",
                f"Bedrock接続エラー: {e}",
            )

        return True

    def generate_report(self) -> str:
        """Markdownレポートを生成"""
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

        # 統計計算
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == "pass")
        failed = sum(1 for r in self.results if r.status == "fail")
        skipped = sum(1 for r in self.results if r.status == "skip")

        report = f"""# AgentCore vs LangChain PoC 検証レポート

**生成日時**: {timestamp}

## サマリー

| 項目 | 結果 |
|------|------|
| 総検証項目数 | {total} |
| 成功 | {passed} ✅ |
| 失敗 | {failed} ❌ |
| スキップ | {skipped} ⏭️ |
| 成功率 | {(passed / total * 100):.1f}% |

## 検証結果詳細

"""

        # コンポーネント別にグループ化
        components: dict[str, list[VerificationResult]] = {}
        for result in self.results:
            if result.component not in components:
                components[result.component] = []
            components[result.component].append(result)

        for component, results in components.items():
            report += f"### {component}\n\n"
            report += "| チェック項目 | ステータス | メッセージ |\n"
            report += "|-------------|----------|----------|\n"

            for r in results:
                status_icon = {"pass": "✅", "fail": "❌", "skip": "⏭️"}.get(
                    r.status, "❓"
                )
                report += f"| {r.check_name} | {status_icon} {r.status} | {r.message} |\n"

            report += "\n"

        report += """## 実装アーキテクチャ

### Strands Agents (AWS Bedrock AgentCore)

```
strands_poc/
├── adapter.py      # AgentPort実装（StrandsAgentAdapter）
├── tools.py        # ツール定義
└── example.py      # 使用例
```

**特徴**:
- AWS Bedrock完全統合
- シンプルなAPI設計
- 同期API（非同期はrun_in_executor経由）

### LangChain + LangGraph

```
langchain_poc/
├── adapter.py      # AgentPort実装（LangChainAgentAdapter）
├── tools.py        # ツール定義
└── example.py      # 使用例
```

**特徴**:
- マルチプロバイダー対応
- LangGraphによる複雑なワークフロー
- 完全非同期対応

## Clean Architecture 統合

```
backend/
├── domain/
│   ├── entities/       # Session, Message
│   └── ports/          # AgentPort インターフェース
├── application/
│   └── handlers/       # CQRS ハンドラ
└── infrastructure/
    └── persistence/    # イベントストア
```

## 次のステップ

1. **AWS環境でのE2Eテスト実行**
2. **パフォーマンスベンチマーク**
3. **本番環境へのデプロイ**

---
*このレポートは `scripts/verify_implementations.py` により自動生成されました。*
"""
        return report


async def main():
    """メイン処理"""
    print("=" * 60)
    print("AgentCore vs LangChain 実装検証")
    print("=" * 60)

    verifier = ImplementationVerifier()

    # 検証実行
    print("\n[1/4] Strands Agents インポート検証...")
    verifier.verify_strands_imports()

    print("[2/4] LangChain インポート検証...")
    verifier.verify_langchain_imports()

    print("[3/4] アダプター実装検証...")
    verifier.verify_adapter_implementations()

    print("[4/4] バックエンド統合検証...")
    verifier.verify_backend_integration()

    # AWS接続テスト（オプション）
    print("[Optional] AWS Bedrock接続検証...")
    await verifier.verify_bedrock_connection()

    # 結果表示
    print("\n" + "=" * 60)
    print("検証結果")
    print("=" * 60)

    for result in verifier.results:
        icon = {"pass": "✅", "fail": "❌", "skip": "⏭️"}.get(result.status, "❓")
        print(f"{icon} [{result.component}] {result.check_name}: {result.message}")

    # レポート生成
    report = verifier.generate_report()

    # 保存
    docs_dir = Path("docs/reports")
    docs_dir.mkdir(parents=True, exist_ok=True)

    report_file = docs_dir / "poc-verification-report.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n📄 レポート保存: {report_file}")

    # JSON形式でも保存
    json_file = docs_dir / "verification-results.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "results": [asdict(r) for r in verifier.results],
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"📄 JSON結果保存: {json_file}")

    # 失敗があれば非ゼロで終了
    failed_count = sum(1 for r in verifier.results if r.status == "fail")
    if failed_count > 0:
        print(f"\n⚠️ {failed_count}件の検証が失敗しました")
        sys.exit(1)

    print("\n✅ すべての検証が成功しました")


if __name__ == "__main__":
    asyncio.run(main())
