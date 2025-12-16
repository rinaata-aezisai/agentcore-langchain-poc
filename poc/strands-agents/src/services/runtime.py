"""Strands Runtime Adapter

AgentCore Runtime サービスの実装。
エージェント実行環境とライフサイクル管理。
"""

import asyncio
import time
from typing import Any, AsyncIterator

from strands import Agent
from strands.models import BedrockModel

import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent.parent.parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_path))

from application.ports.runtime_port import (
    RuntimePort,
    RuntimeConfig,
    RuntimeStatus,
    ExecutionResult,
)


class StrandsRuntimeAdapter(RuntimePort):
    """Strands Agents Runtime アダプター
    
    AgentCore Runtimeの機能:
    - エージェント実行環境管理
    - ストリーミング応答
    - ツール統合
    - ライフサイクル制御
    """

    def __init__(self):
        self._config: RuntimeConfig | None = None
        self._model: BedrockModel | None = None
        self._agent: Agent | None = None
        self._status: RuntimeStatus = RuntimeStatus.INITIALIZING
        self._is_paused: bool = False

    async def initialize(self, config: RuntimeConfig) -> RuntimeStatus:
        """ランタイムを初期化"""
        try:
            self._config = config
            self._model = BedrockModel(
                model_id=config.model_id,
                region_name=config.region,
            )
            
            self._agent = Agent(
                model=self._model,
                system_prompt=config.system_prompt or self._default_system_prompt(),
            )
            
            self._status = RuntimeStatus.READY
            return self._status
        except Exception as e:
            self._status = RuntimeStatus.ERROR
            raise RuntimeError(f"Runtime initialization failed: {e}")

    async def execute(
        self,
        instruction: str,
        context: list[dict[str, Any]] | None = None,
    ) -> ExecutionResult:
        """同期実行"""
        if self._status != RuntimeStatus.READY:
            raise RuntimeError(f"Runtime not ready: {self._status}")
        
        self._status = RuntimeStatus.RUNNING
        start_time = time.time()
        
        try:
            # Strandsは同期APIなのでrun_in_executorで実行
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: self._agent(instruction)
            )
            
            execution_time = int((time.time() - start_time) * 1000)
            self._status = RuntimeStatus.READY
            
            return ExecutionResult(
                content=str(response),
                status=RuntimeStatus.READY,
                iterations=1,
                execution_time_ms=execution_time,
                metadata={
                    "provider": "strands-agents",
                    "model_id": self._config.model_id,
                },
            )
        except Exception as e:
            self._status = RuntimeStatus.ERROR
            raise RuntimeError(f"Execution failed: {e}")

    async def execute_stream(
        self,
        instruction: str,
        context: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[str]:
        """ストリーミング実行"""
        if self._status != RuntimeStatus.READY:
            raise RuntimeError(f"Runtime not ready: {self._status}")
        
        self._status = RuntimeStatus.RUNNING
        
        try:
            # Strands streaming (イベントベース)
            loop = asyncio.get_event_loop()
            
            # ストリーミング対応のAgent実行
            def stream_execute():
                chunks = []
                for event in self._agent.stream(instruction):
                    if hasattr(event, 'content'):
                        chunks.append(event.content)
                return chunks
            
            chunks = await loop.run_in_executor(None, stream_execute)
            
            for chunk in chunks:
                yield chunk
            
            self._status = RuntimeStatus.READY
        except Exception as e:
            self._status = RuntimeStatus.ERROR
            raise RuntimeError(f"Streaming execution failed: {e}")

    async def execute_with_tools(
        self,
        instruction: str,
        tools: list[Any],
        context: list[dict[str, Any]] | None = None,
    ) -> ExecutionResult:
        """ツール付き実行"""
        if self._status != RuntimeStatus.READY:
            raise RuntimeError(f"Runtime not ready: {self._status}")
        
        self._status = RuntimeStatus.RUNNING
        start_time = time.time()
        
        try:
            # ツール付きAgent作成
            agent_with_tools = Agent(
                model=self._model,
                system_prompt=self._config.system_prompt or self._default_system_prompt(),
                tools=tools,
            )
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: agent_with_tools(instruction)
            )
            
            execution_time = int((time.time() - start_time) * 1000)
            self._status = RuntimeStatus.READY
            
            # ツール呼び出し情報を抽出
            tool_calls = None
            if hasattr(response, 'tool_calls') and response.tool_calls:
                tool_calls = [
                    {
                        "tool_name": tc.name,
                        "tool_input": tc.input,
                        "tool_output": tc.output,
                    }
                    for tc in response.tool_calls
                ]
            
            return ExecutionResult(
                content=str(response),
                status=RuntimeStatus.READY,
                iterations=1,
                execution_time_ms=execution_time,
                tool_calls=tool_calls,
                metadata={
                    "provider": "strands-agents",
                    "model_id": self._config.model_id,
                    "tools_used": len(tools),
                },
            )
        except Exception as e:
            self._status = RuntimeStatus.ERROR
            raise RuntimeError(f"Tool execution failed: {e}")

    async def get_status(self) -> RuntimeStatus:
        """ステータス取得"""
        return self._status

    async def pause(self) -> bool:
        """一時停止"""
        if self._status == RuntimeStatus.RUNNING:
            self._is_paused = True
            self._status = RuntimeStatus.PAUSED
            return True
        return False

    async def resume(self) -> bool:
        """再開"""
        if self._status == RuntimeStatus.PAUSED:
            self._is_paused = False
            self._status = RuntimeStatus.READY
            return True
        return False

    async def terminate(self) -> bool:
        """終了"""
        self._status = RuntimeStatus.TERMINATED
        self._agent = None
        self._model = None
        return True

    @staticmethod
    def _default_system_prompt() -> str:
        return """あなたは親切で知識豊富なAIアシスタントです。
正確で有用な情報を提供し、不確かな場合は明確に伝えてください。"""


def create_strands_runtime() -> StrandsRuntimeAdapter:
    """ファクトリ関数"""
    return StrandsRuntimeAdapter()

