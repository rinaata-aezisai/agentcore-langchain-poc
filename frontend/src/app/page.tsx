import { ChatWindow } from "@/widgets/chat-window";

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800">
      <div className="container mx-auto px-4 py-8">
        <header className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-white mb-2">AI Agent PoC</h1>
          <p className="text-slate-400">AgentCore vs LangChain Comparison</p>
        </header>
        <ChatWindow />
      </div>
    </main>
  );
}


