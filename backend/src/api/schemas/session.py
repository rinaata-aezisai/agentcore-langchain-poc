"""Session API Schemas"""

from typing import Any
from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    """セッション作成リクエスト"""

    agent_id: str | None = Field(None, description="エージェントID")
    user_id: str | None = Field(None, description="ユーザーID")
    metadata: dict[str, Any] | None = Field(None, description="メタデータ")


class CreateSessionResponse(BaseModel):
    """セッション作成レスポンス"""

    session_id: str
    agent_id: str
    created_at: str


class SendInstructionRequest(BaseModel):
    """命令送信リクエスト"""

    instruction: str = Field(..., description="エージェントへの命令")
    tools: list[dict[str, Any]] | None = Field(None, description="使用するツール")
    metadata: dict[str, Any] | None = Field(None, description="メタデータ")


class SendInstructionResponse(BaseModel):
    """命令送信レスポンス"""

    response_id: str
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    latency_ms: int
    metadata: dict[str, Any] | None = None


class SessionResponse(BaseModel):
    """セッション情報レスポンス"""

    session_id: str
    agent_id: str
    state: str
    created_at: str
    message_count: int


class SessionListResponse(BaseModel):
    """セッション一覧レスポンス"""

    sessions: list[SessionResponse]
    total_count: int


class MessageResponse(BaseModel):
    """メッセージレスポンス"""

    id: str
    role: str
    content: str
    created_at: str


class MessageListResponse(BaseModel):
    """メッセージ一覧レスポンス"""

    messages: list[dict[str, Any]]
    total_count: int
