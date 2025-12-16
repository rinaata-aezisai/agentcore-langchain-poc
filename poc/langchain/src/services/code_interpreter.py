"""LangChain Code Interpreter Adapter

LangChain PythonREPL / E2B による実装。
安全なコード実行環境。
"""

import asyncio
import os
import tempfile
import time
import uuid
from typing import Any

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


class LangChainCodeInterpreterAdapter(CodeInterpreterPort):
    """LangChain Code Interpreter アダプター
    
    LangChain相当機能:
    - PythonREPL
    - E2B Code Interpreter
    - Shell Tool
    """

    def __init__(self):
        self._config: CodeConfig | None = None
        self._environment_id: str = ""
        self._files: dict[str, bytes] = {}
        self._temp_dir: str = ""
        self._repl = None
        self._context: dict[str, Any] = {}

    async def initialize(self, config: CodeConfig) -> ExecutionEnvironment:
        """実行環境を初期化"""
        self._config = config
        self._environment_id = str(uuid.uuid4())
        self._temp_dir = tempfile.mkdtemp(prefix="langchain_code_")
        
        # PythonREPLを初期化（可能な場合）
        try:
            from langchain_experimental.utilities import PythonREPL
            self._repl = PythonREPL()
        except ImportError:
            self._repl = None
        
        return ExecutionEnvironment(
            environment_id=self._environment_id,
            language=config.language,
            status="ready",
            available_packages=["numpy", "pandas", "requests", "langchain"],
            metadata={
                "temp_dir": self._temp_dir,
                "repl_available": self._repl is not None,
            },
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
            else:
                return CodeExecutionResult(
                    status=ExecutionStatus.ERROR,
                    error=f"Unsupported language: {lang}",
                )
            
            result.execution_time_ms = int((time.time() - start_time) * 1000)
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
        self._context.update(context)
        
        if (language or self._config.language) == Language.PYTHON:
            context_setup = "\n".join(
                f"{k} = {repr(v)}" for k, v in context.items()
            )
            code = f"{context_setup}\n\n{code}"
        
        return await self.execute(code, language)

    async def _execute_python(self, code: str, timeout: int) -> CodeExecutionResult:
        """Pythonコードを実行"""
        # LangChain PythonREPLを使用（可能な場合）
        if self._repl:
            try:
                loop = asyncio.get_event_loop()
                output = await asyncio.wait_for(
                    loop.run_in_executor(None, self._repl.run, code),
                    timeout=timeout,
                )
                return CodeExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    output=output,
                    metadata={"executor": "langchain-repl"},
                )
            except Exception as e:
                return CodeExecutionResult(
                    status=ExecutionStatus.ERROR,
                    error=str(e),
                )
        
        # フォールバック: subprocess
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
                    metadata={"executor": "subprocess"},
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

    async def upload_file(
        self,
        filename: str,
        content: bytes,
    ) -> str:
        """ファイルをアップロード"""
        file_id = str(uuid.uuid4())
        self._files[file_id] = content
        
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
            available_packages=["numpy", "pandas", "requests", "langchain"],
            metadata={
                "temp_dir": self._temp_dir,
                "files_count": len(self._files),
                "repl_available": self._repl is not None,
            },
        )

    async def reset_environment(self) -> bool:
        """環境をリセット"""
        self._files.clear()
        self._context.clear()
        
        if self._temp_dir and os.path.exists(self._temp_dir):
            import shutil
            shutil.rmtree(self._temp_dir)
            self._temp_dir = tempfile.mkdtemp(prefix="langchain_code_")
        
        return True


def create_langchain_code_interpreter() -> LangChainCodeInterpreterAdapter:
    """ファクトリ関数"""
    return LangChainCodeInterpreterAdapter()

