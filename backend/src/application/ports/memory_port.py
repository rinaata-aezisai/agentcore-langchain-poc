"""Memory Port - Memory Service Interface

AgentCore Memory / LangChain Memory に対応。
会話履歴、長期記憶、セマンティック検索。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime
from enum import Enum


class MemoryType(str, Enum):
    """メモリタイプ"""
    CONVERSATION = "conversation"  # 会話履歴
    SEMANTIC = "semantic"  # セマンティックメモリ
    EPISODIC = "episodic"  # エピソード記憶
    WORKING = "working"  # ワーキングメモリ


@dataclass
class MemoryConfig:
    """メモリ設定"""
    memory_type: MemoryType = MemoryType.CONVERSATION
    max_history: int = 100
    embedding_model: str = "amazon.titan-embed-text-v2:0"
    vector_store: str = "in_memory"  # "in_memory", "opensearch", "pinecone"
    ttl_seconds: int | None = None
    namespace: str = "default"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationMemory:
    """会話メモリ"""
    session_id: str
    messages: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LongTermMemory:
    """長期記憶"""
    memory_id: str
    content: str
    embedding: list[float] | None = None
    relevance_score: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


class MemoryPort(ABC):
    """Memory Port - メモリサービス

    Strands Agents: AgentCore Memory
    LangChain: ConversationBufferMemory / VectorStoreRetrieverMemory
    """

    @abstractmethod
    async def initialize(self, config: MemoryConfig) -> bool:
        """メモリを初期化"""
        ...

    # Conversation Memory
    @abstractmethod
    async def save_conversation(
        self,
        session_id: str,
        messages: list[dict[str, Any]],
    ) -> ConversationMemory:
        """会話を保存"""
        ...

    @abstractmethod
    async def load_conversation(
        self,
        session_id: str,
        limit: int | None = None,
    ) -> ConversationMemory | None:
        """会話を読み込み"""
        ...

    @abstractmethod
    async def clear_conversation(self, session_id: str) -> bool:
        """会話をクリア"""
        ...

    # Long-term Memory
    @abstractmethod
    async def store_memory(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> LongTermMemory:
        """長期記憶に保存"""
        ...

    @abstractmethod
    async def search_memory(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.7,
    ) -> list[LongTermMemory]:
        """セマンティック検索"""
        ...

    @abstractmethod
    async def delete_memory(self, memory_id: str) -> bool:
        """記憶を削除"""
        ...

    @abstractmethod
    async def get_memory_stats(self) -> dict[str, Any]:
        """メモリ統計を取得"""
        ...

