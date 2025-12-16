"""Sessions Router"""

from fastapi import APIRouter, HTTPException, status
from api.schemas.session import (
    CreateSessionRequest, CreateSessionResponse,
    SendInstructionRequest, SendInstructionResponse,
    SessionListResponse,
)


router = APIRouter()


@router.post("", response_model=CreateSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(request: CreateSessionRequest):
    # TODO: DI実装後にユースケース呼び出し
    return CreateSessionResponse(
        session_id="test-session-id",
        agent_id=request.agent_id or "default-agent",
        created_at="2025-12-16T00:00:00Z",
    )


@router.get("", response_model=SessionListResponse)
async def list_sessions(limit: int = 20):
    return SessionListResponse(sessions=[], total_count=0)


@router.post("/{session_id}/messages", response_model=SendInstructionResponse)
async def send_instruction(session_id: str, request: SendInstructionRequest):
    # TODO: DI実装後にユースケース呼び出し
    return SendInstructionResponse(
        response_id="test-response-id",
        content="This is a test response.",
        latency_ms=100,
    )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def end_session(session_id: str):
    pass


