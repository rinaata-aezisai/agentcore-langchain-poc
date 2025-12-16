"""FastAPI Dependencies - Dependency Injection Configuration

DIコンテナとしてFastAPIのDependsを使用。

接続モード:
1. AgentCore Runtime (本番推奨):
   - AGENT_RUNTIME_ARN が設定されている場合
   - invoke_agent_runtime() でECRにデプロイされたエージェントを呼び出し

2. Direct Bedrock (開発/テスト用):
   - AGENT_RUNTIME_ARN が未設定の場合
   - strands_poc/langchain_poc 経由でBedrockを直接呼び出し

3. Mock (ローカル開発用):
   - ENVIRONMENT=development の場合
   - AWS認証不要のモックレスポンス
"""

import os
from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from application.handlers.command_handlers import (
    EndSessionHandler,
    ExecuteAgentHandler,
    SendMessageHandler,
    StartSessionHandler,
)
from application.handlers.query_handlers import (
    GetActiveSessionsHandler,
    GetSessionHandler,
    GetSessionMessagesHandler,
)
from application.ports.agent_port import AgentPort
from domain.repositories.session_repository import SessionRepository
from infrastructure.messaging.event_publisher import (
    EventBridgePublisher,
    EventPublisher,
    InMemoryEventPublisher,
)
from infrastructure.persistence.event_store import (
    DynamoDBEventStore,
    EventStore,
    InMemoryEventStore,
)
from infrastructure.persistence.session_repository_impl import EventSourcedSessionRepository

# ===========================================
# Configuration
# ===========================================

class Settings:
    """アプリケーション設定"""

    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.agent_type = os.getenv("AGENT_TYPE", "strands")  # strands or langchain
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        self.event_table_name = os.getenv("EVENT_TABLE_NAME", "agentcore-poc-events")
        self.event_bus_name = os.getenv("EVENT_BUS_NAME", "agentcore-poc-events")
        self.bedrock_model_id = os.getenv(
            "BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"
        )
        self.langfuse_enabled = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"

        # AgentCore Runtime設定 (本番環境用)
        # ARNが設定されている場合はAgentCore Runtime経由で接続
        self.agent_runtime_arn = os.getenv("AGENT_RUNTIME_ARN")
        self.agent_runtime_qualifier = os.getenv("AGENT_RUNTIME_QUALIFIER", "DEFAULT")


@lru_cache
def get_settings() -> Settings:
    return Settings()


# ===========================================
# Infrastructure Dependencies
# ===========================================

def get_event_store(settings: Annotated[Settings, Depends(get_settings)]) -> EventStore:
    """EventStoreのDI"""
    if settings.environment == "development":
        return InMemoryEventStore()
    return DynamoDBEventStore(
        table_name=settings.event_table_name,
        region=settings.aws_region,
    )


def get_event_publisher(settings: Annotated[Settings, Depends(get_settings)]) -> EventPublisher:
    """EventPublisherのDI"""
    if settings.environment == "development":
        return InMemoryEventPublisher()
    return EventBridgePublisher(
        event_bus_name=settings.event_bus_name,
        region=settings.aws_region,
    )


def get_session_repository(
    event_store: Annotated[EventStore, Depends(get_event_store)]
) -> SessionRepository:
    """SessionRepositoryのDI"""
    return EventSourcedSessionRepository(event_store)


# ===========================================
# Agent Port Dependencies
# ===========================================

def get_agent_port(settings: Annotated[Settings, Depends(get_settings)]) -> AgentPort:
    """AgentPortのDI - 環境と設定で切り替え

    優先順位:
    1. development環境 → MockAgentPort（AWS認証不要）
    2. AGENT_RUNTIME_ARN設定あり → AgentCore Runtime経由（本番推奨）
    3. それ以外 → Direct Bedrock（strands/langchain）
    """
    # 1. 開発環境ではモックエージェントを使用（AWS認証不要）
    if settings.environment == "development":
        print("Using MockAgentPort for development environment")
        return MockAgentPort()

    # 2. AGENT_RUNTIME_ARNが設定されている場合はAgentCore Runtime経由
    if settings.agent_runtime_arn:
        print(f"Using AgentCore Runtime: {settings.agent_runtime_arn}")
        try:
            from infrastructure.agents.agentcore_runtime_adapter import (
                create_agentcore_runtime_adapter,
            )
            return create_agentcore_runtime_adapter(
                agent_runtime_arn=settings.agent_runtime_arn,
                region=settings.aws_region,
                qualifier=settings.agent_runtime_qualifier,
            )
        except ImportError as e:
            print(f"Warning: Failed to import agentcore_runtime_adapter: {e}")
            return MockAgentPort()

    # 3. Direct Bedrock（フォールバック）
    print(f"Using Direct Bedrock with {settings.agent_type}")
    if settings.agent_type == "langchain":
        try:
            from langchain_poc.adapter import create_langchain_adapter
            return create_langchain_adapter(
                model_id=settings.bedrock_model_id,
                region=settings.aws_region,
            )
        except ImportError:
            print("Warning: langchain_poc not installed, using mock agent")
            return MockAgentPort()
    else:
        try:
            from strands_poc.adapter import create_strands_adapter
            return create_strands_adapter(
                model_id=settings.bedrock_model_id,
                region=settings.aws_region,
            )
        except ImportError:
            print("Warning: strands_poc not installed, using mock agent")
            return MockAgentPort()


class MockAgentPort(AgentPort):
    """開発用モックエージェント（AWS認証不要）"""

    async def execute(self, context, instruction: str):
        """モック実行"""
        from application.ports.agent_port import AgentResponse
        return AgentResponse(
            content=f"[Mock Response] あなたのメッセージ: {instruction}\n\nこれは開発環境のモックレスポンスです。本番環境ではAWS Bedrockを通じて実際のLLMが応答します。",
            metadata={
                "provider": "mock",
                "model_id": "mock-model",
                "latency_ms": 100,
            },
        )

    async def execute_with_tools(self, context, instruction: str, tools=None):
        """モック実行（ツール付き）"""
        from application.ports.agent_port import AgentResponse
        tool_info = f"利用可能なツール: {len(tools) if tools else 0}個" if tools else ""
        return AgentResponse(
            content=f"[Mock Response with Tools] あなたのメッセージ: {instruction}\n{tool_info}\n\nこれは開発環境のモックレスポンスです。",
            tool_calls=None,
            metadata={
                "provider": "mock",
                "model_id": "mock-model",
                "latency_ms": 150,
                "tools_available": len(tools) if tools else 0,
            },
        )


# ===========================================
# Command Handler Dependencies
# ===========================================

def get_start_session_handler(
    repository: Annotated[SessionRepository, Depends(get_session_repository)],
    publisher: Annotated[EventPublisher, Depends(get_event_publisher)],
) -> StartSessionHandler:
    return StartSessionHandler(repository, publisher)


def get_send_message_handler(
    repository: Annotated[SessionRepository, Depends(get_session_repository)],
    publisher: Annotated[EventPublisher, Depends(get_event_publisher)],
) -> SendMessageHandler:
    return SendMessageHandler(repository, publisher)


def get_end_session_handler(
    repository: Annotated[SessionRepository, Depends(get_session_repository)],
    publisher: Annotated[EventPublisher, Depends(get_event_publisher)],
) -> EndSessionHandler:
    return EndSessionHandler(repository, publisher)


def get_execute_agent_handler(
    repository: Annotated[SessionRepository, Depends(get_session_repository)],
    agent: Annotated[AgentPort, Depends(get_agent_port)],
    publisher: Annotated[EventPublisher, Depends(get_event_publisher)],
) -> ExecuteAgentHandler:
    return ExecuteAgentHandler(repository, agent, publisher)


# ===========================================
# Query Handler Dependencies
# ===========================================

def get_session_query_handler(
    repository: Annotated[SessionRepository, Depends(get_session_repository)],
) -> GetSessionHandler:
    return GetSessionHandler(repository)


def get_session_messages_handler(
    repository: Annotated[SessionRepository, Depends(get_session_repository)],
) -> GetSessionMessagesHandler:
    return GetSessionMessagesHandler(repository)


def get_active_sessions_handler(
    repository: Annotated[SessionRepository, Depends(get_session_repository)],
) -> GetActiveSessionsHandler:
    return GetActiveSessionsHandler(repository)


# ===========================================
# Type Aliases for Depends
# ===========================================

SettingsDep = Annotated[Settings, Depends(get_settings)]
StartSessionHandlerDep = Annotated[StartSessionHandler, Depends(get_start_session_handler)]
SendMessageHandlerDep = Annotated[SendMessageHandler, Depends(get_send_message_handler)]
EndSessionHandlerDep = Annotated[EndSessionHandler, Depends(get_end_session_handler)]
ExecuteAgentHandlerDep = Annotated[ExecuteAgentHandler, Depends(get_execute_agent_handler)]
GetSessionHandlerDep = Annotated[GetSessionHandler, Depends(get_session_query_handler)]
GetSessionMessagesHandlerDep = Annotated[
    GetSessionMessagesHandler, Depends(get_session_messages_handler)
]
GetActiveSessionsHandlerDep = Annotated[
    GetActiveSessionsHandler, Depends(get_active_sessions_handler)
]

