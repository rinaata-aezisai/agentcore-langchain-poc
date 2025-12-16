"""Strands Agent Adapter

AWS Bedrock AgentCore (Strands Agents) の実装。
backendのAgentPortを実装し、DIで注入可能。
"""

import sys
from pathlib import Path
from typing import Any

# backendモジュールをパスに追加
backend_path = Path(__file__).parent.parent.parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_path))

from strands import Agent
from strands.models import BedrockModel

from domain.entities.message import Message
from application.ports.agent_port import AgentPort, AgentResponse


class StrandsAgentAdapter(AgentPort):
    """Strands Agents アダプター (AgentCore実装)"""

    def __init__(
        self,
        model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0",
        region: str = "us-east-1",
        system_prompt: str | None = None,
    ):
        self.model = BedrockModel(model_id=model_id, region_name=region)
        self.system_prompt = system_prompt or self._default_system_prompt()

    async def execute(self, context: list[Message], instruction: str) -> AgentResponse:
        agent = Agent(model=self.model, system_prompt=self.system_prompt)
        response = agent(instruction)
        return AgentResponse(content=str(response), metadata={"provider": "strands"})

    async def execute_with_tools(
        self, context: list[Message], instruction: str, tools: list[dict[str, Any]],
    ) -> AgentResponse:
        agent = Agent(model=self.model, system_prompt=self.system_prompt, tools=tools)
        response = agent(instruction)
        return AgentResponse(
            content=str(response),
            tool_calls=self._extract_tool_calls(response),
            metadata={"provider": "strands"},
        )

    def _extract_tool_calls(self, response) -> list[dict[str, Any]] | None:
        # Strandsのレスポンス形式に応じて実装
        return None

    @staticmethod
    def _default_system_prompt() -> str:
        return "あなたは親切で知識豊富なAIアシスタントです。"


