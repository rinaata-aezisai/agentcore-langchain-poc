"use client";

import { cn } from "@/shared/lib/utils";
import { Message } from "@/entities/message/model/types";

interface MessageItemProps {
  message: Message;
  latencyMs?: number;
}

export function MessageItem({ message, latencyMs }: MessageItemProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={cn(
        "flex gap-3 p-4 rounded-xl max-w-[85%]",
        isUser
          ? "ml-auto bg-blue-600 text-white"
          : "mr-auto bg-slate-700 text-slate-100"
      )}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-medium opacity-70">
            {isUser ? "You" : "AI"}
          </span>
          {latencyMs !== undefined && !isUser && (
            <span className="text-xs opacity-50">
              {latencyMs < 1000 ? `${latencyMs}ms` : `${(latencyMs / 1000).toFixed(1)}s`}
            </span>
          )}
        </div>
        <div className="whitespace-pre-wrap break-words text-sm leading-relaxed">
          {message.content}
        </div>
      </div>
    </div>
  );
}

export function MessageSkeleton() {
  return (
    <div className="flex gap-3 p-4 rounded-xl max-w-[85%] mr-auto bg-slate-700">
      <div className="flex-1 space-y-2">
        <div className="h-3 w-12 bg-slate-600 rounded animate-pulse" />
        <div className="space-y-1.5">
          <div className="h-4 w-full bg-slate-600 rounded animate-pulse" />
          <div className="h-4 w-3/4 bg-slate-600 rounded animate-pulse" />
        </div>
      </div>
    </div>
  );
}
