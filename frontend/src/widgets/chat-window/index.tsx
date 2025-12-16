"use client";

import { useState, useEffect, useRef } from "react";
import { useMutation } from "@tanstack/react-query";
import { MessageItem, MessageSkeleton } from "@/entities/message/ui/message-item";
import { ChatInput } from "@/features/send-message/ui/chat-input";
import { authenticatedSessionApi } from "@/shared/api/amplify-client";
import { cn } from "@/shared/lib/utils";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  latencyMs?: number;
}

type AgentType = "strands" | "langchain";

export function ChatWindow() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [agentType, setAgentType] = useState<AgentType>("strands");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // セッション作成
  const createSession = useMutation({
    mutationFn: () =>
      authenticatedSessionApi.create({
        agent_type: agentType,
      }),
    onSuccess: (data) => {
      setSessionId(data.session_id);
      setMessages([]);
    },
    onError: (error) => {
      console.error("Failed to create session:", error);
    },
  });

  // メッセージ送信
  const sendMessage = useMutation({
    mutationFn: (instruction: string) => {
      if (!sessionId) throw new Error("No session");
      return authenticatedSessionApi.sendMessage(sessionId, { instruction });
    },
    onMutate: (instruction) => {
      // Optimistic update - ユーザーメッセージを即座に表示
      const userMessage: ChatMessage = {
        id: `temp-${Date.now()}`,
        role: "user",
        content: instruction,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);
    },
    onSuccess: (response) => {
      // AIレスポンスを追加
      const aiMessage: ChatMessage = {
        id: response.response_id,
        role: "assistant",
        content: response.content,
        timestamp: new Date().toISOString(),
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  const handleAgentTypeChange = (newType: AgentType) => {
    if (newType !== agentType) {
      setAgentType(newType);
      setSessionId(null);
      setMessages([]);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-200px)] max-w-4xl mx-auto bg-slate-800/30 rounded-2xl border border-slate-700 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700 bg-slate-800/50">
        <div>
          <h2 className="text-lg font-semibold text-white">AI Assistant</h2>
          <p className="text-sm text-slate-400">
            {agentType === "langchain"
              ? "LangChain + LangGraph"
              : "Strands Agents (AgentCore)"}
            <span className="mx-2">•</span>
            <span className="text-xs">claude-3-haiku</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Agent Type Selector */}
          <div className="flex bg-slate-700/50 rounded-lg p-1">
            <button
              onClick={() => handleAgentTypeChange("strands")}
              className={cn(
                "px-3 py-1.5 text-xs font-medium rounded transition-colors",
                agentType === "strands"
                  ? "bg-blue-600 text-white"
                  : "text-slate-400 hover:text-white"
              )}
            >
              Strands
            </button>
            <button
              onClick={() => handleAgentTypeChange("langchain")}
              className={cn(
                "px-3 py-1.5 text-xs font-medium rounded transition-colors",
                agentType === "langchain"
                  ? "bg-purple-600 text-white"
                  : "text-slate-400 hover:text-white"
              )}
            >
              LangChain
            </button>
          </div>

          {sessionId && (
            <span className="text-xs text-slate-500 font-mono">
              {sessionId.slice(0, 8)}...
            </span>
          )}
          <button
            onClick={handleNewSession}
            disabled={createSession.isPending}
            className={cn(
              "px-3 py-1.5 text-sm bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors",
              createSession.isPending && "opacity-50 cursor-not-allowed"
            )}
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
              {agentType === "langchain"
                ? "Using LangChain + LangGraph for advanced workflows"
                : "Using Strands Agents with AWS Bedrock"}
            </p>
            <div className="mt-4 flex gap-2">
              <span
                className={cn(
                  "px-2 py-1 rounded text-xs",
                  agentType === "strands"
                    ? "bg-blue-600/20 text-blue-400"
                    : "bg-purple-600/20 text-purple-400"
                )}
              >
                {agentType === "strands" ? "Strands Agents" : "LangChain"}
              </span>
              <span className="px-2 py-1 rounded text-xs bg-slate-700 text-slate-300">
                AWS Bedrock
              </span>
            </div>
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
