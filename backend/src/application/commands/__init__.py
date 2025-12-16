"""CQRS Commands

コマンド（書き込み操作）の定義。
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class Command:
    """コマンド基底クラス"""

    pass


@dataclass
class StartSessionCommand(Command):
    """セッション開始コマンド"""

    agent_id: str
    user_id: str


@dataclass
class SendMessageCommand(Command):
    """メッセージ送信コマンド"""

    session_id: str
    content: str
    metadata: dict[str, Any] | None = None


@dataclass
class EndSessionCommand(Command):
    """セッション終了コマンド"""

    session_id: str
    reason: str = "user_requested"


@dataclass
class ExecuteAgentCommand(Command):
    """エージェント実行コマンド"""

    session_id: str
    instruction: str
    tools: list[dict[str, Any]] | None = None

