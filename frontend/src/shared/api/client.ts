/**
 * API Client - Backend連携
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiClient<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new ApiError(
      response.status,
      response.statusText,
      errorText || `API Error: ${response.status}`
    );
  }

  return response.json();
}

// ===========================================
// Session API
// ===========================================

export interface CreateSessionRequest {
  agent_id?: string;
  user_id?: string;
}

export interface CreateSessionResponse {
  session_id: string;
  agent_id: string;
  created_at: string;
}

export interface SendMessageRequest {
  instruction: string;
  tools?: Record<string, unknown>[];
}

export interface SendMessageResponse {
  response_id: string;
  content: string;
  tool_calls?: Record<string, unknown>[];
  latency_ms: number;
  metadata?: Record<string, unknown>;
}

export interface SessionInfo {
  session_id: string;
  agent_id: string;
  state: string;
  created_at: string;
  message_count: number;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export const sessionApi = {
  create: (data: CreateSessionRequest) =>
    apiClient<CreateSessionResponse>("/sessions", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  get: (sessionId: string) =>
    apiClient<SessionInfo>(`/sessions/${sessionId}`),

  getMessages: (sessionId: string, limit = 50, offset = 0) =>
    apiClient<{ messages: Message[]; total_count: number }>(
      `/sessions/${sessionId}/messages?limit=${limit}&offset=${offset}`
    ),

  sendMessage: (sessionId: string, data: SendMessageRequest) =>
    apiClient<SendMessageResponse>(`/sessions/${sessionId}/messages`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  end: (sessionId: string) =>
    apiClient<void>(`/sessions/${sessionId}`, { method: "DELETE" }),
};

// ===========================================
// Agent API
// ===========================================

export interface AgentInfo {
  agent_type: string;
  model_id: string;
  provider: string;
  capabilities: string[];
}

export interface AgentComparison {
  strands: {
    name: string;
    strengths: string[];
    features: Record<string, boolean>;
  };
  langchain: {
    name: string;
    strengths: string[];
    features: Record<string, boolean>;
  };
}

export const agentApi = {
  getInfo: () => apiClient<AgentInfo>("/agents/info"),

  getComparison: () => apiClient<AgentComparison>("/agents/comparison"),

  getTools: () =>
    apiClient<{
      agent_type: string;
      tools: { name: string; description: string; available: boolean }[];
      total_count: number;
    }>("/agents/tools"),
};

// ===========================================
// Health API
// ===========================================

export const healthApi = {
  check: () => apiClient<{ status: string }>("/health"),
};
