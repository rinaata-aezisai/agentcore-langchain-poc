"use client";

import { ChatWindow } from "@/widgets/chat-window";

export default function ChatPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white mb-2">Chat テスト</h1>
        <p className="text-slate-400">
          基本的なチャット機能の検証。Strands Agents / LangChain の基本動作確認
        </p>
      </div>
      <ChatWindow />
    </div>
  );
}

