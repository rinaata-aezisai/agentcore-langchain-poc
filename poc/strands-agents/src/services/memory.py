"""Strands Memory Adapter

AgentCore Memory サービスの実装。
会話履歴、長期記憶、セマンティック検索。
"""

import asyncio
from datetime import datetime
from typing import Any
import uuid

import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent.parent.parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_path))

from application.ports.memory_port import (
    MemoryPort,
    MemoryConfig,
    MemoryType,
    ConversationMemory,
    LongTermMemory,
)


class StrandsMemoryAdapter(MemoryPort):
    """Strands Agents Memory アダプター
    
    AgentCore Memoryの機能:
    - 会話履歴管理
    - 長期記憶ストレージ
    - セマンティック検索
    - メモリ永続化
    """

    def __init__(self):
        self._config: MemoryConfig | None = None
        self._conversations: dict[str, ConversationMemory] = {}
        self._long_term_memories: dict[str, LongTermMemory] = {}
        self._embeddings_cache: dict[str, list[float]] = {}

    async def initialize(self, config: MemoryConfig) -> bool:
        """メモリを初期化"""
        self._config = config
        return True

    # Conversation Memory
    async def save_conversation(
        self,
        session_id: str,
        messages: list[dict[str, Any]],
    ) -> ConversationMemory:
        """会話を保存"""
        now = datetime.now()
        
        if session_id in self._conversations:
            # 既存セッションを更新
            conv = self._conversations[session_id]
            conv.messages = messages
            conv.updated_at = now
        else:
            # 新規セッション作成
            conv = ConversationMemory(
                session_id=session_id,
                messages=messages,
                created_at=now,
                updated_at=now,
            )
            self._conversations[session_id] = conv
        
        # 最大履歴数を超えた場合は古いメッセージを削除
        if self._config and len(conv.messages) > self._config.max_history:
            conv.messages = conv.messages[-self._config.max_history:]
        
        return conv

    async def load_conversation(
        self,
        session_id: str,
        limit: int | None = None,
    ) -> ConversationMemory | None:
        """会話を読み込み"""
        conv = self._conversations.get(session_id)
        if conv is None:
            return None
        
        if limit and len(conv.messages) > limit:
            # 制限付きで返す（新しいConversationMemoryを作成）
            return ConversationMemory(
                session_id=conv.session_id,
                messages=conv.messages[-limit:],
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                metadata=conv.metadata,
            )
        
        return conv

    async def clear_conversation(self, session_id: str) -> bool:
        """会話をクリア"""
        if session_id in self._conversations:
            del self._conversations[session_id]
            return True
        return False

    # Long-term Memory
    async def store_memory(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> LongTermMemory:
        """長期記憶に保存"""
        memory_id = str(uuid.uuid4())
        
        # 埋め込みベクトルを生成（簡易実装）
        embedding = await self._generate_embedding(content)
        
        memory = LongTermMemory(
            memory_id=memory_id,
            content=content,
            embedding=embedding,
            created_at=datetime.now(),
            metadata=metadata or {},
        )
        
        self._long_term_memories[memory_id] = memory
        self._embeddings_cache[memory_id] = embedding
        
        return memory

    async def search_memory(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.7,
    ) -> list[LongTermMemory]:
        """セマンティック検索"""
        if not self._long_term_memories:
            return []
        
        # クエリの埋め込みを生成
        query_embedding = await self._generate_embedding(query)
        
        # コサイン類似度でスコアリング
        scored_memories = []
        for memory_id, memory in self._long_term_memories.items():
            if memory.embedding:
                score = self._cosine_similarity(query_embedding, memory.embedding)
                if score >= threshold:
                    memory.relevance_score = score
                    scored_memories.append((score, memory))
        
        # スコア順にソート
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        
        return [m for _, m in scored_memories[:top_k]]

    async def delete_memory(self, memory_id: str) -> bool:
        """記憶を削除"""
        if memory_id in self._long_term_memories:
            del self._long_term_memories[memory_id]
            if memory_id in self._embeddings_cache:
                del self._embeddings_cache[memory_id]
            return True
        return False

    async def get_memory_stats(self) -> dict[str, Any]:
        """メモリ統計を取得"""
        return {
            "conversation_count": len(self._conversations),
            "long_term_memory_count": len(self._long_term_memories),
            "total_messages": sum(
                len(c.messages) for c in self._conversations.values()
            ),
            "memory_type": self._config.memory_type.value if self._config else "unknown",
        }

    async def _generate_embedding(self, text: str) -> list[float]:
        """埋め込みベクトルを生成（簡易実装）
        
        本番環境ではBedrock Titan Embeddingsを使用：
        from strands.models import BedrockEmbeddings
        """
        # 簡易的なハッシュベースの埋め込み（デモ用）
        import hashlib
        hash_bytes = hashlib.sha256(text.encode()).digest()
        return [float(b) / 255.0 for b in hash_bytes[:128]]

    @staticmethod
    def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        """コサイン類似度を計算"""
        import math
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)


def create_strands_memory() -> StrandsMemoryAdapter:
    """ファクトリ関数"""
    return StrandsMemoryAdapter()

