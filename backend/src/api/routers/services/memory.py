"""Memory Service Router - メモリ管理比較

AgentCore Memory vs LangChain Memory の比較:

AgentCore Memory:
- 短期・長期メモリのマネージドサービス
- エピソード機能（経験ベース学習）
- エージェント間メモリ共有
- 検索機能

LangChain Memory:
- ConversationBufferMemory
- ConversationSummaryMemory
- VectorStoreRetrieverMemory
- カスタムメモリ実装
"""

from .base import create_service_router

router = create_service_router(
    service_name="Memory",
    service_description="短期・長期メモリのマネージドサービス。会話履歴やコンテキストの保持・検索。",
    strands_features=[
        "managed_memory_service",
        "episodic_functionality",
        "agent_memory_sharing",
        "semantic_search",
        "long_term_retention",
        "automatic_summarization",
    ],
    langchain_features=[
        "conversation_buffer_memory",
        "conversation_summary_memory",
        "vector_store_memory",
        "custom_memory_implementations",
        "langgraph_checkpointing",
        "time_travel_debugging",
    ],
)
