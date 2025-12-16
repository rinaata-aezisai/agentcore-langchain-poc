"""LangChain Runtime Adapter

LangGraph Runtime による実装。
エージェント実行環境とライフサイクル管理。
"""

import asyncio
import time
from typing import Any, AsyncIterator, Annotated

from langchain_aws import ChatBedrock
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent.parent.parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_path))

from application.ports.runtime_port import (
    RuntimePort,
    RuntimeConfig,
    RuntimeStatus,
    ExecutionResult,
)


class AgentState(TypedDict):
    """LangGraph Agent State"""
    messages: Annotated[list, add_messages]


class LangChainRuntimeAdapter(RuntimePort):
    """LangChain/LangGraph Runtime アダプター
    
    LangChain相当機能:
    - LangGraph Runtime
    - RunnableSequence
    - Streaming callbacks
    """

    def __init__(self):
        self._config: RuntimeConfig | None = None
        self._model = None
        self._graph = None
        self._status: RuntimeStatus = RuntimeStatus.INITIALIZING
        self._is_paused: bool = False

    async def initialize(self, config: RuntimeConfig) -> RuntimeStatus:
        """ランタイムを初期化"""
        try:
            self._config = config
            
            # Bedrock or Anthropic直接
            if "anthropic" in config.model_id:
                self._model = ChatBedrock(
                    model_id=config.model_id,
                    region_name=config.region,
                    model_kwargs={
                        "temperature": config.temperature,
                        "max_tokens": config.max_tokens,
                    },
                )
            else:
                self._model = ChatBedrock(
                    model_id=config.model_id,
                    region_name=config.region,
                )
            
            # LangGraphを構築
            self._graph = self._build_graph()
            
            self._status = RuntimeStatus.READY
            return self._status
        except Exception as e:
            self._status = RuntimeStatus.ERROR
            raise RuntimeError(f"Runtime initialization failed: {e}")

    def _build_graph(self):
        """LangGraphを構築"""
        async def call_model(state: AgentState) -> dict:
            messages = state["messages"]
            
            # システムプロンプトを追加
            if self._config and self._config.system_prompt:
                all_messages = [SystemMessage(content=self._config.system_prompt)] + messages
            else:
                all_messages = messages
            
            response = await self._model.ainvoke(all_messages)
            return {"messages": [response]}
        
        workflow = StateGraph(AgentState)
        workflow.add_node("agent", call_model)
        workflow.set_entry_point("agent")
        workflow.add_edge("agent", END)
        
        return workflow.compile()

    async def execute(
        self,
        instruction: str,
        context: list[dict[str, Any]] | None = None,
    ) -> ExecutionResult:
        """同期実行"""
        if self._status != RuntimeStatus.READY:
            raise RuntimeError(f"Runtime not ready: {self._status}")
        
        self._status = RuntimeStatus.RUNNING
        start_time = time.time()
        
        try:
            # メッセージを構築
            messages = self._build_messages(context, instruction)
            initial_state = {"messages": messages}
            
            result = await self._graph.ainvoke(initial_state)
            
            execution_time = int((time.time() - start_time) * 1000)
            self._status = RuntimeStatus.READY
            
            # 最終メッセージを取得
            final_message = result["messages"][-1]
            content = final_message.content if hasattr(final_message, "content") else str(final_message)
            
            return ExecutionResult(
                content=content,
                status=RuntimeStatus.READY,
                iterations=1,
                execution_time_ms=execution_time,
                metadata={
                    "provider": "langchain",
                    "model_id": self._config.model_id,
                    "message_count": len(result["messages"]),
                },
            )
        except Exception as e:
            self._status = RuntimeStatus.ERROR
            raise RuntimeError(f"Execution failed: {e}")

    async def execute_stream(
        self,
        instruction: str,
        context: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[str]:
        """ストリーミング実行"""
        if self._status != RuntimeStatus.READY:
            raise RuntimeError(f"Runtime not ready: {self._status}")
        
        self._status = RuntimeStatus.RUNNING
        
        try:
            messages = self._build_messages(context, instruction)
            
            # システムプロンプトを追加
            if self._config and self._config.system_prompt:
                all_messages = [SystemMessage(content=self._config.system_prompt)] + messages
            else:
                all_messages = messages
            
            async for chunk in self._model.astream(all_messages):
                if hasattr(chunk, "content"):
                    yield chunk.content
            
            self._status = RuntimeStatus.READY
        except Exception as e:
            self._status = RuntimeStatus.ERROR
            raise RuntimeError(f"Streaming execution failed: {e}")

    async def execute_with_tools(
        self,
        instruction: str,
        tools: list[Any],
        context: list[dict[str, Any]] | None = None,
    ) -> ExecutionResult:
        """ツール付き実行"""
        if self._status != RuntimeStatus.READY:
            raise RuntimeError(f"Runtime not ready: {self._status}")
        
        self._status = RuntimeStatus.RUNNING
        start_time = time.time()
        
        try:
            # ツールバインド
            model_with_tools = self._model.bind_tools(tools)
            
            # ツール対応グラフを構築
            graph = self._build_tool_graph(model_with_tools, tools)
            
            messages = self._build_messages(context, instruction)
            initial_state = {"messages": messages}
            
            result = await graph.ainvoke(initial_state)
            
            execution_time = int((time.time() - start_time) * 1000)
            self._status = RuntimeStatus.READY
            
            final_message = result["messages"][-1]
            content = final_message.content if hasattr(final_message, "content") else str(final_message)
            
            # ツール呼び出し情報を抽出
            tool_calls = self._extract_tool_calls(result["messages"])
            
            return ExecutionResult(
                content=content,
                status=RuntimeStatus.READY,
                iterations=len(result["messages"]) // 2,
                execution_time_ms=execution_time,
                tool_calls=tool_calls,
                metadata={
                    "provider": "langchain",
                    "model_id": self._config.model_id,
                    "tools_available": len(tools),
                },
            )
        except Exception as e:
            self._status = RuntimeStatus.ERROR
            raise RuntimeError(f"Tool execution failed: {e}")

    def _build_tool_graph(self, model_with_tools, tools):
        """ツール対応グラフを構築"""
        from langgraph.prebuilt import ToolNode
        
        def should_continue(state: AgentState) -> str:
            messages = state["messages"]
            last_message = messages[-1]
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"
            return END
        
        async def call_model(state: AgentState) -> dict:
            messages = state["messages"]
            if self._config and self._config.system_prompt:
                all_messages = [SystemMessage(content=self._config.system_prompt)] + messages
            else:
                all_messages = messages
            response = await model_with_tools.ainvoke(all_messages)
            return {"messages": [response]}
        
        workflow = StateGraph(AgentState)
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", ToolNode(tools))
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges("agent", should_continue)
        workflow.add_edge("tools", "agent")
        
        return workflow.compile()

    def _build_messages(
        self,
        context: list[dict[str, Any]] | None,
        instruction: str,
    ) -> list:
        """メッセージリストを構築"""
        messages = []
        
        if context:
            for msg in context:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))
        
        messages.append(HumanMessage(content=instruction))
        return messages

    def _extract_tool_calls(self, messages: list) -> list[dict[str, Any]] | None:
        """ツール呼び出し情報を抽出"""
        tool_calls = []
        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_calls.append({
                        "tool_name": tc.get("name"),
                        "tool_input": tc.get("args"),
                    })
        return tool_calls if tool_calls else None

    async def get_status(self) -> RuntimeStatus:
        """ステータス取得"""
        return self._status

    async def pause(self) -> bool:
        """一時停止"""
        if self._status == RuntimeStatus.RUNNING:
            self._is_paused = True
            self._status = RuntimeStatus.PAUSED
            return True
        return False

    async def resume(self) -> bool:
        """再開"""
        if self._status == RuntimeStatus.PAUSED:
            self._is_paused = False
            self._status = RuntimeStatus.READY
            return True
        return False

    async def terminate(self) -> bool:
        """終了"""
        self._status = RuntimeStatus.TERMINATED
        self._graph = None
        self._model = None
        return True


def create_langchain_runtime() -> LangChainRuntimeAdapter:
    """ファクトリ関数"""
    return LangChainRuntimeAdapter()

