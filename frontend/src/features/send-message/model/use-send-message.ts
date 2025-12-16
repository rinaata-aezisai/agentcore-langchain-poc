/**
 * Send Message Hook - TanStack Query + API連携
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { sessionApi, SendMessageRequest, SendMessageResponse } from "@/shared/api/client";

interface UseSendMessageOptions {
  sessionId: string;
  onSuccess?: (response: SendMessageResponse) => void;
  onError?: (error: Error) => void;
}

export function useSendMessage({ sessionId, onSuccess, onError }: UseSendMessageOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: SendMessageRequest) => sessionApi.sendMessage(sessionId, data),
    onSuccess: (response) => {
      // メッセージキャッシュを更新
      queryClient.invalidateQueries({ queryKey: ["messages", sessionId] });
      onSuccess?.(response);
    },
    onError: (error: Error) => {
      console.error("Send message error:", error);
      onError?.(error);
    },
  });
}
