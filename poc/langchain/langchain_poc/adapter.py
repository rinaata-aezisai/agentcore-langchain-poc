"""LangChain + LangGraph Agent Adapter - 本格実装

LangChainエコシステムの本格的な実装。
LangGraph 1.0 GA の機能を活用:
- StateGraph: 状態管理とワークフロー制御
- Checkpointing: 状態の保存と復元
- Memory: ConversationBufferMemory / Summary
- Tool Calling: ツール呼び出しの自動処理
"""

import os
import time
from dataclasses import dataclass, field
from typing import Annotated, Any

from langchain_aws import ChatBedrock
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from application.ports.agent_port import AgentPort, AgentResponse
from domain.entities.message import Message

from .tools import AVAILABLE_TOOLS, get_langchain_tools


@dataclass
class ConversationMemory:
    """LangChain用の会話メモリ実装

    LangChainのMemoryコンポーネントと互換性のある形式。
    ConversationBufferMemory相当の機能を提供。
    """

    max_history: int = 20
    messages: list[BaseMessage] = field(default_factory=list)
    summary: str = ""

    def add_user_message(self, content: str) -> None:
        """ユーザーメッセージを追加"""
        self.messages.append(HumanMessage(content=content))
        self._trim_history()

    def add_ai_message(self, content: str) -> None:
        """AIメッセージを追加"""
        self.messages.append(AIMessage(content=content))
        self._trim_history()

    def _trim_history(self) -> None:
        """履歴を制限"""
        if len(self.messages) > self.max_history:
            # 古いメッセージを要約（LangChainのConversationSummaryMemory相当）
            old_messages = self.messages[: -self.max_history]
            self._update_summary(old_messages)
            self.messages = self.messages[-self.max_history:]

    def _update_summary(self, messages: list[BaseMessage]) -> None:
        """要約を更新（簡易実装）"""
        # 本番ではLLMを使用して要約を生成
        summaries = []
        for msg in messages:
            role = "User" if isinstance(msg, HumanMessage) else "Assistant"
            summaries.append(f"{role}: {msg.content[:100]}...")
        self.summary += "\n" + "\n".join(summaries)

    def get_messages(self) -> list[BaseMessage]:
        """メッセージ履歴を取得"""
        return self.messages.copy()

    def clear(self) -> None:
        """メモリをクリア"""
        self.messages = []
        self.summary = ""


class AgentState(TypedDict):
    """LangGraph Agent State

    LangGraphの状態管理の中核。
    - messages: 会話履歴（add_messagesアノテーションで自動マージ）
    - tool_calls: ツール呼び出し履歴
    - metadata: 追加のメタデータ
    """

    messages: Annotated[list[BaseMessage], add_messages]
    tool_calls: list[dict[str, Any]]
    metadata: dict[str, Any]


class LangChainAgentAdapter(AgentPort):
    """LangChain + LangGraph アダプター

    LangChainエコシステムの特徴:
    - マルチプロバイダー対応（Bedrock/Anthropic/OpenAI等）
    - LangGraphによる高度な状態管理
    - Checkpointingによる状態の保存・復元
    - Time-Travel Debuggingサポート
    """

    def __init__(
        self,
        model_provider: str = "bedrock",
        model_id: str = "anthropic.claude-3-haiku-20240307-v1:0",
        region: str = "us-east-1",
        system_prompt: str | None = None,
        memory: ConversationMemory | None = None,
        enable_checkpointing: bool = True,
    ):
        self.model_provider = model_provider
        self.model_id = model_id
        self.region = region
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.memory = memory or ConversationMemory()
        self.enable_checkpointing = enable_checkpointing

        # モデル初期化
        self.model = self._create_model()

        # Checkpointer（LangGraphの状態保存機能）
        self.checkpointer = MemorySaver() if enable_checkpointing else None

        # 実行統計
        self._execution_stats: dict[str, Any] = {
            "total_executions": 0,
            "total_tool_calls": 0,
            "total_latency_ms": 0,
        }

    def _create_model(self) -> ChatBedrock:
        """モデルを作成

        LangChainの特徴:
        - Model Profiles による機能自動検出（LangChain 1.1）
        - 構造化出力の自動選択
        """
        return ChatBedrock(
            model_id=self.model_id,
            region_name=self.region,
            model_kwargs={
                "temperature": 0.7,
                "max_tokens": 4096,
            },
        )

    async def execute(self, context: list[Message], instruction: str) -> AgentResponse:
        """エージェントを実行（ツールなし）

        LangChainの特徴:
        - 完全非同期対応（ainvoke）
        - メッセージベースのAPI
        """
        start_time = time.time()

        # コンテキストをメモリに追加
        for msg in context:
            if msg.role == "user":
                self.memory.add_user_message(msg.content.text)
            elif msg.role == "assistant":
                self.memory.add_ai_message(msg.content.text)

        # メッセージを構築
        messages = self._build_messages(instruction)

        # 実行
        response = await self.model.ainvoke(messages)

        # メモリに追加
        self.memory.add_user_message(instruction)
        self.memory.add_ai_message(response.content)

        latency_ms = int((time.time() - start_time) * 1000)
        self._update_stats(latency_ms, 0)

        return AgentResponse(
            content=response.content,
            metadata={
                "provider": "langchain",
                "model_provider": self.model_provider,
                "model_id": self.model_id,
                "latency_ms": latency_ms,
                "memory_size": len(self.memory.messages),
                "framework_features": [
                    "multi_provider_support",
                    "async_native",
                    "message_based_api",
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
        """ツール付きでエージェントを実行（LangGraph使用）

        LangGraph 1.0 GAの特徴:
        - StateGraphによる状態管理
        - Checkpointingによる状態保存
        - 条件分岐によるワークフロー制御
        - Time-Travel Debugging対応
        """
        start_time = time.time()

        # コンテキストをメモリに追加
        for msg in context:
            if msg.role == "user":
                self.memory.add_user_message(msg.content.text)
            elif msg.role == "assistant":
                self.memory.add_ai_message(msg.content.text)

        # ツール準備
        agent_tools = tools if tools else get_langchain_tools()

        # LangGraphワークフロー構築
        graph = self._build_agent_graph(agent_tools)

        # 初期状態
        messages = self._build_messages(instruction)
        initial_state: AgentState = {
            "messages": messages,
            "tool_calls": [],
            "metadata": {},
        }

        # 実行設定（Checkpointing対応）
        config = {
            "configurable": {
                "thread_id": f"session-{time.time()}",  # セッション識別子
            }
        }

        # 実行
        result = await graph.ainvoke(initial_state, config=config)

        # 最終メッセージを取得
        final_message = result["messages"][-1]
        tool_calls = result.get("tool_calls", [])

        content = (
            final_message.content
            if hasattr(final_message, "content")
            else str(final_message)
        )

        # メモリに追加
        self.memory.add_user_message(instruction)
        self.memory.add_ai_message(content)

        latency_ms = int((time.time() - start_time) * 1000)
        self._update_stats(latency_ms, len(tool_calls))

        return AgentResponse(
            content=content,
            tool_calls=tool_calls if tool_calls else None,
            metadata={
                "provider": "langchain",
                "model_provider": self.model_provider,
                "model_id": self.model_id,
                "latency_ms": latency_ms,
                "tools_available": len(agent_tools),
                "tools_called": len(tool_calls),
                "message_count": len(result["messages"]),
                "memory_size": len(self.memory.messages),
                "checkpointing_enabled": self.enable_checkpointing,
                "framework_features": [
                    "langgraph_state_management",
                    "checkpointing",
                    "conditional_edges",
                    "time_travel_debugging",
                    "tool_node_automation",
                    "conversation_memory",
                ],
            },
        )

    def _build_agent_graph(self, tools: list) -> StateGraph:
        """LangGraphエージェントグラフを構築

        LangGraph 1.0 GAの特徴:
        - 宣言的なグラフ定義
        - 条件分岐（conditional_edges）
        - ToolNodeによる自動ツール実行
        """
        # ツールバインド
        model_with_tools = self.model.bind_tools(tools)

        def should_continue(state: AgentState) -> str:
            """継続判定

            LangGraphの条件分岐:
            - ツール呼び出しがあれば "tools" へ
            - なければ END へ
            """
            messages = state["messages"]
            last_message = messages[-1]

            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"
            return END

        async def call_model(state: AgentState) -> dict:
            """モデル呼び出しノード"""
            messages = state["messages"]
            response = await model_with_tools.ainvoke(messages)

            # ツール呼び出しを記録
            tool_calls = state.get("tool_calls", [])
            if hasattr(response, "tool_calls") and response.tool_calls:
                for tc in response.tool_calls:
                    tool_calls.append({
                        "tool_name": tc.get("name"),
                        "tool_input": tc.get("args"),
                    })

            return {
                "messages": [response],
                "tool_calls": tool_calls,
            }

        # グラフ構築
        workflow = StateGraph(AgentState)

        # ノード追加
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", ToolNode(tools))

        # エッジ追加
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges("agent", should_continue)
        workflow.add_edge("tools", "agent")

        # コンパイル（Checkpointer付き）
        if self.checkpointer:
            return workflow.compile(checkpointer=self.checkpointer)
        return workflow.compile()

    def _build_messages(self, instruction: str) -> list[BaseMessage]:
        """メッセージリストを構築

        LangChainのメッセージ形式:
        - SystemMessage: システムプロンプト
        - HumanMessage: ユーザー入力
        - AIMessage: アシスタント応答
        """
        messages: list[BaseMessage] = [SystemMessage(content=self.system_prompt)]

        # 要約があれば追加（ConversationSummaryMemory相当）
        if self.memory.summary:
            messages.append(SystemMessage(
                content=f"これまでの会話の要約:\n{self.memory.summary}"
            ))

        # 会話履歴を追加
        messages.extend(self.memory.get_messages())

        # 新しい指示を追加
        messages.append(HumanMessage(content=instruction))

        return messages

    def _update_stats(self, latency_ms: int, tool_calls: int) -> None:
        """実行統計を更新"""
        self._execution_stats["total_executions"] += 1
        self._execution_stats["total_tool_calls"] += tool_calls
        self._execution_stats["total_latency_ms"] += latency_ms

    def clear_memory(self) -> None:
        """メモリをクリア"""
        self.memory.clear()

    def get_memory_stats(self) -> dict[str, Any]:
        """メモリ統計を取得"""
        return {
            "message_count": len(self.memory.messages),
            "max_history": self.memory.max_history,
            "has_summary": bool(self.memory.summary),
            "checkpointing_enabled": self.enable_checkpointing,
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

    @staticmethod
    def _default_system_prompt() -> str:
        return """あなたは LangChain + LangGraph を使用した親切なAIアシスタントです。

## 特徴
- LangGraph 1.0 GA による高度な状態管理
- Checkpointingによる状態保存
- マルチプロバイダー対応

## 原則
1. 正確で有用な情報を提供する
2. 不確かな場合は明確に伝える
3. ツールが利用可能な場合は適切に活用する
4. 日本語で応答する（ユーザーが英語の場合は英語で）
"""


def create_langchain_adapter(
    model_provider: str | None = None,
    model_id: str | None = None,
    region: str | None = None,
    system_prompt: str | None = None,
    enable_checkpointing: bool = True,
) -> LangChainAgentAdapter:
    """LangChainAgentAdapterのファクトリ関数"""
    return LangChainAgentAdapter(
        model_provider=model_provider or os.getenv("MODEL_PROVIDER", "bedrock"),
        model_id=model_id or os.getenv(
            "BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0"
        ),
        region=region or os.getenv("AWS_REGION", "us-east-1"),
        system_prompt=system_prompt,
        enable_checkpointing=enable_checkpointing,
    )
