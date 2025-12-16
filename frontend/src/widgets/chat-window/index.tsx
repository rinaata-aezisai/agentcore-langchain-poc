"use client";

import { useState } from "react";
import { MessageItem } from "@/entities/message/ui/message-item";
import { ChatInput } from "@/features/send-message/ui/chat-input";
import { useSendMessage } from "@/features/send-message/model/use-send-message";
import type { Message } from "@/entities/message/model/types";

export function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId] = useState("demo-session");
  const sendMessage = useSendMessage();

  const handleSend = async (content: string) => {
    // ユーザーメッセージを追加
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);

    try {
      const response = await sendMessage.mutateAsync({ sessionId, content });

      // アシスタントメッセージを追加
      const assistantMessage: Message = {
        id: response.response_id,
        role: "assistant",
        content: response.content,
        timestamp: new Date().toISOString(),
        toolCalls: response.tool_calls?.map((tc) => ({
          toolId: tc.tool_id,
          result: tc.result,
        })),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error("Failed to send message:", error);
    }
  };

  return (
    <div className="mx-auto max-w-3xl rounded-xl bg-slate-800/50 backdrop-blur border border-slate-700 shadow-2xl">
      <div className="p-4 border-b border-slate-700">
        <h2 className="text-lg font-semibold text-white">Chat Session</h2>
        <p className="text-sm text-slate-400">Session: {sessionId}</p>
      </div>

      <div className="h-[500px] overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-slate-500">
            メッセージを送信してください
          </div>
        ) : (
          messages.map((msg) => <MessageItem key={msg.id} message={msg} />)
        )}
      </div>

      <div className="p-4 border-t border-slate-700">
        <ChatInput onSend={handleSend} isLoading={sendMessage.isPending} />
      </div>
    </div>
  );
}


