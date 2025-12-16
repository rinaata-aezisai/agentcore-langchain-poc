"""LangChain Agent Adapter

LangChain + LangGraph の実装。
backendのAgentPortを実装し、DIで注入可能。
"""

import sys
from pathlib import Path
from typing import Any, Annotated

# backendモジュールをパスに追加
backend_path = Path(__file__).parent.parent.parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_path))

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from domain.entities.message import Message
from application.ports.agent_port import AgentPort, AgentResponse


class AgentState(dict):
    messages: Annotated[list[BaseMessage], add_messages]


class LangChainAgentAdapter(AgentPort):
    """LangChain アダプター"""

    def __init__(
        self,
        model_name: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ):
        self.model = ChatAnthropic(model=model_name, temperature=temperature)
        self.system_prompt = system_prompt or self._default_system_prompt()

    async def execute(self, context: list[Message], instruction: str) -> AgentResponse:
        messages = self._convert_context(context)
        messages.insert(0, SystemMessage(content=self.system_prompt))
        messages.append(HumanMessage(content=instruction))

        response = await self.model.ainvoke(messages)
        return AgentResponse(content=response.content, metadata={"provider": "langchain"})

    async def execute_with_tools(
        self, context: list[Message], instruction: str, tools: list[dict[str, Any]],
    ) -> AgentResponse:
        model_with_tools = self.model.bind_tools(tools)
        graph = self._build_graph(model_with_tools, tools)

        messages = self._convert_context(context)
        messages.insert(0, SystemMessage(content=self.system_prompt))
        messages.append(HumanMessage(content=instruction))

        result = await graph.ainvoke({"messages": messages})
        final_message = result["messages"][-1]

        return AgentResponse(
            content=final_message.content if isinstance(final_message, AIMessage) else "",
            tool_calls=self._extract_tool_calls(result["messages"]),
            metadata={"provider": "langchain"},
        )

    def _build_graph(self, model_with_tools, tools):
        def should_continue(state: AgentState) -> str:
            last_message = state["messages"][-1]
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"
            return END

        async def call_model(state: AgentState) -> dict:
            response = await model_with_tools.ainvoke(state["messages"])
            return {"messages": [response]}

        workflow = StateGraph(AgentState)
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", ToolNode(tools))
        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
        workflow.add_edge("tools", "agent")

        return workflow.compile()

    def _convert_context(self, messages: list[Message]) -> list[BaseMessage]:
        result = []
        for msg in messages:
            if msg.role == "user":
                result.append(HumanMessage(content=msg.content.text))
            elif msg.role == "assistant":
                result.append(AIMessage(content=msg.content.text))
            elif msg.role == "system":
                result.append(SystemMessage(content=msg.content.text))
        return result

    def _extract_tool_calls(self, messages: list[BaseMessage]) -> list[dict[str, Any]] | None:
        tool_calls = []
        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_calls.append({"tool_id": tc["name"], "params": tc.get("args", {})})
        return tool_calls if tool_calls else None

    @staticmethod
    def _default_system_prompt() -> str:
        return "あなたは親切で知識豊富なAIアシスタントです。"


