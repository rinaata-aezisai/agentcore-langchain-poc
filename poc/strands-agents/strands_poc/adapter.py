"""Strands Agent Adapter

AWS Bedrock AgentCore (Strands Agents) の実装。
backendのAgentPortを実装し、DIで注入可能。
"""

import asyncio
import os
from typing import Any

from strands import Agent
from strands.models import BedrockModel

from application.ports.agent_port import AgentPort, AgentResponse
from domain.entities.message import Message

from .tools import AVAILABLE_TOOLS


class StrandsAgentAdapter(AgentPort):
    """Strands Agents アダプター (AgentCore実装)"""

    def __init__(
        self,
        model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0",
        region: str = "us-east-1",
        system_prompt: str | None = None,
        enable_memory: bool = False,
    ):
        self.model = BedrockModel(model_id=model_id, region_name=region)
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.enable_memory = enable_memory
        self._conversation_history: list[dict[str, str]] = []

    async def execute(self, context: list[Message], instruction: str) -> AgentResponse:
        """エージェントを実行（ツールなし）"""
        agent = Agent(
            model=self.model,
            system_prompt=self.system_prompt,
        )

        # Strandsは同期APIなのでrun_in_executorで実行
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: agent(instruction))

        return AgentResponse(
            content=str(response),
            metadata={
                "provider": "strands-agents",
                "model_id": self.model.model_id,
            },
        )

    async def execute_with_tools(
        self,
        context: list[Message],
        instruction: str,
        tools: list[dict[str, Any]] | None = None,
    ) -> AgentResponse:
        """ツール付きでエージェントを実行"""
        agent_tools = tools if tools else AVAILABLE_TOOLS

        agent = Agent(
            model=self.model,
            system_prompt=self.system_prompt,
            tools=agent_tools,
        )

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: agent(instruction))

        return AgentResponse(
            content=str(response),
            tool_calls=self._extract_tool_calls(response),
            metadata={
                "provider": "strands-agents",
                "model_id": self.model.model_id,
                "tools_available": len(agent_tools),
            },
        )

    def _extract_tool_calls(self, response) -> list[dict[str, Any]] | None:
        """レスポンスからツール呼び出し情報を抽出"""
        if hasattr(response, "tool_calls") and response.tool_calls:
            return [
                {
                    "tool_name": tc.name,
                    "tool_input": tc.input,
                    "tool_output": tc.output,
                }
                for tc in response.tool_calls
            ]
        return None

    @staticmethod
    def _default_system_prompt() -> str:
        return """あなたは親切で知識豊富なAIアシスタントです。

以下の原則に従って応答してください：
1. 正確で有用な情報を提供する
2. 不確かな場合は明確に伝える
3. ツールが利用可能な場合は適切に活用する
4. 日本語で応答する（ユーザーが英語の場合は英語で）
"""


def create_strands_adapter(
    model_id: str | None = None,
    region: str | None = None,
    system_prompt: str | None = None,
) -> StrandsAgentAdapter:
    """StrandsAgentAdapterのファクトリ関数"""
    default_model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    return StrandsAgentAdapter(
        model_id=model_id or os.getenv("BEDROCK_MODEL_ID", default_model_id),
        region=region or os.getenv("AWS_REGION", "us-east-1"),
        system_prompt=system_prompt,
    )
