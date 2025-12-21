'use client';

import { fetchAuthSession, getCurrentUser } from 'aws-amplify/auth';
import { apiConfig } from '@/lib/amplify-config';

/**
 * Amplify認証付きAPIクライアント
 */

export class AuthenticatedApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    message: string
  ) {
    super(message);
    this.name = 'AuthenticatedApiError';
  }
}

/**
 * 認証トークンを取得
 */
export async function getAuthToken(): Promise<string | null> {
  try {
    const session = await fetchAuthSession();
    return session.tokens?.idToken?.toString() || null;
  } catch {
    console.log('No authenticated session');
    return null;
  }
}

/**
 * 現在のユーザー情報を取得
 */
export async function getCurrentUserInfo() {
  try {
    const user = await getCurrentUser();
    return {
      userId: user.userId,
      username: user.username,
      signInDetails: user.signInDetails,
    };
  } catch {
    return null;
  }
}

/**
 * 認証付きAPIクライアント
 */
export async function authenticatedApiClient<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const token = await getAuthToken();
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options?.headers,
  };
  
  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${apiConfig.endpoint}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new AuthenticatedApiError(
      response.status,
      response.statusText,
      errorText || `API Error: ${response.status}`
    );
  }

  return response.json();
}

// ===========================================
// Session API (認証付き)
// ===========================================

export interface CreateSessionRequest {
  agent_id?: string;
  agent_type: 'strands' | 'langchain';
}

export interface CreateSessionResponse {
  session_id: string;
  agent_id: string;
  agent_type: string;
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
  agent_type: string;
  state: string;
  created_at: string;
  message_count: number;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  latency_ms?: number;
}

export const authenticatedSessionApi = {
  create: async (data: CreateSessionRequest) => {
    const userInfo = await getCurrentUserInfo();
    return authenticatedApiClient<CreateSessionResponse>('/sessions', {
      method: 'POST',
      body: JSON.stringify({
        ...data,
        user_id: userInfo?.userId,
      }),
    });
  },

  get: (sessionId: string) =>
    authenticatedApiClient<SessionInfo>(`/sessions/${sessionId}`),

  getMessages: (sessionId: string, limit = 50, offset = 0) =>
    authenticatedApiClient<{ messages: Message[]; total_count: number }>(
      `/sessions/${sessionId}/messages?limit=${limit}&offset=${offset}`
    ),

  sendMessage: (sessionId: string, data: SendMessageRequest) =>
    authenticatedApiClient<SendMessageResponse>(`/sessions/${sessionId}/messages`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  end: (sessionId: string) =>
    authenticatedApiClient<void>(`/sessions/${sessionId}`, { method: 'DELETE' }),
};

// ===========================================
// Service API (認証付き)
// ===========================================

export interface ServiceExecuteRequest {
  instruction: string;
  agent_type: 'strands' | 'langchain';
  tools?: Record<string, unknown>[];
}

export interface ServiceExecuteResponse {
  response_id: string;
  content: string;
  tool_calls?: Record<string, unknown>[];
  latency_ms: number;
  metadata?: Record<string, unknown>;
}

const createAuthenticatedServiceApi = (servicePath: string) => ({
  execute: (data: ServiceExecuteRequest) =>
    authenticatedApiClient<ServiceExecuteResponse>(`/services/${servicePath}/execute`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
});

export const authenticatedServiceApi = {
  runtime: createAuthenticatedServiceApi('runtime'),
  memory: createAuthenticatedServiceApi('memory'),
  gateway: createAuthenticatedServiceApi('gateway'),
  identity: createAuthenticatedServiceApi('identity'),
  codeInterpreter: createAuthenticatedServiceApi('code-interpreter'),
  browser: createAuthenticatedServiceApi('browser'),
  observability: createAuthenticatedServiceApi('observability'),
  evaluations: createAuthenticatedServiceApi('evaluations'),
  policy: createAuthenticatedServiceApi('policy'),
};

// ===========================================
// Benchmark API (認証付き)
// ===========================================

export interface BenchmarkRequest {
  test_cases: string[];
  iterations?: number;
}

export interface BenchmarkResult {
  test_name: string;
  strands_latency_ms: number;
  langchain_latency_ms: number;
  strands_success: boolean;
  langchain_success: boolean;
  strands_response?: string;
  langchain_response?: string;
}

export const authenticatedBenchmarkApi = {
  run: (data: BenchmarkRequest) =>
    authenticatedApiClient<{ results: BenchmarkResult[] }>('/benchmark/run', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getResults: () =>
    authenticatedApiClient<{ results: BenchmarkResult[] }>('/benchmark/results'),
};


