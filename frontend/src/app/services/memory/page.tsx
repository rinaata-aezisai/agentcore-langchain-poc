"use client";

import { ServiceTest } from "@/widgets/service-test";

const testCases = [
  {
    id: "memory-stats",
    name: "メモリ統計取得",
    endpoint: "/services/memory/stats",
    method: "GET" as const,
    expectedBehavior: "メモリ使用状況の統計を取得",
  },
  {
    id: "memory-save",
    name: "会話保存",
    endpoint: "/services/memory/conversation/save",
    method: "POST" as const,
    body: { 
      session_id: "test-session-123",
      messages: [
        { role: "user", content: "こんにちは" },
        { role: "assistant", content: "こんにちは！何かお手伝いできますか？" }
      ]
    },
    expectedBehavior: "会話履歴を保存",
  },
  {
    id: "memory-search",
    name: "セマンティック検索",
    endpoint: "/services/memory/long-term/search",
    method: "POST" as const,
    body: { query: "プロジェクトについて", top_k: 5 },
    expectedBehavior: "関連する記憶を検索",
  },
];

export default function MemoryPage() {
  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-2 text-sm text-slate-400 mb-2">
          <span>Services</span>
          <span>/</span>
          <span className="text-white">Memory</span>
        </div>
        <h1 className="text-2xl font-bold text-white">Memory Service</h1>
      </div>

      <ServiceTest
        serviceName="Memory"
        serviceKey="memory"
        serviceDescription="会話履歴と長期記憶を統合管理。セマンティック検索によるコンテキスト取得。"
        testCases={testCases}
        strandsFeatures={[
          "AgentCore統合メモリ",
          "自動コンテキスト管理",
          "セッションベース永続化",
          "ベクトル検索対応",
        ]}
        langchainFeatures={[
          "ConversationBufferMemory",
          "VectorStoreRetrieverMemory",
          "FAISS/Pinecone統合",
          "カスタムメモリクラス",
        ]}
        strandsExample={`# AgentCore Memory
from strands import Agent

agent = Agent(
    model=model,
    memory=True  # 自動メモリ管理
)

# 会話コンテキストが自動保持される
response1 = agent("私の名前は田中です")
response2 = agent("私の名前は？")`}
        langchainExample={`from langchain.memory import ConversationBufferMemory
from langchain_community.vectorstores import FAISS

# 会話メモリ
memory = ConversationBufferMemory(
    return_messages=True
)

# ベクトルストア検索
vectorstore = FAISS.from_texts(texts, embeddings)
retriever = vectorstore.as_retriever()`}
      />
    </div>
  );
}
