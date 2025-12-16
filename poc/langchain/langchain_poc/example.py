"""LangChain + LangGraph 使用例

AWS Bedrockを使用したLangChainの実装例（Strands Agentsとの公平な比較のため）
"""

import asyncio
import os

from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage, SystemMessage


async def main():
    """LangChain + Bedrock の基本的な使用例"""
    # モデル設定（AWS Bedrockを使用）
    model = ChatBedrock(
        model_id=os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        model_kwargs={"temperature": 0.7},
    )

    # メッセージ
    messages = [
        SystemMessage(content="あなたは親切なAIアシスタントです。日本語で回答してください。"),
        HumanMessage(content="こんにちは！今日の天気を教えてください。"),
    ]

    # 実行
    print("LangChain + AWS Bedrock 実行中...")
    response = await model.ainvoke(messages)
    print(f"Response: {response.content}")


if __name__ == "__main__":
    asyncio.run(main())
