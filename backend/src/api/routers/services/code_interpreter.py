"""Code Interpreter Service Router

コード実行サービスAPIエンドポイント。
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Any
from enum import Enum

router = APIRouter(prefix="/code-interpreter", tags=["Code Interpreter"])


class AgentType(str, Enum):
    STRANDS = "strands"
    LANGCHAIN = "langchain"


class Language(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    BASH = "bash"
    SQL = "sql"


class CodeConfigRequest(BaseModel):
    agent_type: AgentType = AgentType.STRANDS
    language: Language = Language.PYTHON
    timeout_seconds: int = 30
    max_memory_mb: int = 512


class ExecuteCodeRequest(BaseModel):
    code: str
    language: Language | None = None


class ExecuteWithContextRequest(BaseModel):
    code: str
    context: dict[str, Any]
    language: Language | None = None


@router.post("/initialize")
async def initialize_code_interpreter(config: CodeConfigRequest):
    """実行環境を初期化"""
    return {
        "environment_id": "env-123",
        "language": config.language.value,
        "status": "ready",
        "agent_type": config.agent_type.value,
    }


@router.post("/execute")
async def execute_code(request: ExecuteCodeRequest, agent_type: AgentType = AgentType.STRANDS):
    """コードを実行"""
    return {
        "status": "success",
        "output": f"Executed: {request.code[:50]}...",
        "execution_time_ms": 100,
        "agent_type": agent_type.value,
    }


@router.post("/execute-with-context")
async def execute_with_context(request: ExecuteWithContextRequest, agent_type: AgentType = AgentType.STRANDS):
    """コンテキスト付きで実行"""
    return {
        "status": "success",
        "output": f"Executed with {len(request.context)} context vars",
        "execution_time_ms": 150,
        "agent_type": agent_type.value,
    }


@router.post("/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    agent_type: AgentType = AgentType.STRANDS,
):
    """ファイルをアップロード"""
    return {
        "file_id": "file-123",
        "filename": file.filename,
        "size": 0,
        "agent_type": agent_type.value,
    }


@router.get("/files/{file_id}")
async def download_file(file_id: str, agent_type: AgentType = AgentType.STRANDS):
    """ファイルをダウンロード"""
    raise HTTPException(status_code=404, detail="File not found")


@router.get("/files")
async def list_files(agent_type: AgentType = AgentType.STRANDS):
    """ファイル一覧を取得"""
    return {
        "files": [],
        "agent_type": agent_type.value,
    }


@router.get("/environment")
async def get_environment_info(agent_type: AgentType = AgentType.STRANDS):
    """環境情報を取得"""
    return {
        "environment_id": "env-123",
        "language": "python",
        "status": "ready",
        "available_packages": ["numpy", "pandas"],
        "agent_type": agent_type.value,
    }


@router.post("/reset")
async def reset_environment(agent_type: AgentType = AgentType.STRANDS):
    """環境をリセット"""
    return {
        "reset": True,
        "agent_type": agent_type.value,
    }

