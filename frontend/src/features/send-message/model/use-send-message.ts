"use client";

import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@/shared/api/client";

interface SendMessageInput {
  sessionId: string;
  content: string;
}

interface SendMessageResponse {
  response_id: string;
  content: string;
  tool_calls?: { tool_id: string; result?: unknown }[];
  latency_ms: number;
}

export function useSendMessage() {
  return useMutation({
    mutationFn: async ({ sessionId, content }: SendMessageInput) => {
      return apiClient<SendMessageResponse>(
        `/sessions/${sessionId}/messages`,
        {
          method: "POST",
          body: JSON.stringify({ content }),
        }
      );
    },
  });
}


