"""Code Interpreter Port - Code Execution Service Interface

AgentCore Code Interpreter / LangChain PythonREPL に対応。
安全なコード実行環境。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class ExecutionStatus(str, Enum):
    """実行ステータス"""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class Language(str, Enum):
    """対応言語"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    BASH = "bash"
    SQL = "sql"


@dataclass
class CodeConfig:
    """コード実行設定"""
    language: Language = Language.PYTHON
    timeout_seconds: int = 30
    max_memory_mb: int = 512
    enable_network: bool = False
    enable_filesystem: bool = False
    allowed_imports: list[str] = field(default_factory=list)
    environment_vars: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionEnvironment:
    """実行環境情報"""
    environment_id: str
    language: Language
    status: str
    available_packages: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CodeExecutionResult:
    """コード実行結果"""
    status: ExecutionStatus
    output: str = ""
    error: str | None = None
    execution_time_ms: int = 0
    memory_used_mb: float = 0.0
    artifacts: list[dict[str, Any]] = field(default_factory=list)  # files, images, etc.
    metadata: dict[str, Any] = field(default_factory=dict)


class CodeInterpreterPort(ABC):
    """Code Interpreter Port - コード実行

    Strands Agents: AgentCore Code Interpreter
    LangChain: PythonREPL / E2B Code Interpreter
    """

    @abstractmethod
    async def initialize(self, config: CodeConfig) -> ExecutionEnvironment:
        """実行環境を初期化"""
        ...

    @abstractmethod
    async def execute(
        self,
        code: str,
        language: Language | None = None,
    ) -> CodeExecutionResult:
        """コードを実行"""
        ...

    @abstractmethod
    async def execute_with_context(
        self,
        code: str,
        context: dict[str, Any],
        language: Language | None = None,
    ) -> CodeExecutionResult:
        """コンテキスト付きで実行"""
        ...

    @abstractmethod
    async def upload_file(
        self,
        filename: str,
        content: bytes,
    ) -> str:
        """ファイルをアップロード"""
        ...

    @abstractmethod
    async def download_file(self, file_id: str) -> bytes | None:
        """ファイルをダウンロード"""
        ...

    @abstractmethod
    async def list_files(self) -> list[dict[str, Any]]:
        """ファイル一覧を取得"""
        ...

    @abstractmethod
    async def get_environment_info(self) -> ExecutionEnvironment:
        """環境情報を取得"""
        ...

    @abstractmethod
    async def reset_environment(self) -> bool:
        """環境をリセット"""
        ...

