"use client";

import { ServiceTest } from "@/widgets/service-test";

const testCases = [
  {
    id: "memory-short-term",
    name: "短期メモリテスト",
    prompt: "私は東京に住んでいます。どこに住んでいるか聞いてください。",
    expectedBehavior: "同一セッション内で情報を記憶",
  },
  {
    id: "memory-context-window",
    name: "コンテキストウィンドウ",
    prompt: "これまでの会話を要約してください。",
    expectedBehavior: "会話履歴を正確に参照",
  },
  {
    id: "memory-episodic",
    name: "エピソード記憶 (AgentCore)",
    prompt: "前回の会話で学んだことを教えてください。",
    expectedBehavior: "エピソードベースの学習内容を参照（AgentCore限定）",
  },
  {
    id: "memory-summarization",
    name: "メモリ要約",
    prompt: "長い会話履歴がある場合、どのように管理していますか？",
    expectedBehavior: "メモリ管理戦略の説明",
  },
];

export default function MemoryPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-8">
      <div className="mb-6">
        <div className="flex items-center gap-2 text-sm text-slate-400 mb-2">
          <span>Services</span>
          <span>/</span>
          <span className="text-white">Memory</span>
        </div>
        <h1 className="text-2xl font-bold text-white">Memory Service</h1>
      </div>

      <ServiceTest
        serviceName="Memory"
        serviceDescription="短期・長期メモリ管理による文脈認識機能。エピソードベース学習対応。"
        testCases={testCases}
        strandsFeatures={[
          "短期メモリ（セッション内）",
          "長期メモリ（永続化）",
          "エピソード記憶 (Episodic)",
          "セマンティック検索",
          "Reflection Agent統合",
        ]}
        langchainFeatures={[
          "LangGraph Checkpointer",
          "カスタムメモリクラス",
          "ConversationBufferMemory",
          "VectorStoreメモリ",
        ]}
        strandsExample={`from strands import Agent
from strands.memory import Memory

memory = Memory(
    episodic=True,
    semantic_search=True
)
agent = Agent(
    model=model,
    memory=memory
)`}
        langchainExample={`from langgraph.checkpoint import MemorySaver

checkpointer = MemorySaver()
graph = workflow.compile(
    checkpointer=checkpointer
)`}
      />
    </div>
  );
}

