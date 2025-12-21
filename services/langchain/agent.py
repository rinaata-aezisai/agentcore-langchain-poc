"""LangChain/LangGraph Agent Implementation

LangChain + LangGraph による Agent 実装。
比較検証用の統一APIを提供。
"""

import logging
import os
import time
import uuid
from datetime import datetime
from typing import Annotated, Any

from langchain_aws import ChatBedrock
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from tools import AVAILABLE_TOOLS

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===========================================
# Configuration
# ===========================================

MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
ENABLE_CHECKPOINTING = os.getenv("ENABLE_CHECKPOINTING", "true").lower() == "true"

SYSTEM_PROMPT = """あなたは LangChain + LangGraph を使用した親切なAIアシスタントです。

## 特徴
- LangChain によるモデル抽象化
- LangGraph による状態管理とワークフロー制御
- Checkpointing による状態保存
- 条件分岐による柔軟なツール実行

## 原則
1. 正確で有用な情報を提供する
2. 不確かな場合は明確に伝える
3. ツールが利用可能な場合は適切に活用する
4. 日本語で応答する（ユーザーが英語の場合は英語で）

## 利用可能なツール
- get_current_weather: 天気情報取得
- search_documents: ドキュメント検索
- calculate: 数式計算
- create_task: タスク作成
- fetch_url: URL取得
- get_current_time: 現在時刻取得
- analyze_text: テキスト分析
"""

# ===========================================
# Request/Response Models
# ===========================================


class ChatRequest(BaseModel):
    """統一チャットリクエスト"""

    instruction: str = Field(..., description="ユーザーの入力")
    session_id: str | None = Field(None, description="セッションID")
    use_tools: bool = Field(False, description="ツールを使用するか")


class ChatResponse(BaseModel):
    """統一チャットレスポンス"""

    response_id: str
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    latency_ms: int
    metadata: dict[str, Any]


class HealthResponse(BaseModel):
    """ヘルスチェックレスポンス"""

    status: str
    service: str
    version: str
    model_id: str
    region: str
    timestamp: str


class ServiceInfo(BaseModel):
    """サービス情報"""

    service: str
    framework: str
    version: str
    model_id: str
    region: str
    features: list[str]
    tools: list[str]


# ===========================================
# LangGraph State
# ===========================================


class AgentState(TypedDict):
    """LangGraph Agent State"""

    messages: Annotated[list[BaseMessage], add_messages]
    tool_calls: list[dict[str, Any]]


# ===========================================
# LangChain Agent Class
# ===========================================


class LangChainAgent:
    """LangChain/LangGraph Agent"""

    def __init__(
        self,
        model_id: str = MODEL_ID,
        region: str = AWS_REGION,
        enable_checkpointing: bool = ENABLE_CHECKPOINTING,
    ):
        self.model_id = model_id
        self.region = region
        self.enable_checkpointing = enable_checkpointing

        # モデル初期化
        self.model = ChatBedrock(
            model_id=model_id,
            region_name=region,
            model_kwargs={
                "temperature": 0.7,
                "max_tokens": 4096,
            },
        )

        # Checkpointer
        self.checkpointer = MemorySaver() if enable_checkpointing else None

        # グラフは遅延初期化
        self._graph = None
        self._graph_with_tools = None

        logger.info(f"LangChain Agent initialized with model: {model_id}")

    def _build_graph(self, use_tools: bool = False) -> StateGraph:
        """LangGraphエージェントグラフを構築"""
        if use_tools:
            model_with_tools = self.model.bind_tools(AVAILABLE_TOOLS)
        else:
            model_with_tools = self.model

        def should_continue(state: AgentState) -> str:
            """継続判定"""
            messages = state["messages"]
            last_message = messages[-1]

            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"
            return END

        def call_model(state: AgentState) -> dict:
            """モデル呼び出しノード"""
            messages = state["messages"]
            response = model_with_tools.invoke(messages)

            tool_calls = state.get("tool_calls", [])
            if hasattr(response, "tool_calls") and response.tool_calls:
                for tc in response.tool_calls:
                    tool_calls.append(
                        {
                            "tool_name": tc.get("name"),
                            "tool_input": tc.get("args"),
                        }
                    )

            return {
                "messages": [response],
                "tool_calls": tool_calls,
            }

        workflow = StateGraph(AgentState)

        workflow.add_node("agent", call_model)
        if use_tools:
            workflow.add_node("tools", ToolNode(AVAILABLE_TOOLS))

        workflow.set_entry_point("agent")

        if use_tools:
            workflow.add_conditional_edges("agent", should_continue)
            workflow.add_edge("tools", "agent")
        else:
            workflow.add_edge("agent", END)

        if self.checkpointer:
            return workflow.compile(checkpointer=self.checkpointer)
        return workflow.compile()

    def get_graph(self, use_tools: bool = False) -> StateGraph:
        """グラフを取得（キャッシュ）"""
        if use_tools:
            if self._graph_with_tools is None:
                self._graph_with_tools = self._build_graph(use_tools=True)
            return self._graph_with_tools
        else:
            if self._graph is None:
                self._graph = self._build_graph(use_tools=False)
            return self._graph

    def invoke(self, instruction: str, use_tools: bool = False, session_id: str | None = None):
        """エージェントを実行"""
        messages: list[BaseMessage] = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=instruction),
        ]

        initial_state: AgentState = {
            "messages": messages,
            "tool_calls": [],
        }

        config = {
            "configurable": {
                "thread_id": session_id or f"session-{time.time()}",
            }
        }

        graph = self.get_graph(use_tools=use_tools)
        result = graph.invoke(initial_state, config=config)

        return result


# ===========================================
# Singleton Agent Instance
# ===========================================

_agent_instance: LangChainAgent | None = None


def get_agent() -> LangChainAgent:
    """エージェントインスタンスを取得"""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = LangChainAgent()
    return _agent_instance


# ===========================================
# API Functions
# ===========================================


def chat(request: ChatRequest) -> ChatResponse:
    """統一チャットAPI"""
    start_time = time.time()
    logger.info(f"Chat request: {request.instruction[:100]}...")

    agent = get_agent()
    result = agent.invoke(
        instruction=request.instruction,
        use_tools=request.use_tools,
        session_id=request.session_id,
    )

    # レスポンス抽出
    messages = result.get("messages", [])
    last_message = messages[-1] if messages else None

    content = ""
    if last_message:
        if hasattr(last_message, "content"):
            content = last_message.content
        else:
            content = str(last_message)

    tool_calls = result.get("tool_calls", [])
    latency_ms = int((time.time() - start_time) * 1000)

    logger.info(f"Response generated in {latency_ms}ms")

    return ChatResponse(
        response_id=str(uuid.uuid4()),
        content=content,
        tool_calls=tool_calls if tool_calls else None,
        latency_ms=latency_ms,
        metadata={
            "service": "langchain",
            "framework": "langchain + langgraph",
            "model_id": MODEL_ID,
            "region": AWS_REGION,
            "checkpointing_enabled": ENABLE_CHECKPOINTING,
            "tools_used": len(tool_calls) if tool_calls else 0,
        },
    )


def health() -> HealthResponse:
    """ヘルスチェック"""
    return HealthResponse(
        status="healthy",
        service="langchain",
        version="1.0.0",
        model_id=MODEL_ID,
        region=AWS_REGION,
        timestamp=datetime.utcnow().isoformat(),
    )


def info() -> ServiceInfo:
    """サービス情報"""
    return ServiceInfo(
        service="langchain",
        framework="langchain + langgraph",
        version="1.0.0",
        model_id=MODEL_ID,
        region=AWS_REGION,
        features=[
            "multi_provider_support",
            "langgraph_state_management",
            "checkpointing",
            "conditional_edges",
            "tool_node_automation",
            "conversation_memory",
        ],
        tools=[t.name for t in AVAILABLE_TOOLS],
    )

