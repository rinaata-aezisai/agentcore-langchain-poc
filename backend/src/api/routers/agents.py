"""Agents Router"""

from fastapi import APIRouter
from pydantic import BaseModel, Field


router = APIRouter()


class AgentResponse(BaseModel):
    agent_id: str
    name: str
    description: str | None = None
    model_id: str


class AgentListResponse(BaseModel):
    agents: list[AgentResponse]


@router.get("", response_model=AgentListResponse)
async def list_agents():
    return AgentListResponse(agents=[
        AgentResponse(
            agent_id="default-agent",
            name="Default Support Agent",
            description="一般的なサポート質問に回答するエージェント",
            model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
        ),
    ])


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    return AgentResponse(
        agent_id=agent_id,
        name="Default Support Agent",
        description="一般的なサポート質問に回答するエージェント",
        model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
    )


