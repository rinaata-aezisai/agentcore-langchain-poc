"""LangChain Memory Adapter

LangChain Memory による実装。
会話履歴、長期記憶、セマンティック検索。
"""

from datetime import datetime
from typing import Any
import uuid

from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory
from langchain_community.vectorstores import FAISS
from langchain_aws import BedrockEmbeddings

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


class LangChainMemoryAdapter(MemoryPort):
    """LangChain Memory アダプター
    
    LangChain相当機能:
    - ConversationBufferMemory
    - ConversationSummaryMemory
    - VectorStoreRetrieverMemory (FAISS)
    """

    def __init__(self):
        self._config: MemoryConfig | None = None
        self._conversations: dict[str, ConversationMemory] = {}
        self._conversation_memories: dict[str, ConversationBufferMemory] = {}
        self._long_term_memories: dict[str, LongTermMemory] = {}
        self._vector_store = None
        self._embeddings = None

    async def initialize(self, config: MemoryConfig) -> bool:
        """メモリを初期化"""
        self._config = config
        
        # Embeddings初期化
        try:
            self._embeddings = BedrockEmbeddings(
                model_id=config.embedding_model,
                region_name="us-east-1",
            )
        except Exception:
            # フォールバック: 簡易埋め込み
            self._embeddings = None
        
        return True

    # Conversation Memory
    async def save_conversation(
        self,
        session_id: str,
        messages: list[dict[str, Any]],
    ) -> ConversationMemory:
        """会話を保存"""
        now = datetime.now()
        
        # LangChain ConversationBufferMemoryを使用
        if session_id not in self._conversation_memories:
            self._conversation_memories[session_id] = ConversationBufferMemory(
                return_messages=True,
            )
        
        # メッセージを追加
        memory = self._conversation_memories[session_id]
        for msg in messages:
            if msg.get("role") == "user":
                memory.chat_memory.add_user_message(msg.get("content", ""))
            elif msg.get("role") == "assistant":
                memory.chat_memory.add_ai_message(msg.get("content", ""))
        
        if session_id in self._conversations:
            conv = self._conversations[session_id]
            conv.messages = messages
            conv.updated_at = now
        else:
            conv = ConversationMemory(
                session_id=session_id,
                messages=messages,
                created_at=now,
                updated_at=now,
            )
            self._conversations[session_id] = conv
        
        # 最大履歴数制限
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
        if session_id in self._conversation_memories:
            self._conversation_memories[session_id].clear()
            del self._conversation_memories[session_id]
        return True

    # Long-term Memory (Vector Store)
    async def store_memory(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> LongTermMemory:
        """長期記憶に保存（FAISSベクトルストア）"""
        memory_id = str(uuid.uuid4())
        
        # 埋め込みを生成
        embedding = await self._generate_embedding(content)
        
        memory = LongTermMemory(
            memory_id=memory_id,
            content=content,
            embedding=embedding,
            created_at=datetime.now(),
            metadata=metadata or {},
        )
        
        self._long_term_memories[memory_id] = memory
        
        # FAISSに追加（利用可能な場合）
        if self._embeddings and self._vector_store is None:
            try:
                self._vector_store = FAISS.from_texts(
                    [content],
                    self._embeddings,
                    metadatas=[{"memory_id": memory_id, **(metadata or {})}],
                )
            except Exception:
                pass
        elif self._vector_store:
            try:
                self._vector_store.add_texts(
                    [content],
                    metadatas=[{"memory_id": memory_id, **(metadata or {})}],
                )
            except Exception:
                pass
        
        return memory

    async def search_memory(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.7,
    ) -> list[LongTermMemory]:
        """セマンティック検索（FAISS）"""
        # FAISSベクトルストアで検索
        if self._vector_store:
            try:
                results = self._vector_store.similarity_search_with_score(
                    query,
                    k=top_k,
                )
                
                memories = []
                for doc, score in results:
                    # スコアを正規化（FAISSは距離を返すので変換）
                    normalized_score = 1 / (1 + score)
                    
                    if normalized_score >= threshold:
                        memory_id = doc.metadata.get("memory_id")
                        if memory_id and memory_id in self._long_term_memories:
                            memory = self._long_term_memories[memory_id]
                            memory.relevance_score = normalized_score
                            memories.append(memory)
                
                return memories
            except Exception:
                pass
        
        # フォールバック: 簡易検索
        query_embedding = await self._generate_embedding(query)
        scored_memories = []
        
        for memory in self._long_term_memories.values():
            if memory.embedding:
                score = self._cosine_similarity(query_embedding, memory.embedding)
                if score >= threshold:
                    memory.relevance_score = score
                    scored_memories.append((score, memory))
        
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored_memories[:top_k]]

    async def delete_memory(self, memory_id: str) -> bool:
        """記憶を削除"""
        if memory_id in self._long_term_memories:
            del self._long_term_memories[memory_id]
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
            "vector_store_available": self._vector_store is not None,
            "memory_type": self._config.memory_type.value if self._config else "unknown",
        }

    async def _generate_embedding(self, text: str) -> list[float]:
        """埋め込みベクトルを生成"""
        if self._embeddings:
            try:
                return self._embeddings.embed_query(text)
            except Exception:
                pass
        
        # フォールバック: 簡易ハッシュベース埋め込み
        import hashlib
        hash_bytes = hashlib.sha256(text.encode()).digest()
        return [float(b) / 255.0 for b in hash_bytes[:128]]

    @staticmethod
    def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        """コサイン類似度"""
        import math
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)


def create_langchain_memory() -> LangChainMemoryAdapter:
    """ファクトリ関数"""
    return LangChainMemoryAdapter()

