"""Strands Agents 使用例"""

from strands import Agent
from strands.models import BedrockModel


def main():
    # モデル設定
    model = BedrockModel(
        model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
        region_name="us-east-1",
    )

    # エージェント作成
    agent = Agent(
        model=model,
        system_prompt="あなたは親切なAIアシスタントです。日本語で回答してください。",
    )

    # 実行
    response = agent("こんにちは！今日の天気を教えてください。")
    print(f"Response: {response}")


if __name__ == "__main__":
    main()


