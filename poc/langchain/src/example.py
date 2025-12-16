"""LangChain + LangGraph 使用例"""

import asyncio
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage


async def main():
    # モデル設定
    model = ChatAnthropic(
        model="claude-3-5-sonnet-20241022",
        temperature=0.7,
    )

    # メッセージ
    messages = [
        SystemMessage(content="あなたは親切なAIアシスタントです。日本語で回答してください。"),
        HumanMessage(content="こんにちは！今日の天気を教えてください。"),
    ]

    # 実行
    response = await model.ainvoke(messages)
    print(f"Response: {response.content}")


if __name__ == "__main__":
    asyncio.run(main())


