"use client";

import { clsx } from "clsx";
import type { Message } from "../model/types";

interface MessageItemProps {
  message: Message;
}

export function MessageItem({ message }: MessageItemProps) {
  const isUser = message.role === "user";

  return (
    <div className={clsx("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={clsx(
          "max-w-[80%] rounded-2xl px-4 py-3",
          isUser
            ? "bg-primary-600 text-white rounded-br-md"
            : "bg-slate-700 text-slate-100 rounded-bl-md"
        )}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="mt-2 pt-2 border-t border-slate-600 text-xs text-slate-400">
            {message.toolCalls.map((tc, i) => (
              <div key={i}>🔧 {tc.toolId}</div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}


