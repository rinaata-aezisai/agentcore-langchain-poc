"""Sessions Router - CQRS統合済み"""

from fastapi import APIRouter, HTTPException, status
from api.schemas.session import (
    CreateSessionRequest,
    CreateSessionResponse,
    SendInstructionRequest,
    SendInstructionResponse,
    SessionResponse,
    SessionListResponse,
    MessageListResponse,
)
from api.dependencies import (
    StartSessionHandlerDep,
    SendMessageHandlerDep,
    EndSessionHandlerDep,
    ExecuteAgentHandlerDep,
    GetSessionHandlerDep,
    GetSessionMessagesHandlerDep,
    GetActiveSessionsHandlerDep,
)
from application.commands import (
    StartSessionCommand,
    SendMessageCommand,
    EndSessionCommand,
    ExecuteAgentCommand,
)
from application.queries import (
    GetSessionQuery,
    GetSessionMessagesQuery,
    GetActiveSessionsQuery,
)
from application.handlers.command_handlers import SessionNotFoundError


router = APIRouter()


@router.post("", response_model=CreateSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: CreateSessionRequest,
    handler: StartSessionHandlerDep,
):
    """新しいセッションを作成"""
    command = StartSessionCommand(
        agent_id=request.agent_id or "default-agent",
        user_id=request.user_id or "anonymous",
    )
    session_id = await handler.handle(command)

    return CreateSessionResponse(
        session_id=session_id,
        agent_id=command.agent_id,
        created_at="",  # handlerから取得するように改善可能
    )


@router.get("", response_model=SessionListResponse)
async def list_active_sessions(
    user_id: str,
    handler: GetActiveSessionsHandlerDep,
):
    """ユーザーのアクティブセッション一覧を取得"""
    query = GetActiveSessionsQuery(user_id=user_id)
    sessions = await handler.handle(query)

    return SessionListResponse(
        sessions=[
            SessionResponse(
                session_id=s.id,
                agent_id=s.agent_id,
                state=s.state,
                created_at=s.created_at,
                message_count=s.message_count,
            )
            for s in sessions
        ],
        total_count=len(sessions),
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    handler: GetSessionHandlerDep,
):
    """セッション情報を取得"""
    query = GetSessionQuery(session_id=session_id)
    session = await handler.handle(query)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    return SessionResponse(
        session_id=session.id,
        agent_id=session.agent_id,
        state=session.state,
        created_at=session.created_at,
        message_count=session.message_count,
    )


@router.get("/{session_id}/messages", response_model=MessageListResponse)
async def get_session_messages(
    session_id: str,
    handler: GetSessionMessagesHandlerDep,
    limit: int = 50,
    offset: int = 0,
):
    """セッションのメッセージ一覧を取得"""
    query = GetSessionMessagesQuery(
        session_id=session_id,
        limit=limit,
        offset=offset,
    )
    messages = await handler.handle(query)

    return MessageListResponse(
        messages=[
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at,
            }
            for m in messages
        ],
        total_count=len(messages),
    )


@router.post("/{session_id}/messages", response_model=SendInstructionResponse)
async def send_message(
    session_id: str,
    request: SendInstructionRequest,
    send_handler: SendMessageHandlerDep,
    execute_handler: ExecuteAgentHandlerDep,
):
    """メッセージを送信してエージェントレスポンスを取得"""
    import time
    start_time = time.time()

    try:
        # ユーザーメッセージを追加
        send_command = SendMessageCommand(
            session_id=session_id,
            content=request.instruction,
        )
        await send_handler.handle(send_command)

        # エージェント実行
        execute_command = ExecuteAgentCommand(
            session_id=session_id,
            instruction=request.instruction,
            tools=request.tools,
        )
        result = await execute_handler.handle(execute_command)

        latency_ms = int((time.time() - start_time) * 1000)

        return SendInstructionResponse(
            response_id=result["message_id"],
            content=result["content"],
            tool_calls=result.get("tool_calls"),
            latency_ms=latency_ms,
            metadata=result.get("metadata"),
        )

    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def end_session(
    session_id: str,
    handler: EndSessionHandlerDep,
):
    """セッションを終了"""
    try:
        command = EndSessionCommand(session_id=session_id)
        await handler.handle(command)
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )
