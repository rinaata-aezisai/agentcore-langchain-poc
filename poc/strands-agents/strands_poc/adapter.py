"""Strands Agent Adapter - AgentCore統合版 (2025年12月版)

AWS Bedrock AgentCore (Strands Agents) の本格的な実装。
2025年12月 re:Invent アップデート対応:
- Memory API: 短期/長期メモリ、エピソード記憶の統合管理
- Caching: プロンプト/ツールキャッシングによるコスト削減
- Guardrails: 入出力のガードレール設定
- Reasoning: 推論プロセスの可視化
"""

import asyncio
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from strands import Agent
from strands.models import BedrockModel
from strands.types.content import SystemContentBlock

from application.ports.agent_port import AgentPort, AgentResponse
from domain.entities.message import Message

from .tools import AVAILABLE_TOOLS

# AgentCore Memory API (Optional - 環境に応じて有効化)
try:
    from bedrock_agentcore.memory import MemoryClient
    from bedrock_agentcore.memory.integrations.strands.config import (
        AgentCoreMemoryConfig,
        RetrievalConfig,
    )
    from bedrock_agentcore.memory.integrations.strands.session_manager import (
        AgentCoreMemorySessionManager,
    )
    AGENTCORE_MEMORY_AVAILABLE = True
except ImportError:
    AGENTCORE_MEMORY_AVAILABLE = False


@dataclass
class LocalConversationMemory:
    """ローカル会話メモリ実装（フォールバック用）

    AgentCore Memory APIが利用できない場合のローカル実装。
    """

    max_history: int = 20
    messages: list[dict[str, str]] = field(default_factory=list)
    episodes: list[dict[str, Any]] = field(default_factory=list)

    def add_message(self, role: str, content: str) -> None:
        """メッセージを追加"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": time.time(),
        })
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history:]

    def add_episode(self, episode: dict[str, Any]) -> None:
        """エピソード（長期記憶）を追加"""
        self.episodes.append({
            **episode,
            "timestamp": time.time(),
        })

    def get_context_string(self) -> str:
        """コンテキスト文字列を生成"""
        if not self.messages:
            return ""
        context_parts = []
        for msg in self.messages:
            role = "User" if msg["role"] == "user" else "Assistant"
            context_parts.append(f"{role}: {msg['content']}")
        return "\n".join(context_parts)

    def get_relevant_episodes(self, query: str, max_episodes: int = 3) -> list[dict[str, Any]]:
        """関連するエピソードを取得（簡易実装）"""
        return self.episodes[-max_episodes:] if self.episodes else []

    def clear(self) -> None:
        """メモリをクリア"""
        self.messages = []


@dataclass
class AgentCoreMemoryManager:
    """AgentCore Memory API を使用したメモリ管理

    AgentCore Memory Session Managerを使用した実装。
    参考: https://dev.classmethod.jp/articles/strands-agents-agentcore-memory-session-manager/

    2025年12月の新機能:
    - 短期メモリ（会話履歴）: session_managerをAgentに渡すだけで自動管理
    - 長期メモリ: retrieval_configでnamespaceを指定して取得
      - User Preference: ユーザーの好みを自動抽出・記憶
      - Semantic Memory: 事実情報を抽出・記憶
      - Summary: 会話の要約を記憶
      - Episodic Memory: エピソードベースの記憶
    """

    memory_id: str
    session_id: str
    actor_id: str
    region_name: str = "us-east-1"
    retrieval_config: dict[str, Any] | None = None  # 長期記憶取得設定
    _client: Any = field(default=None, repr=False)
    _session_manager: Any = field(default=None, repr=False)

    def __post_init__(self):
        if AGENTCORE_MEMORY_AVAILABLE:
            self._client = MemoryClient(region_name=self.region_name)

            # AgentCoreMemoryConfigを作成
            config_kwargs: dict[str, Any] = {
                "memory_id": self.memory_id,
                "session_id": self.session_id,
                "actor_id": self.actor_id,
            }

            # 長期記憶の取得設定（retrieval_config）
            # namespaceを指定することで長期記憶を会話に反映
            if self.retrieval_config:
                config_kwargs["retrieval_config"] = self.retrieval_config

            self._session_manager = AgentCoreMemorySessionManager(
                agentcore_memory_config=AgentCoreMemoryConfig(**config_kwargs),
                region_name=self.region_name,
            )

    @classmethod
    def from_existing_memory(
        cls,
        memory_id: str,
        actor_id: str,
        session_id: str | None = None,
        region_name: str = "us-east-1",
        strategy_namespaces: list[str] | None = None,
        retrieval_top_k: int = 5,
        retrieval_relevance_score: float = 0.5,
    ) -> "AgentCoreMemoryManager":
        """既存のMemoryに接続するファクトリメソッド

        コンソールで作成済みのMemoryを使用する場合に便利。

        Args:
            memory_id: 既存のMemory ID（コンソールから取得）
            actor_id: アクターID（ユーザー識別子）
            session_id: セッションID（省略時は自動生成）
            region_name: AWSリージョン
            strategy_namespaces: 長期記憶のnamespaceリスト（例: ["/strategies/{strategyId}/actors/{actorId}"]）
            retrieval_top_k: 取得する記憶の最大数
            retrieval_relevance_score: 関連性スコアの閾値

        Example:
            # コンソールで作成したMemoryに接続
            manager = AgentCoreMemoryManager.from_existing_memory(
                memory_id="sample_memory-XXXXXXXXXXXX",
                actor_id="user_123",
                strategy_namespaces=[
                    "/strategies/preference_builtin_XXXXX/actors/{actorId}"
                ],
            )
        """
        if not AGENTCORE_MEMORY_AVAILABLE:
            raise RuntimeError(
                "bedrock-agentcore package is not installed. "
                "Install with: pip install 'bedrock-agentcore[strands-agents]'"
            )

        actual_session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 長期記憶のretrieval_configを構築
        retrieval_config = None
        if strategy_namespaces:
            retrieval_config = {}
            for namespace in strategy_namespaces:
                # {actorId}プレースホルダーを実際の値に置換
                actual_namespace = namespace.replace("{actorId}", actor_id)
                retrieval_config[actual_namespace] = RetrievalConfig(
                    top_k=retrieval_top_k,
                    relevance_score=retrieval_relevance_score,
                )

        return cls(
            memory_id=memory_id,
            session_id=actual_session_id,
            actor_id=actor_id,
            region_name=region_name,
            retrieval_config=retrieval_config,
        )

    @classmethod
    def create_with_strategies(
        cls,
        name: str,
        description: str,
        actor_id: str,
        session_id: str | None = None,
        region_name: str = "us-east-1",
        enable_summary: bool = True,
        enable_preferences: bool = True,
        enable_semantic: bool = True,
        retrieval_top_k: int = 5,
        retrieval_relevance_score: float = 0.5,
    ) -> "AgentCoreMemoryManager":
        """新規Memoryを戦略付きで作成するファクトリメソッド

        Args:
            name: メモリの名前
            description: メモリの説明
            actor_id: アクターID（ユーザー識別子）
            session_id: セッションID（省略時は自動生成）
            region_name: AWSリージョン
            enable_summary: 会話要約を有効にするか
            enable_preferences: ユーザー嗜好学習を有効にするか
            enable_semantic: セマンティック記憶（事実抽出）を有効にするか
            retrieval_top_k: 取得する記憶の最大数
            retrieval_relevance_score: 関連性スコアの閾値

        Example:
            # 新規Memoryを作成して接続
            manager = AgentCoreMemoryManager.create_with_strategies(
                name="MyAgentMemory",
                description="Memory for my AI assistant",
                actor_id="user_123",
                enable_preferences=True,
                enable_semantic=True,
            )
        """
        if not AGENTCORE_MEMORY_AVAILABLE:
            raise RuntimeError(
                "bedrock-agentcore package is not installed. "
                "Install with: pip install 'bedrock-agentcore[strands-agents]'"
            )

        client = MemoryClient(region_name=region_name)

        # 戦略の構築（AWSコンソールで作成する場合と同等）
        strategies = []
        retrieval_namespaces = []

        if enable_summary:
            namespace = "/summaries/{actorId}/{sessionId}"
            strategies.append({
                "summaryMemoryStrategy": {
                    "name": "SessionSummarizer",
                    "namespaces": [namespace]
                }
            })
            retrieval_namespaces.append(namespace)

        if enable_preferences:
            namespace = "/preferences/{actorId}"
            strategies.append({
                "userPreferenceMemoryStrategy": {
                    "name": "PreferenceLearner",
                    "namespaces": [namespace]
                }
            })
            retrieval_namespaces.append(namespace)

        if enable_semantic:
            namespace = "/facts/{actorId}"
            strategies.append({
                "semanticMemoryStrategy": {
                    "name": "FactExtractor",
                    "namespaces": [namespace]
                }
            })
            retrieval_namespaces.append(namespace)

        # メモリ作成（同期待機）
        memory = client.create_memory_and_wait(
            name=name,
            description=description,
            strategies=strategies if strategies else None,
        )

        memory_id = memory.get("id")
        actual_session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # retrieval_configを構築
        retrieval_config = None
        if retrieval_namespaces:
            retrieval_config = {}
            for namespace in retrieval_namespaces:
                # {actorId}と{sessionId}を実際の値に置換
                actual_namespace = namespace.replace("{actorId}", actor_id)
                actual_namespace = actual_namespace.replace("{sessionId}", actual_session_id)
                retrieval_config[actual_namespace] = RetrievalConfig(
                    top_k=retrieval_top_k,
                    relevance_score=retrieval_relevance_score,
                )

        return cls(
            memory_id=memory_id,
            session_id=actual_session_id,
            actor_id=actor_id,
            region_name=region_name,
            retrieval_config=retrieval_config,
        )

    def get_session_manager(self) -> Any:
        """Strands Agent用のセッションマネージャーを取得

        AgentのコンストラクタにSessionManagerを渡すだけで
        短期記憶（会話履歴）と長期記憶が自動的に管理される。

        Example:
            agent = Agent(
                model=model,
                system_prompt="あなたは親切なアシスタントです。",
                session_manager=manager.get_session_manager(),
            )
        """
        return self._session_manager

    def get_memory_info(self) -> dict[str, Any]:
        """メモリ情報を取得"""
        return {
            "memory_id": self.memory_id,
            "session_id": self.session_id,
            "actor_id": self.actor_id,
            "region_name": self.region_name,
            "has_retrieval_config": self.retrieval_config is not None,
            "retrieval_namespaces": list(self.retrieval_config.keys()) if self.retrieval_config else [],
        }


class StrandsAgentAdapter(AgentPort):
    """Strands Agents アダプター (AgentCore実装) - 2025年12月版

    AgentCoreの2025年12月新機能:
    - Memory API: 短期・長期メモリの統合管理
    - Caching: プロンプト/ツールキャッシング
    - Guardrails: 入出力ガードレール
    - Reasoning: 推論プロセスの可視化
    - 双方向ストリーミング（Runtime Bidirectional）
    """

    def __init__(
        self,
        model_id: str = "us.anthropic.claude-sonnet-4-20250514-v1:0",
        region: str = "us-east-1",
        system_prompt: str | None = None,
        memory_manager: AgentCoreMemoryManager | None = None,
        local_memory: LocalConversationMemory | None = None,
        # 2025年12月新機能
        enable_caching: bool = True,
        guardrail_id: str | None = None,
        guardrail_version: str = "DRAFT",
        enable_reasoning: bool = False,
        reasoning_budget_tokens: int = 4096,
    ):
        self.model_id = model_id
        self.region = region
        self.system_prompt = system_prompt or self._default_system_prompt()

        # メモリ管理（AgentCore Memory API優先）
        self.memory_manager = memory_manager
        self.local_memory = local_memory or LocalConversationMemory()

        # キャッシング設定
        self.enable_caching = enable_caching

        # Guardrails設定
        self.guardrail_id = guardrail_id
        self.guardrail_version = guardrail_version

        # Reasoning設定
        self.enable_reasoning = enable_reasoning
        self.reasoning_budget_tokens = reasoning_budget_tokens

        # モデル作成
        self.model = self._create_model()

        # 実行統計
        self._execution_stats: dict[str, Any] = {
            "total_executions": 0,
            "total_tool_calls": 0,
            "total_latency_ms": 0,
            "cache_write_tokens": 0,
            "cache_read_tokens": 0,
        }

    def _create_model(self) -> BedrockModel:
        """BedrockModelを作成

        2025年12月の新機能:
        - cache_prompt/cache_tools: キャッシングによるコスト削減
        - guardrail_*: ガードレール設定
        - additional_request_fields: 推論設定等
        """
        model_kwargs: dict[str, Any] = {
            "model_id": self.model_id,
            "region_name": self.region,
            "temperature": 0.7,
            "max_tokens": 4096,
        }

        # キャッシング設定（2025年12月新機能）
        if self.enable_caching:
            model_kwargs["cache_prompt"] = "default"
            model_kwargs["cache_tools"] = "default"

        # Guardrails設定（2025年12月新機能）
        if self.guardrail_id:
            model_kwargs["guardrail_id"] = self.guardrail_id
            model_kwargs["guardrail_version"] = self.guardrail_version
            model_kwargs["guardrail_trace"] = "enabled"

        # Reasoning設定（2025年12月新機能）
        if self.enable_reasoning:
            model_kwargs["additional_request_fields"] = {
                "thinking": {
                    "type": "enabled",
                    "budget_tokens": self.reasoning_budget_tokens
                }
            }

        return BedrockModel(**model_kwargs)

    def _create_agent(self, tools: list | None = None) -> Agent:
        """エージェントインスタンスを作成

        2025年12月の新機能:
        - session_manager: AgentCore Memory APIとの統合
        - SystemContentBlock: キャッシュポイントの設定
        """
        # システムプロンプトの構築（キャッシュポイント付き）
        if self.enable_caching:
            # SystemContentBlockを使用してキャッシュポイントを設定
            system_content = [
                SystemContentBlock(text=self.system_prompt),
                SystemContentBlock(cachePoint={"type": "default"})
            ]
        else:
            system_content = self.system_prompt

        # ローカルメモリからコンテキストを追加
        context = self.local_memory.get_context_string()
        if context:
            if isinstance(system_content, list):
                system_content.insert(1, SystemContentBlock(
                    text=f"\n## 会話履歴\n{context}\n\n上記の会話履歴を考慮して応答してください。"
                ))
            else:
                system_content = f"""{system_content}

## 会話履歴
{context}

上記の会話履歴を考慮して応答してください。
"""

        # エピソード記憶を追加
        episodes = self.local_memory.get_relevant_episodes("")
        if episodes:
            episode_text = "\n".join([
                f"- {ep.get('summary', 'No summary')}"
                for ep in episodes
            ])
            if isinstance(system_content, list):
                system_content.insert(-1, SystemContentBlock(
                    text=f"\n## 過去の経験から学んだこと\n{episode_text}\n"
                ))

        # エージェント作成
        agent_kwargs: dict[str, Any] = {
            "model": self.model,
            "system_prompt": system_content,
            "tools": tools or [],
        }

        # AgentCore Memory APIが利用可能な場合はセッションマネージャーを設定
        if self.memory_manager and self.memory_manager._session_manager:
            agent_kwargs["session_manager"] = self.memory_manager.get_session_manager()

        return Agent(**agent_kwargs)

    async def execute(self, context: list[Message], instruction: str) -> AgentResponse:
        """エージェントを実行（ツールなし）"""
        start_time = time.time()

        # コンテキストをメモリに追加
        for msg in context:
            self.local_memory.add_message(msg.role, msg.content.text)
        self.local_memory.add_message("user", instruction)

        # エージェント作成
        agent = self._create_agent()

        # 実行（同期APIのためrun_in_executor使用）
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: agent(instruction))

        # レスポンス処理
        response_text = str(response)
        self.local_memory.add_message("assistant", response_text)

        # キャッシュ統計を更新
        self._update_cache_stats(response)

        latency_ms = int((time.time() - start_time) * 1000)
        self._update_stats(latency_ms, 0)

        return AgentResponse(
            content=response_text,
            metadata={
                "provider": "strands-agents",
                "model_id": self.model_id,
                "latency_ms": latency_ms,
                "memory_size": len(self.local_memory.messages),
                "agentcore_memory_enabled": self.memory_manager is not None,
                "caching_enabled": self.enable_caching,
                "guardrails_enabled": self.guardrail_id is not None,
                "reasoning_enabled": self.enable_reasoning,
                "framework_features": [
                    "bedrock_native_integration",
                    "agentcore_memory_api",
                    "prompt_caching",
                    "tool_caching",
                    "guardrails",
                    "reasoning_support",
                ],
            },
        )

    async def execute_with_tools(
        self,
        context: list[Message],
        instruction: str,
        tools: list[dict[str, Any]] | None = None,
    ) -> AgentResponse:
        """ツール付きでエージェントを実行

        2025年12月の新機能:
        - ツールキャッシング
        - エピソード記憶（ツール使用パターンの学習）
        """
        start_time = time.time()

        # コンテキストをメモリに追加
        for msg in context:
            self.local_memory.add_message(msg.role, msg.content.text)
        self.local_memory.add_message("user", instruction)

        # カスタムツールまたはデフォルトツールを使用
        agent_tools = tools if tools else AVAILABLE_TOOLS

        # エージェント作成（ツール付き）
        agent = self._create_agent(tools=agent_tools)

        # 実行
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: agent(instruction))

        response_text = str(response)
        self.local_memory.add_message("assistant", response_text)

        # ツール呼び出し情報を抽出
        tool_calls = self._extract_tool_calls(response)

        # ツール使用をエピソードとして記録（AgentCore Episodic Memory相当）
        if tool_calls:
            self.local_memory.add_episode({
                "type": "tool_usage",
                "instruction": instruction,
                "tools_used": [tc["tool_name"] for tc in tool_calls],
                "summary": f"Used tools {[tc['tool_name'] for tc in tool_calls]} for: {instruction[:100]}",
            })

        # キャッシュ統計を更新
        self._update_cache_stats(response)

        latency_ms = int((time.time() - start_time) * 1000)
        self._update_stats(latency_ms, len(tool_calls) if tool_calls else 0)

        return AgentResponse(
            content=response_text,
            tool_calls=tool_calls,
            metadata={
                "provider": "strands-agents",
                "model_id": self.model_id,
                "latency_ms": latency_ms,
                "tools_available": len(agent_tools),
                "tools_called": len(tool_calls) if tool_calls else 0,
                "memory_size": len(self.local_memory.messages),
                "episodes_count": len(self.local_memory.episodes),
                "agentcore_memory_enabled": self.memory_manager is not None,
                "caching_enabled": self.enable_caching,
                "cache_stats": {
                    "write_tokens": self._execution_stats["cache_write_tokens"],
                    "read_tokens": self._execution_stats["cache_read_tokens"],
                },
                "framework_features": [
                    "bedrock_native_integration",
                    "agentcore_memory_api",
                    "prompt_caching",
                    "tool_caching",
                    "automatic_tool_loop",
                    "episodic_memory",
                    "guardrails",
                ],
            },
        )

    async def execute_streaming(
        self,
        context: list[Message],
        instruction: str,
    ):
        """ストリーミングレスポンス（AgentCore Runtime Bidirectional対応）

        2025年12月新機能:
        - 双方向ストリーミング（音声エージェント向け）
        - 中断処理対応
        """
        # NOTE: Strands Agentsの完全なストリーミングは
        # AgentCore Runtimeを使用する場合にネイティブサポート
        response = await self.execute(context, instruction)
        yield response.content

    def _extract_tool_calls(self, response) -> list[dict[str, Any]] | None:
        """レスポンスからツール呼び出し情報を抽出"""
        if hasattr(response, "tool_calls") and response.tool_calls:
            return [
                {
                    "tool_name": tc.name,
                    "tool_input": tc.input if hasattr(tc, "input") else {},
                    "tool_output": tc.output if hasattr(tc, "output") else None,
                }
                for tc in response.tool_calls
            ]
        return None

    def _update_cache_stats(self, response) -> None:
        """キャッシュ統計を更新"""
        if hasattr(response, "metrics") and hasattr(response.metrics, "accumulated_usage"):
            usage = response.metrics.accumulated_usage
            self._execution_stats["cache_write_tokens"] += usage.get("cacheWriteInputTokens", 0)
            self._execution_stats["cache_read_tokens"] += usage.get("cacheReadInputTokens", 0)

    def _update_stats(self, latency_ms: int, tool_calls: int) -> None:
        """実行統計を更新"""
        self._execution_stats["total_executions"] += 1
        self._execution_stats["total_tool_calls"] += tool_calls
        self._execution_stats["total_latency_ms"] += latency_ms

    def clear_memory(self) -> None:
        """メモリをクリア"""
        self.local_memory.clear()

    def get_memory_stats(self) -> dict[str, Any]:
        """メモリ統計を取得"""
        return {
            "message_count": len(self.local_memory.messages),
            "episode_count": len(self.local_memory.episodes),
            "max_history": self.local_memory.max_history,
            "agentcore_memory_enabled": self.memory_manager is not None,
        }

    def get_execution_stats(self) -> dict[str, Any]:
        """実行統計を取得"""
        total = self._execution_stats["total_executions"]
        return {
            **self._execution_stats,
            "avg_latency_ms": (
                self._execution_stats["total_latency_ms"] / total if total > 0 else 0
            ),
        }

    def update_model_config(self, **kwargs) -> None:
        """モデル設定を動的に更新

        2025年12月新機能: runtime設定変更
        """
        self.model.update_config(**kwargs)

    @staticmethod
    def _default_system_prompt() -> str:
        return """あなたは AWS Bedrock AgentCore (Strands Agents) を使用した親切なAIアシスタントです。

## 特徴（2025年12月版）
- AWS Bedrockとのネイティブ統合
- AgentCore Memory APIによる高度なメモリ管理
- プロンプト/ツールキャッシングによる効率化
- Guardrailsによる安全性確保

## 原則
1. 正確で有用な情報を提供する
2. 不確かな場合は明確に伝える
3. ツールが利用可能な場合は適切に活用する
4. 日本語で応答する（ユーザーが英語の場合は英語で）
"""


def create_strands_adapter(
    model_id: str | None = None,
    region: str | None = None,
    system_prompt: str | None = None,
    enable_caching: bool = True,
    guardrail_id: str | None = None,
    enable_reasoning: bool = False,
) -> StrandsAgentAdapter:
    """StrandsAgentAdapterのファクトリ関数

    Args:
        model_id: Bedrockモデル ID (省略時は環境変数から取得)
        region: AWSリージョン (省略時は環境変数から取得)
        system_prompt: システムプロンプト
        enable_caching: キャッシングを有効にするか（デフォルト: True）
        guardrail_id: GuardrailのID（省略可）
        enable_reasoning: 推論可視化を有効にするか（デフォルト: False）
    """
    return StrandsAgentAdapter(
        model_id=model_id or os.getenv(
            "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0"
        ),
        region=region or os.getenv("AWS_REGION", "us-east-1"),
        system_prompt=system_prompt,
        enable_caching=enable_caching,
        guardrail_id=guardrail_id,
        enable_reasoning=enable_reasoning,
    )


def create_strands_adapter_with_memory(
    memory_name: str,
    actor_id: str,
    model_id: str | None = None,
    region: str | None = None,
    system_prompt: str | None = None,
) -> StrandsAgentAdapter:
    """AgentCore Memory API統合版のファクトリ関数

    Args:
        memory_name: メモリの名前
        actor_id: アクターID（ユーザー識別子）
        model_id: Bedrockモデル ID
        region: AWSリージョン
        system_prompt: システムプロンプト
    """
    actual_region = region or os.getenv("AWS_REGION", "us-east-1")

    # AgentCore Memory Managerを作成
    memory_manager = AgentCoreMemoryManager.create_with_strategies(
        name=memory_name,
        description=f"Memory for {memory_name}",
        actor_id=actor_id,
        region_name=actual_region,
    )

    return StrandsAgentAdapter(
        model_id=model_id or os.getenv(
            "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0"
        ),
        region=actual_region,
        system_prompt=system_prompt,
        memory_manager=memory_manager,
    )
