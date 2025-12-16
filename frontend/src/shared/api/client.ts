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

// ===========================================
// Agent Type
// ===========================================

export type AgentType = "strands" | "langchain";

// ===========================================
// Runtime Service API
// ===========================================

export interface RuntimeConfigRequest {
  agent_type: AgentType;
  model_id?: string;
  region?: string;
  max_tokens?: number;
  temperature?: number;
  system_prompt?: string;
}

export interface ExecuteRequest {
  instruction: string;
  context?: Record<string, unknown>[];
}

export const runtimeApi = {
  initialize: (config: RuntimeConfigRequest) =>
    apiClient<{ status: string; agent_type: string }>("/services/runtime/initialize", {
      method: "POST",
      body: JSON.stringify(config),
    }),

  execute: (data: ExecuteRequest, agentType: AgentType = "strands") =>
    apiClient<{ content: string; agent_type: string; status: string }>(
      `/services/runtime/execute?agent_type=${agentType}`,
      { method: "POST", body: JSON.stringify(data) }
    ),

  getStatus: (agentType: AgentType = "strands") =>
    apiClient<{ status: string; agent_type: string }>(
      `/services/runtime/status?agent_type=${agentType}`
    ),
};

// ===========================================
// Memory Service API
// ===========================================

export const memoryApi = {
  initialize: (config: { agent_type: AgentType; memory_type?: string }) =>
    apiClient<{ initialized: boolean; agent_type: string }>(
      "/services/memory/initialize",
      { method: "POST", body: JSON.stringify(config) }
    ),

  saveConversation: (sessionId: string, messages: Record<string, unknown>[], agentType: AgentType = "strands") =>
    apiClient<{ session_id: string; saved: boolean }>(
      `/services/memory/conversation/save?agent_type=${agentType}`,
      { method: "POST", body: JSON.stringify({ session_id: sessionId, messages }) }
    ),

  loadConversation: (sessionId: string, agentType: AgentType = "strands") =>
    apiClient<{ session_id: string; messages: Record<string, unknown>[] }>(
      `/services/memory/conversation/${sessionId}?agent_type=${agentType}`
    ),

  searchMemory: (query: string, topK = 5, agentType: AgentType = "strands") =>
    apiClient<{ query: string; results: Record<string, unknown>[] }>(
      `/services/memory/long-term/search?agent_type=${agentType}`,
      { method: "POST", body: JSON.stringify({ query, top_k: topK }) }
    ),

  getStats: (agentType: AgentType = "strands") =>
    apiClient<Record<string, unknown>>(
      `/services/memory/stats?agent_type=${agentType}`
    ),
};

// ===========================================
// Gateway Service API
// ===========================================

export const gatewayApi = {
  initialize: (config: { agent_type: AgentType; base_url?: string }) =>
    apiClient<{ initialized: boolean; agent_type: string }>(
      "/services/gateway/initialize",
      { method: "POST", body: JSON.stringify(config) }
    ),

  listRoutes: (agentType: AgentType = "strands") =>
    apiClient<{ routes: Record<string, unknown>[]; agent_type: string }>(
      `/services/gateway/routes?agent_type=${agentType}`
    ),

  getMetrics: (agentType: AgentType = "strands") =>
    apiClient<Record<string, unknown>>(
      `/services/gateway/metrics?agent_type=${agentType}`
    ),
};

// ===========================================
// Identity Service API
// ===========================================

export const identityApi = {
  initialize: (config: { agent_type: AgentType; provider?: string }) =>
    apiClient<{ initialized: boolean; agent_type: string }>(
      "/services/identity/initialize",
      { method: "POST", body: JSON.stringify(config) }
    ),

  authenticate: (credentials: Record<string, unknown>, agentType: AgentType = "strands") =>
    apiClient<{ status: string; identity_id: string; token: string }>(
      `/services/identity/authenticate?agent_type=${agentType}`,
      { method: "POST", body: JSON.stringify({ credentials }) }
    ),

  validateToken: (token: string, agentType: AgentType = "strands") =>
    apiClient<{ status: string; identity_id: string }>(
      `/services/identity/validate?agent_type=${agentType}`,
      { method: "POST", body: JSON.stringify({ token }) }
    ),
};

// ===========================================
// Code Interpreter Service API
// ===========================================

export const codeInterpreterApi = {
  initialize: (config: { agent_type: AgentType; language?: string }) =>
    apiClient<{ environment_id: string; status: string }>(
      "/services/code-interpreter/initialize",
      { method: "POST", body: JSON.stringify(config) }
    ),

  execute: (code: string, language?: string, agentType: AgentType = "strands") =>
    apiClient<{ status: string; output: string; execution_time_ms: number }>(
      `/services/code-interpreter/execute?agent_type=${agentType}`,
      { method: "POST", body: JSON.stringify({ code, language }) }
    ),

  getEnvironment: (agentType: AgentType = "strands") =>
    apiClient<Record<string, unknown>>(
      `/services/code-interpreter/environment?agent_type=${agentType}`
    ),
};

// ===========================================
// Browser Service API
// ===========================================

export const browserApi = {
  initialize: (config: { agent_type: AgentType; browser_type?: string; headless?: boolean }) =>
    apiClient<{ initialized: boolean; browser_type: string }>(
      "/services/browser/initialize",
      { method: "POST", body: JSON.stringify(config) }
    ),

  navigate: (url: string, agentType: AgentType = "strands") =>
    apiClient<{ url: string; title: string }>(
      `/services/browser/navigate?agent_type=${agentType}`,
      { method: "POST", body: JSON.stringify({ url }) }
    ),

  getPageState: (agentType: AgentType = "strands") =>
    apiClient<{ url: string; title: string }>(
      `/services/browser/state?agent_type=${agentType}`
    ),

  extractText: (selector?: string, agentType: AgentType = "strands") =>
    apiClient<{ text: string }>(
      `/services/browser/text?selector=${selector || ""}&agent_type=${agentType}`
    ),
};

// ===========================================
// Observability Service API
// ===========================================

export const observabilityApi = {
  initialize: (config: { agent_type: AgentType; provider?: string }) =>
    apiClient<{ initialized: boolean; provider: string }>(
      "/services/observability/initialize",
      { method: "POST", body: JSON.stringify(config) }
    ),

  startTrace: (name: string, metadata?: Record<string, unknown>, agentType: AgentType = "strands") =>
    apiClient<{ trace_id: string; name: string; status: string }>(
      `/services/observability/traces?agent_type=${agentType}`,
      { method: "POST", body: JSON.stringify({ name, metadata }) }
    ),

  listTraces: (limit = 100, agentType: AgentType = "strands") =>
    apiClient<{ traces: Record<string, unknown>[] }>(
      `/services/observability/traces?limit=${limit}&agent_type=${agentType}`
    ),

  getMetrics: (name?: string, agentType: AgentType = "strands") =>
    apiClient<{ metrics: Record<string, unknown>[] }>(
      `/services/observability/metrics?name=${name || ""}&agent_type=${agentType}`
    ),
};

// ===========================================
// Evaluations Service API
// ===========================================

export const evaluationsApi = {
  initialize: (config: { agent_type: AgentType; evaluation_types?: string[] }) =>
    apiClient<{ initialized: boolean; evaluation_types: string[] }>(
      "/services/evaluations/initialize",
      { method: "POST", body: JSON.stringify(config) }
    ),

  evaluateSingle: (
    caseData: { case_id: string; input_data: unknown; expected_output?: unknown; actual_output?: unknown },
    evaluationTypes?: string[],
    agentType: AgentType = "strands"
  ) =>
    apiClient<{ result_id: string; scores: Record<string, number>; status: string }>(
      `/services/evaluations/evaluate/single?agent_type=${agentType}`,
      { method: "POST", body: JSON.stringify({ case: caseData, evaluation_types: evaluationTypes }) }
    ),

  getResults: (limit = 100, agentType: AgentType = "strands") =>
    apiClient<{ results: Record<string, unknown>[] }>(
      `/services/evaluations/results?limit=${limit}&agent_type=${agentType}`
    ),
};

// ===========================================
// Policy Service API
// ===========================================

export const policyApi = {
  initialize: (config: { agent_type: AgentType; enabled_policies?: string[] }) =>
    apiClient<{ initialized: boolean; enabled_policies: string[] }>(
      "/services/policy/initialize",
      { method: "POST", body: JSON.stringify(config) }
    ),

  validateInput: (content: string, context?: Record<string, unknown>, agentType: AgentType = "strands") =>
    apiClient<{ status: string; violations: Record<string, unknown>[] }>(
      `/services/policy/validate/input?agent_type=${agentType}`,
      { method: "POST", body: JSON.stringify({ content, context }) }
    ),

  validateOutput: (content: string, context?: Record<string, unknown>, agentType: AgentType = "strands") =>
    apiClient<{ status: string; violations: Record<string, unknown>[] }>(
      `/services/policy/validate/output?agent_type=${agentType}`,
      { method: "POST", body: JSON.stringify({ content, context }) }
    ),

  detectPii: (content: string, agentType: AgentType = "strands") =>
    apiClient<{ violations: Record<string, unknown>[] }>(
      `/services/policy/detect/pii?agent_type=${agentType}`,
      { method: "POST", body: JSON.stringify({ content }) }
    ),

  getStats: (agentType: AgentType = "strands") =>
    apiClient<Record<string, unknown>>(
      `/services/policy/stats?agent_type=${agentType}`
    ),
};
