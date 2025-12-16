"""Strands Agent Adapter - AgentCore統合版

AWS Bedrock AgentCore (Strands Agents) の本格的な実装。
AgentCoreの機能を活用:
- Memory: 会話履歴の保持、エピソード記憶
- Tools: @toolデコレータによるツール統合
- Streaming: ストリーミングレスポンス対応
"""

import asyncio
import os
import time
from dataclasses import dataclass, field
from typing import Any

from strands import Agent
from strands.models import BedrockModel

from application.ports.agent_port import AgentPort, AgentResponse
from domain.entities.message import Message

from .tools import AVAILABLE_TOOLS


@dataclass
class ConversationMemory:
    """Strands用の会話メモリ実装

    AgentCoreのMemory APIと互換性のある形式でメモリを管理。
    短期メモリ（会話履歴）と長期メモリ（エピソード）を分離。
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
        # 履歴の上限を超えた場合は古いものを削除
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history:]

    def add_episode(self, episode: dict[str, Any]) -> None:
        """エピソード（長期記憶）を追加

        AgentCoreのEpisodic Memory機能に相当。
        過去の経験から学習するためのデータを保存。
        """
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
        """関連するエピソードを取得（簡易実装）

        本番環境では、AgentCore Memory APIを使用して
        セマンティック検索で関連エピソードを取得。
        """
        # デモ用: 最新のエピソードを返す
        return self.episodes[-max_episodes:] if self.episodes else []

    def clear(self) -> None:
        """メモリをクリア"""
        self.messages = []


class StrandsAgentAdapter(AgentPort):
    """Strands Agents アダプター (AgentCore実装)

    AgentCoreの特徴:
    - AWS Bedrockとのネイティブ統合
    - シンプルなAPI設計（Agent + @tool）
    - 同期API（非同期はrun_in_executor経由）
    - Memory APIによる会話履歴管理
    """

    def __init__(
        self,
        model_id: str = "anthropic.claude-3-haiku-20240307-v1:0",
        region: str = "us-east-1",
        system_prompt: str | None = None,
        memory: ConversationMemory | None = None,
    ):
        self.model = BedrockModel(model_id=model_id, region_name=region)
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.memory = memory or ConversationMemory()
        self._agent: Agent | None = None

    def _create_agent(self, tools: list | None = None) -> Agent:
        """エージェントインスタンスを作成

        Strands Agentsの特徴:
        - 宣言的なエージェント定義
        - ツールは@toolデコレータで定義
        - システムプロンプトで振る舞いを制御
        """
        # メモリからコンテキストを構築
        context = self.memory.get_context_string()
        enhanced_prompt = self.system_prompt

        if context:
            enhanced_prompt = f"""{self.system_prompt}

## 会話履歴
{context}

上記の会話履歴を考慮して応答してください。
"""

        # エピソード記憶を追加（AgentCore Episodic Memory機能）
        episodes = self.memory.get_relevant_episodes("")
        if episodes:
            episode_text = "\n".join([
                f"- {ep.get('summary', 'No summary')}"
                for ep in episodes
            ])
            enhanced_prompt += f"\n## 過去の経験から学んだこと\n{episode_text}\n"

        return Agent(
            model=self.model,
            system_prompt=enhanced_prompt,
            tools=tools or [],
        )

    async def execute(self, context: list[Message], instruction: str) -> AgentResponse:
        """エージェントを実行（ツールなし）

        Strands Agentsの特徴:
        - 同期APIのためrun_in_executorで実行
        - レスポンスは文字列として返される
        """
        start_time = time.time()

        # コンテキストをメモリに追加
        for msg in context:
            self.memory.add_message(msg.role, msg.content.text)

        # ユーザーの指示をメモリに追加
        self.memory.add_message("user", instruction)

        # エージェント作成
        agent = self._create_agent()

        # Strandsは同期APIなのでrun_in_executorで実行
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: agent(instruction))

        # レスポンスをメモリに追加
        response_text = str(response)
        self.memory.add_message("assistant", response_text)

        latency_ms = int((time.time() - start_time) * 1000)

        return AgentResponse(
            content=response_text,
            metadata={
                "provider": "strands-agents",
                "model_id": self.model.model_id,
                "latency_ms": latency_ms,
                "memory_size": len(self.memory.messages),
                "framework_features": [
                    "bedrock_native_integration",
                    "declarative_agent_definition",
                    "conversation_memory",
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

        Strands Agentsの特徴:
        - @toolデコレータで定義されたツールを使用
        - ツール呼び出しは自動的に処理される
        - 複数回のツール呼び出しも自動ループ
        """
        start_time = time.time()

        # コンテキストをメモリに追加
        for msg in context:
            self.memory.add_message(msg.role, msg.content.text)

        self.memory.add_message("user", instruction)

        # カスタムツールまたはデフォルトツールを使用
        agent_tools = tools if tools else AVAILABLE_TOOLS

        # エージェント作成（ツール付き）
        agent = self._create_agent(tools=agent_tools)

        # 実行
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: agent(instruction))

        response_text = str(response)
        self.memory.add_message("assistant", response_text)

        # ツール呼び出し情報を抽出
        tool_calls = self._extract_tool_calls(response)

        # ツール使用をエピソードとして記録（AgentCore Episodic Memory）
        if tool_calls:
            self.memory.add_episode({
                "type": "tool_usage",
                "instruction": instruction,
                "tools_used": [tc["tool_name"] for tc in tool_calls],
                "summary": f"Used tools {[tc['tool_name'] for tc in tool_calls]} for: {instruction[:100]}",
            })

        latency_ms = int((time.time() - start_time) * 1000)

        return AgentResponse(
            content=response_text,
            tool_calls=tool_calls,
            metadata={
                "provider": "strands-agents",
                "model_id": self.model.model_id,
                "latency_ms": latency_ms,
                "tools_available": len(agent_tools),
                "tools_called": len(tool_calls) if tool_calls else 0,
                "memory_size": len(self.memory.messages),
                "episodes_count": len(self.memory.episodes),
                "framework_features": [
                    "bedrock_native_integration",
                    "tool_decorator",
                    "automatic_tool_loop",
                    "conversation_memory",
                    "episodic_memory",
                ],
            },
        )

    async def execute_streaming(
        self,
        context: list[Message],
        instruction: str,
    ):
        """ストリーミングレスポンス（AgentCore Runtime Bidirectional対応）

        AgentCoreの特徴:
        - 双方向ストリーミング（音声エージェント向け）
        - 中断処理対応
        """
        # NOTE: Strands Agentsの現在のバージョンでは
        # 完全なストリーミングAPIは提供されていない
        # AgentCore Runtimeを使用する場合はネイティブサポートあり
        response = await self.execute(context, instruction)
        yield response.content

    def _extract_tool_calls(self, response) -> list[dict[str, Any]] | None:
        """レスポンスからツール呼び出し情報を抽出

        Strands Agentsのtool_calls属性から情報を取得
        """
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

    def clear_memory(self) -> None:
        """メモリをクリア"""
        self.memory.clear()

    def get_memory_stats(self) -> dict[str, Any]:
        """メモリ統計を取得"""
        return {
            "message_count": len(self.memory.messages),
            "episode_count": len(self.memory.episodes),
            "max_history": self.memory.max_history,
        }

    @staticmethod
    def _default_system_prompt() -> str:
        return """あなたは AWS Bedrock AgentCore (Strands Agents) を使用した親切なAIアシスタントです。

## 特徴
- AWS Bedrockとのネイティブ統合
- 会話履歴の自動管理
- ツール呼び出しの自動処理

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
) -> StrandsAgentAdapter:
    """StrandsAgentAdapterのファクトリ関数"""
    return StrandsAgentAdapter(
        model_id=model_id or os.getenv(
            "BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0"
        ),
        region=region or os.getenv("AWS_REGION", "us-east-1"),
        system_prompt=system_prompt,
    )
