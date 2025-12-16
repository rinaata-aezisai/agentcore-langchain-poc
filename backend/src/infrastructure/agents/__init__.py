"""Infrastructure Agents - AgentCore Runtime Integration

AgentCore Runtime経由でECRにデプロイされたエージェントを呼び出すための実装。
"""

from .agentcore_runtime_adapter import AgentCoreRuntimeAdapter

__all__ = ["AgentCoreRuntimeAdapter"]
