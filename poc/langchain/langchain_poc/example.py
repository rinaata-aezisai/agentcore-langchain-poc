"""LangChain + LangGraph 使用例 - 2025年12月版

LangChain 1.1 / LangGraph 1.0 GAの新機能を活用した実装例。

機能:
- create_agent: 新しい標準エージェントAPI
- Middleware: PII、要約、Human-in-the-loop
- Model Profiles: モデル機能の自動検出
- StateGraph: 状態管理とワークフロー制御
"""

import asyncio
import os

from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage, SystemMessage

# LangChain 1.1 の新機能（Optional）
try:
    from langchain.agents import create_agent
    from langchain.agents.middleware import (
        SummarizationMiddleware,
    )
    LANGCHAIN_V1_AVAILABLE = True
except ImportError:
    LANGCHAIN_V1_AVAILABLE = False

from .tools import get_current_weather, calculate


async def basic_example():
    """基本的なLangChain + Bedrock の使用例"""
    model = ChatBedrock(
        model_id=os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0"),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        model_kwargs={"temperature": 0.7},
    )

    messages = [
        SystemMessage(content="あなたは親切なAIアシスタントです。日本語で回答してください。"),
        HumanMessage(content="こんにちは！今日の天気を教えてください。"),
    ]

    print("LangChain + AWS Bedrock 実行中...")
    response = await model.ainvoke(messages)
    print(f"Response: {response.content}")


async def model_profiles_example():
    """Model Profiles機能の使用例（LangChain 1.1新機能）"""
    model = ChatBedrock(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        region_name="us-east-1",
    )

    # Model Profilesを確認
    if hasattr(model, "profile"):
        print(f"Model Profile: {model.profile}")
        print("- 構造化出力サポート:", getattr(model.profile, "structured_output", "N/A"))
        print("- 関数呼び出しサポート:", getattr(model.profile, "function_calling", "N/A"))
    else:
        print("Model Profiles は LangChain 1.1 以降で利用可能です")


async def create_agent_example():
    """create_agent APIの使用例（LangChain 1.1新機能）"""
    if not LANGCHAIN_V1_AVAILABLE:
        print("create_agent は LangChain 1.1 以降で利用可能です")
        print("pip install langchain>=1.1.0 を実行してください")
        return

    model = ChatBedrock(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        region_name="us-east-1",
    )

    # create_agentを使用してエージェント作成
    agent = create_agent(
        model=model,
        tools=[get_current_weather, calculate],
        system_prompt="あなたは親切なAIアシスタントです。ツールを適切に使用してください。",
    )

    # 実行
    result = await agent.ainvoke({
        "messages": [
            {"role": "user", "content": "東京の天気を教えてください。"}
        ]
    })

    print(f"Response: {result}")


async def middleware_example():
    """Middleware機能の使用例（LangChain 1.1新機能）"""
    if not LANGCHAIN_V1_AVAILABLE:
        print("Middleware は LangChain 1.1 以降で利用可能です")
        return

    model = ChatBedrock(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        region_name="us-east-1",
    )

    # ミドルウェア付きエージェント
    agent = create_agent(
        model=model,
        tools=[get_current_weather],
        system_prompt="あなたは親切なAIアシスタントです。",
        middleware=[
            # 要約ミドルウェア：長い会話を自動要約
            SummarizationMiddleware(
                model="us.anthropic.claude-sonnet-4-20250514-v1:0",
                trigger={"tokens": 500}
            ),
        ],
    )

    # 複数回の会話
    result1 = await agent.ainvoke({
        "messages": [{"role": "user", "content": "東京の天気を教えてください。"}]
    })
    print(f"Response 1: {result1}")

    result2 = await agent.ainvoke({
        "messages": [{"role": "user", "content": "大阪の天気も教えてください。"}]
    })
    print(f"Response 2: {result2}")


async def structured_output_example():
    """構造化出力の使用例（LangChain 1.1新機能）"""
    if not LANGCHAIN_V1_AVAILABLE:
        print("構造化出力の改善は LangChain 1.1 以降で利用可能です")
        return

    from pydantic import BaseModel

    class WeatherReport(BaseModel):
        location: str
        temperature: float
        condition: str

    model = ChatBedrock(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        region_name="us-east-1",
    )

    try:
        from langchain.agents.structured_output import ToolStrategy

        agent = create_agent(
            model=model,
            tools=[get_current_weather],
            response_format=ToolStrategy(WeatherReport),
        )

        result = await agent.ainvoke({
            "messages": [{"role": "user", "content": "東京の天気を教えてください。"}]
        })

        print(f"Structured Response: {result.get('structured_response')}")
    except ImportError:
        print("ToolStrategyのインポートに失敗しました")


async def langgraph_state_example():
    """LangGraph StateGraphの使用例（従来方式）"""
    from langgraph.graph import END, StateGraph
    from langgraph.graph.message import add_messages
    from langgraph.prebuilt import ToolNode
    from typing import Annotated
    from typing_extensions import TypedDict

    class AgentState(TypedDict):
        messages: Annotated[list, add_messages]

    model = ChatBedrock(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        region_name="us-east-1",
    )

    tools = [get_current_weather, calculate]
    model_with_tools = model.bind_tools(tools)

    def should_continue(state: AgentState) -> str:
        messages = state["messages"]
        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END

    async def call_model(state: AgentState) -> dict:
        messages = state["messages"]
        response = await model_with_tools.ainvoke(messages)
        return {"messages": [response]}

    # グラフ構築
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(tools))
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue)
    workflow.add_edge("tools", "agent")

    graph = workflow.compile()

    # 実行
    result = await graph.ainvoke({
        "messages": [
            SystemMessage(content="あなたは親切なAIアシスタントです。"),
            HumanMessage(content="123 * 456 を計算してください。"),
        ]
    })

    print(f"StateGraph Response: {result['messages'][-1].content}")


async def main():
    """メイン関数"""
    print("=" * 60)
    print("LangChain + LangGraph Examples - 2025年12月版")
    print("=" * 60)

    print("\n--- 基本的な使用例 ---")
    await basic_example()

    print("\n--- Model Profiles ---")
    await model_profiles_example()

    print("\n--- LangGraph StateGraph ---")
    await langgraph_state_example()

    # LangChain 1.1 の新機能（インストールされている場合）
    if LANGCHAIN_V1_AVAILABLE:
        print("\n--- create_agent API ---")
        await create_agent_example()

        print("\n--- Middleware ---")
        await middleware_example()

        print("\n--- 構造化出力 ---")
        await structured_output_example()
    else:
        print("\n--- LangChain 1.1 の新機能は利用できません ---")
        print("pip install langchain>=1.1.0 を実行してください")


if __name__ == "__main__":
    asyncio.run(main())
