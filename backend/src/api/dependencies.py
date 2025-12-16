"""FastAPI Dependencies - Dependency Injection Configuration

DIコンテナとしてFastAPIのDependsを使用。
環境変数でAgentType（strands/langchain）を切り替え可能。
"""

import os
from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from infrastructure.persistence.event_store import (
    EventStore,
    DynamoDBEventStore,
    InMemoryEventStore,
)
from infrastructure.persistence.session_repository_impl import EventSourcedSessionRepository
from infrastructure.messaging.event_publisher import (
    EventPublisher,
    EventBridgePublisher,
    InMemoryEventPublisher,
)
from domain.repositories.session_repository import SessionRepository
from application.ports.agent_port import AgentPort
from application.handlers.command_handlers import (
    StartSessionHandler,
    SendMessageHandler,
    EndSessionHandler,
    ExecuteAgentHandler,
)
from application.handlers.query_handlers import (
    GetSessionHandler,
    GetSessionMessagesHandler,
    GetActiveSessionsHandler,
)


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


@lru_cache()
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
    """AgentPortのDI - 環境変数で切り替え"""
    if settings.agent_type == "langchain":
        from poc.langchain.src.adapter import create_langchain_adapter
        return create_langchain_adapter(
            model_id=settings.bedrock_model_id,
            region=settings.aws_region,
            langfuse_enabled=settings.langfuse_enabled,
        )
    else:
        from poc.strands_agents.src.adapter import create_strands_adapter
        return create_strands_adapter(
            model_id=settings.bedrock_model_id,
            region=settings.aws_region,
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
GetSessionMessagesHandlerDep = Annotated[GetSessionMessagesHandler, Depends(get_session_messages_handler)]
GetActiveSessionsHandlerDep = Annotated[GetActiveSessionsHandler, Depends(get_active_sessions_handler)]

