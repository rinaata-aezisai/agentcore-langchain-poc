"""LangChain Agent Adapter

LangChain + LangGraph の実装。
backendのAgentPortを実装し、DIで注入可能。
"""

import os
from typing import Annotated, Any

from langchain_anthropic import ChatAnthropic
from langchain_aws import ChatBedrock
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from application.ports.agent_port import AgentPort, AgentResponse
from domain.entities.message import Message

from .tools import AVAILABLE_TOOLS


class AgentState(TypedDict):
    """LangGraph Agent State"""

    messages: Annotated[list, add_messages]


class LangChainAgentAdapter(AgentPort):
    """LangChain + LangGraph アダプター"""

    def __init__(
        self,
        model_provider: str = "bedrock",  # "bedrock" or "anthropic"
        model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0",
        region: str = "us-east-1",
        system_prompt: str | None = None,
        langfuse_enabled: bool = False,
    ):
        self.model_provider = model_provider
        self.model_id = model_id
        self.region = region
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.langfuse_enabled = langfuse_enabled

        # モデル初期化
        self.model = self._create_model()

        # LangFuse callback（オプション）
        self.callbacks = []
        if langfuse_enabled:
            self._setup_langfuse()

    def _create_model(self):
        """モデルを作成"""
        if self.model_provider == "bedrock":
            return ChatBedrock(
                model_id=self.model_id,
                region_name=self.region,
                model_kwargs={"temperature": 0.7},
            )
        elif self.model_provider == "anthropic":
            return ChatAnthropic(
                model=self.model_id.replace("anthropic.", "").replace(":0", ""),
                temperature=0.7,
            )
        else:
            raise ValueError(f"Unknown model provider: {self.model_provider}")

    def _setup_langfuse(self):
        """LangFuseを設定"""
        try:
            from langfuse.callback import CallbackHandler

            self.callbacks.append(
                CallbackHandler(
                    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
                    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
                    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
                )
            )
        except ImportError:
            print("LangFuse not installed, skipping observability")

    async def execute(self, context: list[Message], instruction: str) -> AgentResponse:
        """エージェントを実行（ツールなし）"""
        messages = self._build_messages(context, instruction)

        response = await self.model.ainvoke(
            messages,
            config={"callbacks": self.callbacks} if self.callbacks else None,
        )

        return AgentResponse(
            content=response.content,
            metadata={
                "provider": "langchain",
                "model_provider": self.model_provider,
                "model_id": self.model_id,
            },
        )

    async def execute_with_tools(
        self,
        context: list[Message],
        instruction: str,
        tools: list[dict[str, Any]] | None = None,
    ) -> AgentResponse:
        """ツール付きでエージェントを実行（LangGraph使用）"""
        # ツールバインド
        agent_tools = tools if tools else AVAILABLE_TOOLS
        model_with_tools = self.model.bind_tools(agent_tools)

        # LangGraphワークフロー構築
        graph = self._build_agent_graph(model_with_tools, agent_tools)

        # 実行
        messages = self._build_messages(context, instruction)
        initial_state = {"messages": messages}

        result = await graph.ainvoke(
            initial_state,
            config={"callbacks": self.callbacks} if self.callbacks else None,
        )

        # 最終メッセージを取得
        final_message = result["messages"][-1]
        tool_calls = self._extract_tool_calls(result["messages"])

        content = (
            final_message.content
            if hasattr(final_message, "content")
            else str(final_message)
        )
        return AgentResponse(
            content=content,
            tool_calls=tool_calls,
            metadata={
                "provider": "langchain",
                "model_provider": self.model_provider,
                "model_id": self.model_id,
                "tools_available": len(agent_tools),
                "message_count": len(result["messages"]),
            },
        )

    def _build_agent_graph(self, model_with_tools, tools):
        """LangGraphエージェントグラフを構築"""

        def should_continue(state: AgentState) -> str:
            """継続判定"""
            messages = state["messages"]
            last_message = messages[-1]
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"
            return END

        async def call_model(state: AgentState) -> dict:
            """モデル呼び出し"""
            messages = state["messages"]
            response = await model_with_tools.ainvoke(messages)
            return {"messages": [response]}

        # グラフ構築
        workflow = StateGraph(AgentState)

        # ノード追加
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", ToolNode(tools))

        # エッジ追加
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges("agent", should_continue)
        workflow.add_edge("tools", "agent")

        return workflow.compile()

    def _build_messages(self, context: list[Message], instruction: str) -> list:
        """コンテキストからLangChainメッセージを構築"""
        messages = [SystemMessage(content=self.system_prompt)]

        for msg in context:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content.text))
            elif msg.role == "assistant":
                messages.append(AIMessage(content=msg.content.text))

        messages.append(HumanMessage(content=instruction))
        return messages

    def _extract_tool_calls(self, messages: list) -> list[dict[str, Any]] | None:
        """メッセージからツール呼び出し情報を抽出"""
        tool_calls = []
        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_calls.append(
                        {
                            "tool_name": tc.get("name"),
                            "tool_input": tc.get("args"),
                        }
                    )

        return tool_calls if tool_calls else None

    @staticmethod
    def _default_system_prompt() -> str:
        return """あなたは親切で知識豊富なAIアシスタントです。

以下の原則に従って応答してください：
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
    langfuse_enabled: bool | None = None,
) -> LangChainAgentAdapter:
    """LangChainAgentAdapterのファクトリ関数"""
    default_model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    resolved_langfuse = (
        langfuse_enabled
        if langfuse_enabled is not None
        else os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"
    )
    return LangChainAgentAdapter(
        model_provider=model_provider or os.getenv("MODEL_PROVIDER", "bedrock"),
        model_id=model_id or os.getenv("BEDROCK_MODEL_ID", default_model_id),
        region=region or os.getenv("AWS_REGION", "us-east-1"),
        system_prompt=system_prompt,
        langfuse_enabled=resolved_langfuse,
    )
