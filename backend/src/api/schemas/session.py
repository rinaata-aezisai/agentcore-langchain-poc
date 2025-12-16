"""Session Schemas"""

from typing import Any
from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    agent_id: str | None = None
    metadata: dict[str, Any] | None = None


class CreateSessionResponse(BaseModel):
    session_id: str
    agent_id: str
    created_at: str


class SendInstructionRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    metadata: dict[str, Any] | None = None


class ToolCallResponse(BaseModel):
    tool_id: str
    result: Any = None


class SendInstructionResponse(BaseModel):
    response_id: str
    content: str
    tool_calls: list[ToolCallResponse] | None = None
    latency_ms: int


class SessionResponse(BaseModel):
    session_id: str
    agent_id: str
    state: str
    message_count: int
    created_at: str


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]
    next_cursor: str | None = None
    total_count: int


