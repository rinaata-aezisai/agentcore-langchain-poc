"""Send Instruction Use Case"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from domain.entities.message import Message, ToolCall
from domain.repositories.session_repository import SessionRepository
from domain.value_objects.content import Content
from domain.value_objects.ids import SessionId
from application.ports.agent_port import AgentPort


@dataclass
class SendInstructionInput:
    session_id: str
    content: str
    metadata: dict[str, Any] | None = None


@dataclass
class SendInstructionOutput:
    response_id: str
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    latency_ms: int = 0


class SendInstructionUseCase:
    def __init__(self, session_repository: SessionRepository, agent: AgentPort):
        self.session_repository = session_repository
        self.agent = agent

    async def execute(self, input: SendInstructionInput) -> SendInstructionOutput:
        start_time = datetime.utcnow()

        # 1. セッション取得
        session = await self.session_repository.find_by_id(SessionId(input.session_id))
        if session is None:
            raise SessionNotFoundError(input.session_id)

        # 2. ユーザーメッセージ追加
        user_message = Message.user(Content.from_text(input.content), input.metadata)
        session.add_message(user_message)

        # 3. エージェント実行
        context = session.get_context(limit=10)
        agent_response = await self.agent.execute(context, input.content)

        # 4. アシスタントメッセージ追加
        tool_calls = [
            ToolCall(tool_id=tc["tool_id"], params=tc["params"], result=tc.get("result"))
            for tc in (agent_response.tool_calls or [])
        ]
        assistant_message = Message.assistant(
            Content.from_text(agent_response.content), tool_calls,
        )
        session.add_message(assistant_message)

        # 5. 保存
        await self.session_repository.save(session)

        latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        return SendInstructionOutput(
            response_id=str(assistant_message.id),
            content=agent_response.content,
            tool_calls=[{"tool_id": tc.tool_id, "result": tc.result} for tc in tool_calls] if tool_calls else None,
            latency_ms=latency_ms,
        )


class SessionNotFoundError(Exception):
    def __init__(self, session_id: str):
        super().__init__(f"Session not found: {session_id}")


