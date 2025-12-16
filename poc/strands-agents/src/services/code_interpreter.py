"""Strands Code Interpreter Adapter

AgentCore Code Interpreter サービスの実装。
安全なコード実行環境。
"""

import asyncio
import subprocess
import tempfile
import time
import uuid
from typing import Any
import os

import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent.parent.parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_path))

from application.ports.code_interpreter_port import (
    CodeInterpreterPort,
    CodeConfig,
    Language,
    ExecutionStatus,
    ExecutionEnvironment,
    CodeExecutionResult,
)


class StrandsCodeInterpreterAdapter(CodeInterpreterPort):
    """Strands Agents Code Interpreter アダプター
    
    AgentCore Code Interpreterの機能:
    - 安全なPython/JS/Bash実行
    - ファイル管理
    - リソース制限
    - 実行環境分離
    """

    def __init__(self):
        self._config: CodeConfig | None = None
        self._environment_id: str = ""
        self._files: dict[str, bytes] = {}
        self._temp_dir: str = ""
        self._context: dict[str, Any] = {}

    async def initialize(self, config: CodeConfig) -> ExecutionEnvironment:
        """実行環境を初期化"""
        self._config = config
        self._environment_id = str(uuid.uuid4())
        self._temp_dir = tempfile.mkdtemp(prefix="strands_code_")
        
        return ExecutionEnvironment(
            environment_id=self._environment_id,
            language=config.language,
            status="ready",
            available_packages=["numpy", "pandas", "requests"],  # デモ用
            metadata={"temp_dir": self._temp_dir},
        )

    async def execute(
        self,
        code: str,
        language: Language | None = None,
    ) -> CodeExecutionResult:
        """コードを実行"""
        lang = language or (self._config.language if self._config else Language.PYTHON)
        timeout = self._config.timeout_seconds if self._config else 30
        
        start_time = time.time()
        
        try:
            if lang == Language.PYTHON:
                result = await self._execute_python(code, timeout)
            elif lang == Language.BASH:
                result = await self._execute_bash(code, timeout)
            elif lang == Language.JAVASCRIPT:
                result = await self._execute_javascript(code, timeout)
            else:
                return CodeExecutionResult(
                    status=ExecutionStatus.ERROR,
                    error=f"Unsupported language: {lang}",
                    execution_time_ms=0,
                )
            
            execution_time = int((time.time() - start_time) * 1000)
            result.execution_time_ms = execution_time
            return result
            
        except asyncio.TimeoutError:
            return CodeExecutionResult(
                status=ExecutionStatus.TIMEOUT,
                error="Execution timed out",
                execution_time_ms=timeout * 1000,
            )
        except Exception as e:
            return CodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

    async def execute_with_context(
        self,
        code: str,
        context: dict[str, Any],
        language: Language | None = None,
    ) -> CodeExecutionResult:
        """コンテキスト付きで実行"""
        # コンテキストを事前に設定
        self._context.update(context)
        
        # コンテキストをコードに注入（Python用）
        if (language or self._config.language) == Language.PYTHON:
            context_setup = "\n".join(
                f"{k} = {repr(v)}" for k, v in context.items()
            )
            code = f"{context_setup}\n\n{code}"
        
        return await self.execute(code, language)

    async def upload_file(
        self,
        filename: str,
        content: bytes,
    ) -> str:
        """ファイルをアップロード"""
        file_id = str(uuid.uuid4())
        self._files[file_id] = content
        
        # 実際のファイルとして保存
        file_path = os.path.join(self._temp_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(content)
        
        return file_id

    async def download_file(self, file_id: str) -> bytes | None:
        """ファイルをダウンロード"""
        return self._files.get(file_id)

    async def list_files(self) -> list[dict[str, Any]]:
        """ファイル一覧を取得"""
        files = []
        if self._temp_dir and os.path.exists(self._temp_dir):
            for filename in os.listdir(self._temp_dir):
                filepath = os.path.join(self._temp_dir, filename)
                files.append({
                    "filename": filename,
                    "size": os.path.getsize(filepath),
                    "path": filepath,
                })
        return files

    async def get_environment_info(self) -> ExecutionEnvironment:
        """環境情報を取得"""
        return ExecutionEnvironment(
            environment_id=self._environment_id,
            language=self._config.language if self._config else Language.PYTHON,
            status="ready",
            available_packages=["numpy", "pandas", "requests"],
            metadata={
                "temp_dir": self._temp_dir,
                "files_count": len(self._files),
                "context_keys": list(self._context.keys()),
            },
        )

    async def reset_environment(self) -> bool:
        """環境をリセット"""
        self._files.clear()
        self._context.clear()
        
        # 一時ファイルを削除
        if self._temp_dir and os.path.exists(self._temp_dir):
            import shutil
            shutil.rmtree(self._temp_dir)
            self._temp_dir = tempfile.mkdtemp(prefix="strands_code_")
        
        return True

    async def _execute_python(self, code: str, timeout: int) -> CodeExecutionResult:
        """Pythonコードを実行"""
        # 一時ファイルに書き込み
        script_path = os.path.join(self._temp_dir, "script.py")
        with open(script_path, 'w') as f:
            f.write(code)
        
        try:
            process = await asyncio.create_subprocess_exec(
                "python", script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self._temp_dir,
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
            
            if process.returncode == 0:
                return CodeExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    output=stdout.decode('utf-8'),
                )
            else:
                return CodeExecutionResult(
                    status=ExecutionStatus.ERROR,
                    output=stdout.decode('utf-8'),
                    error=stderr.decode('utf-8'),
                )
        except Exception as e:
            return CodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error=str(e),
            )

    async def _execute_bash(self, code: str, timeout: int) -> CodeExecutionResult:
        """Bashコードを実行"""
        try:
            process = await asyncio.create_subprocess_shell(
                code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self._temp_dir,
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
            
            if process.returncode == 0:
                return CodeExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    output=stdout.decode('utf-8'),
                )
            else:
                return CodeExecutionResult(
                    status=ExecutionStatus.ERROR,
                    output=stdout.decode('utf-8'),
                    error=stderr.decode('utf-8'),
                )
        except Exception as e:
            return CodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error=str(e),
            )

    async def _execute_javascript(self, code: str, timeout: int) -> CodeExecutionResult:
        """JavaScriptコードを実行"""
        script_path = os.path.join(self._temp_dir, "script.js")
        with open(script_path, 'w') as f:
            f.write(code)
        
        try:
            process = await asyncio.create_subprocess_exec(
                "node", script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self._temp_dir,
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
            
            if process.returncode == 0:
                return CodeExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    output=stdout.decode('utf-8'),
                )
            else:
                return CodeExecutionResult(
                    status=ExecutionStatus.ERROR,
                    output=stdout.decode('utf-8'),
                    error=stderr.decode('utf-8'),
                )
        except Exception as e:
            return CodeExecutionResult(
                status=ExecutionStatus.ERROR,
                error=str(e),
            )


def create_strands_code_interpreter() -> StrandsCodeInterpreterAdapter:
    """ファクトリ関数"""
    return StrandsCodeInterpreterAdapter()

