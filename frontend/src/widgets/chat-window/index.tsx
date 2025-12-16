"use client";

import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { MessageItem, MessageSkeleton } from "@/entities/message/ui/message-item";
import { ChatInput } from "@/features/send-message/ui/chat-input";
import { sessionApi, agentApi, Message } from "@/shared/api/client";
import { cn } from "@/shared/lib/utils";

interface ChatMessage extends Message {
  latencyMs?: number;
}

export function ChatWindow() {
  const queryClient = useQueryClient();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // エージェント情報を取得
  const { data: agentInfo } = useQuery({
    queryKey: ["agentInfo"],
    queryFn: agentApi.getInfo,
    retry: false,
  });

  // セッション作成
  const createSession = useMutation({
    mutationFn: () => sessionApi.create({ user_id: "demo-user" }),
    onSuccess: (data) => {
      setSessionId(data.session_id);
      setMessages([]);
    },
  });

  // メッセージ送信
  const sendMessage = useMutation({
    mutationFn: (instruction: string) => {
      if (!sessionId) throw new Error("No session");
      return sessionApi.sendMessage(sessionId, { instruction });
    },
    onMutate: (instruction) => {
      // Optimistic update - ユーザーメッセージを即座に表示
      const userMessage: ChatMessage = {
        id: `temp-${Date.now()}`,
        role: "user",
        content: instruction,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);
    },
    onSuccess: (response) => {
      // AIレスポンスを追加
      const aiMessage: ChatMessage = {
        id: response.response_id,
        role: "assistant",
        content: response.content,
        created_at: new Date().toISOString(),
        latencyMs: response.latency_ms,
      };
      setMessages((prev) => [...prev, aiMessage]);
    },
    onError: (error) => {
      // エラー時は最後のユーザーメッセージを削除
      setMessages((prev) => prev.slice(0, -1));
      console.error("Failed to send message:", error);
    },
  });

  // 初回セッション作成
  useEffect(() => {
    if (!sessionId) {
      createSession.mutate();
    }
  }, []);

  // メッセージ追加時に自動スクロール
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = (content: string) => {
    if (content.trim()) {
      sendMessage.mutate(content);
    }
  };

  const handleNewSession = () => {
    createSession.mutate();
  };

  return (
    <div className="flex flex-col h-[calc(100vh-200px)] max-w-4xl mx-auto bg-slate-800/30 rounded-2xl border border-slate-700 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700 bg-slate-800/50">
        <div>
          <h2 className="text-lg font-semibold text-white">
            AI Assistant
          </h2>
          {agentInfo && (
            <p className="text-sm text-slate-400">
              {agentInfo.agent_type === "langchain" ? "LangChain + LangGraph" : "Strands Agents"} 
              <span className="mx-2">•</span>
              <span className="text-xs">{agentInfo.model_id.split("/").pop()}</span>
            </p>
          )}
        </div>
        <div className="flex items-center gap-3">
          {sessionId && (
            <span className="text-xs text-slate-500 font-mono">
              Session: {sessionId.slice(0, 8)}...
            </span>
          )}
          <button
            onClick={handleNewSession}
            className="px-3 py-1.5 text-sm bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
          >
            New Chat
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-400">
            <svg
              className="w-16 h-16 mb-4 opacity-50"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
              />
            </svg>
            <p className="text-lg font-medium">Start a conversation</p>
            <p className="text-sm mt-1">
              {agentInfo?.agent_type === "langchain"
                ? "Using LangChain + LangGraph for advanced workflows"
                : "Using Strands Agents with AWS Bedrock"}
            </p>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <MessageItem
                key={message.id}
                message={message}
                latencyMs={message.latencyMs}
              />
            ))}
            {sendMessage.isPending && <MessageSkeleton />}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-slate-700 p-4 bg-slate-800/50">
        <ChatInput
          onSend={handleSend}
          isLoading={sendMessage.isPending}
          disabled={!sessionId || createSession.isPending}
          placeholder={
            createSession.isPending
              ? "セッションを作成中..."
              : "メッセージを入力... (Shift+Enter で改行)"
          }
        />
      </div>
    </div>
  );
}
