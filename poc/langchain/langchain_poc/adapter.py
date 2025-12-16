"""LangChain + LangGraph Agent Adapter - 2025年12月版

LangChainエコシステムの最新実装。
LangChain 1.1 / LangGraph 1.0 GA の機能を活用:
- create_agent: 新しい標準的なエージェント作成API
- Middleware: PII、要約、Human-in-the-loop等のミドルウェア
- Model Profiles: モデル機能の自動検出
- StateGraph: 状態管理とワークフロー制御（LangGraph互換レイヤー）
"""

import os
import time
from dataclasses import dataclass, field
from typing import Annotated, Any

from langchain_aws import ChatBedrock
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from application.ports.agent_port import AgentPort, AgentResponse
from domain.entities.message import Message

from .tools import AVAILABLE_TOOLS, get_langchain_tools

# LangChain 1.1 の新機能（Optional - バージョンに応じて有効化）
try:
    from langchain.agents import create_agent
    from langchain.agents.middleware import (
        AgentMiddleware,
        SummarizationMiddleware,
    )
    LANGCHAIN_V1_AVAILABLE = True
except ImportError:
    LANGCHAIN_V1_AVAILABLE = False


@dataclass
class ConversationMemory:
    """LangChain用の会話メモリ実装

    LangChain 1.1のSummarizationMiddlewareと互換性のある形式。
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
            old_messages = self.messages[: -self.max_history]
            self._update_summary(old_messages)
            self.messages = self.messages[-self.max_history:]

    def _update_summary(self, messages: list[BaseMessage]) -> None:
        """要約を更新（簡易実装）"""
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
    """LangChain + LangGraph アダプター - 2025年12月版

    LangChain 1.1 / LangGraph 1.0 GA の特徴:
    - create_agent: 新しい標準エージェントAPI
    - Middleware: コンテキストエンジニアリング
    - Model Profiles: モデル機能の自動検出
    - Checkpointing: 状態の保存・復元
    - Time-Travel Debugging対応
    """

    def __init__(
        self,
        model_provider: str = "bedrock",
        model_id: str = "us.anthropic.claude-sonnet-4-20250514-v1:0",
        region: str = "us-east-1",
        system_prompt: str | None = None,
        memory: ConversationMemory | None = None,
        enable_checkpointing: bool = True,
        # LangChain 1.1 新機能
        enable_summarization_middleware: bool = True,
        summarization_trigger_tokens: int = 500,
    ):
        self.model_provider = model_provider
        self.model_id = model_id
        self.region = region
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.memory = memory or ConversationMemory()
        self.enable_checkpointing = enable_checkpointing

        # LangChain 1.1 Middleware設定
        self.enable_summarization_middleware = enable_summarization_middleware
        self.summarization_trigger_tokens = summarization_trigger_tokens

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

        LangChain 1.1の特徴:
        - Model Profiles による機能自動検出
        - 構造化出力の自動選択
        """
        model = ChatBedrock(
            model_id=self.model_id,
            region_name=self.region,
            model_kwargs={
                "temperature": 0.7,
                "max_tokens": 4096,
            },
        )

        # Model Profiles を確認（LangChain 1.1）
        if hasattr(model, "profile"):
            print(f"Model Profile: {model.profile}")

        return model

    async def execute(self, context: list[Message], instruction: str) -> AgentResponse:
        """エージェントを実行（ツールなし）

        LangChain 1.1の場合はcreate_agentを使用、
        それ以外は従来のainvokeを使用。
        """
        start_time = time.time()

        # コンテキストをメモリに追加
        for msg in context:
            if msg.role == "user":
                self.memory.add_user_message(msg.content.text)
            elif msg.role == "assistant":
                self.memory.add_ai_message(msg.content.text)

        # LangChain 1.1のcreate_agentが利用可能な場合
        if LANGCHAIN_V1_AVAILABLE:
            response = await self._execute_with_create_agent(instruction)
        else:
            # 従来のainvokeを使用
            messages = self._build_messages(instruction)
            response = await self.model.ainvoke(messages)

        # メモリに追加
        self.memory.add_user_message(instruction)
        response_content = response.content if hasattr(response, "content") else str(response)
        self.memory.add_ai_message(response_content)

        latency_ms = int((time.time() - start_time) * 1000)
        self._update_stats(latency_ms, 0)

        return AgentResponse(
            content=response_content,
            metadata={
                "provider": "langchain",
                "model_provider": self.model_provider,
                "model_id": self.model_id,
                "latency_ms": latency_ms,
                "memory_size": len(self.memory.messages),
                "langchain_v1_available": LANGCHAIN_V1_AVAILABLE,
                "framework_features": [
                    "create_agent_api" if LANGCHAIN_V1_AVAILABLE else "legacy_ainvoke",
                    "model_profiles",
                    "middleware_support",
                    "multi_provider_support",
                    "async_native",
                    "conversation_memory",
                ],
            },
        )

    async def _execute_with_create_agent(self, instruction: str) -> Any:
        """LangChain 1.1のcreate_agentを使用して実行"""
        middleware = []

        # 要約ミドルウェア（LangChain 1.1新機能）
        if self.enable_summarization_middleware:
            middleware.append(
                SummarizationMiddleware(
                    model=self.model_id,
                    trigger={"tokens": self.summarization_trigger_tokens}
                )
            )

        agent = create_agent(
            model=self.model,
            tools=[],
            system_prompt=SystemMessage(content=self.system_prompt),
            middleware=middleware,
        )

        # メッセージを構築
        messages = self._build_messages(instruction)

        result = await agent.ainvoke({"messages": messages})
        return result.get("messages", [])[-1] if result.get("messages") else result

    async def execute_with_tools(
        self,
        context: list[Message],
        instruction: str,
        tools: list[dict[str, Any]] | None = None,
    ) -> AgentResponse:
        """ツール付きでエージェントを実行

        LangGraph 1.0 GAの特徴:
        - StateGraphによる状態管理
        - Checkpointingによる状態保存
        - 条件分岐によるワークフロー制御
        - Time-Travel Debugging対応

        LangChain 1.1の場合はcreate_agent + middlewareを使用。
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

        # LangChain 1.1のcreate_agentが利用可能な場合
        if LANGCHAIN_V1_AVAILABLE:
            result = await self._execute_with_tools_create_agent(instruction, agent_tools)
        else:
            # LangGraph StateGraphを使用
            result = await self._execute_with_tools_langgraph(instruction, agent_tools)

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
                "langchain_v1_available": LANGCHAIN_V1_AVAILABLE,
                "framework_features": [
                    "create_agent_api" if LANGCHAIN_V1_AVAILABLE else "langgraph_state_graph",
                    "model_profiles",
                    "middleware_support",
                    "checkpointing",
                    "conditional_edges",
                    "time_travel_debugging",
                    "tool_node_automation",
                    "conversation_memory",
                ],
            },
        )

    async def _execute_with_tools_create_agent(
        self,
        instruction: str,
        tools: list,
    ) -> dict:
        """LangChain 1.1のcreate_agentを使用してツール付き実行"""
        middleware = []

        if self.enable_summarization_middleware:
            middleware.append(
                SummarizationMiddleware(
                    model=self.model_id,
                    trigger={"tokens": self.summarization_trigger_tokens}
                )
            )

        agent = create_agent(
            model=self.model,
            tools=tools,
            system_prompt=SystemMessage(content=self.system_prompt),
            middleware=middleware,
        )

        messages = self._build_messages(instruction)
        config = {
            "configurable": {
                "thread_id": f"session-{time.time()}",
            }
        }

        result = await agent.ainvoke({"messages": messages}, config=config)

        return {
            "messages": result.get("messages", []),
            "tool_calls": self._extract_tool_calls_from_result(result),
        }

    async def _execute_with_tools_langgraph(
        self,
        instruction: str,
        tools: list,
    ) -> dict:
        """LangGraph StateGraphを使用してツール付き実行（従来方式）"""
        graph = self._build_agent_graph(tools)

        messages = self._build_messages(instruction)
        initial_state: AgentState = {
            "messages": messages,
            "tool_calls": [],
            "metadata": {},
        }

        config = {
            "configurable": {
                "thread_id": f"session-{time.time()}",
            }
        }

        result = await graph.ainvoke(initial_state, config=config)
        return result

    def _build_agent_graph(self, tools: list) -> StateGraph:
        """LangGraphエージェントグラフを構築

        LangGraph 1.0 GAの特徴:
        - 宣言的なグラフ定義
        - 条件分岐（conditional_edges）
        - ToolNodeによる自動ツール実行

        NOTE: LangGraph 1.0では langgraph.prebuilt は非推奨
        langchain.agents の create_agent が推奨
        """
        model_with_tools = self.model.bind_tools(tools)

        def should_continue(state: AgentState) -> str:
            """継続判定"""
            messages = state["messages"]
            last_message = messages[-1]

            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"
            return END

        async def call_model(state: AgentState) -> dict:
            """モデル呼び出しノード"""
            messages = state["messages"]
            response = await model_with_tools.ainvoke(messages)

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

        workflow = StateGraph(AgentState)

        workflow.add_node("agent", call_model)
        workflow.add_node("tools", ToolNode(tools))

        workflow.set_entry_point("agent")
        workflow.add_conditional_edges("agent", should_continue)
        workflow.add_edge("tools", "agent")

        if self.checkpointer:
            return workflow.compile(checkpointer=self.checkpointer)
        return workflow.compile()

    def _build_messages(self, instruction: str) -> list[BaseMessage]:
        """メッセージリストを構築"""
        messages: list[BaseMessage] = [SystemMessage(content=self.system_prompt)]

        if self.memory.summary:
            messages.append(SystemMessage(
                content=f"これまでの会話の要約:\n{self.memory.summary}"
            ))

        messages.extend(self.memory.get_messages())
        messages.append(HumanMessage(content=instruction))

        return messages

    def _extract_tool_calls_from_result(self, result: dict) -> list[dict[str, Any]]:
        """結果からツール呼び出し情報を抽出"""
        tool_calls = []
        for msg in result.get("messages", []):
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_calls.append({
                        "tool_name": tc.get("name"),
                        "tool_input": tc.get("args"),
                    })
        return tool_calls

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

## 特徴（2025年12月版）
- LangChain 1.1 の create_agent API
- LangGraph 1.0 GA による高度な状態管理
- Middleware によるコンテキストエンジニアリング
- Model Profiles による機能自動検出
- Checkpointing による状態保存

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
    enable_summarization_middleware: bool = True,
) -> LangChainAgentAdapter:
    """LangChainAgentAdapterのファクトリ関数

    Args:
        model_provider: モデルプロバイダー（デフォルト: bedrock）
        model_id: モデルID（デフォルト: 環境変数から取得）
        region: AWSリージョン（デフォルト: 環境変数から取得）
        system_prompt: システムプロンプト
        enable_checkpointing: Checkpointing を有効にするか
        enable_summarization_middleware: 要約ミドルウェアを有効にするか（LangChain 1.1）
    """
    return LangChainAgentAdapter(
        model_provider=model_provider or os.getenv("MODEL_PROVIDER", "bedrock"),
        model_id=model_id or os.getenv(
            "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0"
        ),
        region=region or os.getenv("AWS_REGION", "us-east-1"),
        system_prompt=system_prompt,
        enable_checkpointing=enable_checkpointing,
        enable_summarization_middleware=enable_summarization_middleware,
    )
