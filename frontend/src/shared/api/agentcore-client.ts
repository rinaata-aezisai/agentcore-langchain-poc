'use client';

import { fetchAuthSession } from 'aws-amplify/auth';

/**
 * AgentCore Runtime APIクライアント
 * 
 * AWS公式ドキュメント参照:
 * https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-invoke-agent.html
 * https://aws.amazon.com/blogs/machine-learning/set-up-custom-domain-names-for-amazon-bedrock-agentcore-runtime-agents/
 * 
 * エンドポイント形式:
 * https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{EncodedAgentARN}/invocations
 */

// AgentCore Runtime設定
const AGENTCORE_CONFIG = {
  region: process.env.NEXT_PUBLIC_AGENTCORE_REGION || 'ap-northeast-1',
  runtimeArn: process.env.NEXT_PUBLIC_AGENTCORE_RUNTIME_ARN || '',
};

/**
 * AgentCore RuntimeエンドポイントURLを生成
 */
function getAgentCoreEndpoint(): string {
  const { region, runtimeArn } = AGENTCORE_CONFIG;
  
  if (!runtimeArn) {
    console.warn('NEXT_PUBLIC_AGENTCORE_RUNTIME_ARN is not set');
    return '';
  }
  
  const encodedArn = encodeURIComponent(runtimeArn);
  return `https://bedrock-agentcore.${region}.amazonaws.com/runtimes/${encodedArn}/invocations`;
}

export class AgentCoreApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    message: string
  ) {
    super(message);
    this.name = 'AgentCoreApiError';
  }
}

/**
 * Cognito認証トークンを取得
 */
async function getAuthToken(): Promise<string | null> {
  try {
    const session = await fetchAuthSession();
    return session.tokens?.idToken?.toString() || null;
  } catch {
    console.log('No authenticated session');
    return null;
  }
}

/**
 * AgentCore Runtime /invocations APIを呼び出す
 */
async function invokeAgentCore<T>(
  action: string,
  payload: Record<string, unknown> | object,
  sessionId?: string
): Promise<T> {
  const endpoint = getAgentCoreEndpoint();
  
  if (!endpoint) {
    throw new AgentCoreApiError(500, 'Configuration Error', 'AgentCore Runtime ARN is not configured');
  }
  
  const token = await getAuthToken();
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  // AgentCore Runtimeセッション管理用ヘッダー
  if (sessionId) {
    headers['X-Amzn-Bedrock-AgentCore-Runtime-Session-Id'] = sessionId;
  }
  
  // /invocations APIにリクエストを送信
  // action: 内部でルーティングするためのアクション識別子
  const body = {
    input: {
      action,
      ...payload,
    },
  };
  
  const response = await fetch(endpoint, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new AgentCoreApiError(
      response.status,
      response.statusText,
      errorText || `AgentCore API Error: ${response.status}`
    );
  }
  
  const data = await response.json();
  
  // AgentCore Runtimeレスポンス形式を処理
  // output.message.content[0].text にJSONが含まれる場合がある
  if (data.output?.message?.content?.[0]?.text) {
    try {
      return JSON.parse(data.output.message.content[0].text);
    } catch {
      // JSONでない場合はそのまま返す
      return data.output.message.content[0].text as T;
    }
  }
  
  return data;
}

// ===========================================
// Session API (AgentCore Runtime経由)
// ===========================================

export interface CreateSessionRequest {
  agent_type?: 'strands' | 'langchain';
  user_id?: string;
}

export interface CreateSessionResponse {
  session_id: string;
  agent_id: string;
  agent_type?: string;
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
  agent_type?: string;
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

export const agentCoreSessionApi = {
  create: (data: CreateSessionRequest) =>
    invokeAgentCore<CreateSessionResponse>('create_session', data as unknown as Record<string, unknown>),

  get: (sessionId: string) =>
    invokeAgentCore<SessionInfo>('get_session', { session_id: sessionId }, sessionId),

  getMessages: (sessionId: string, limit = 50, offset = 0) =>
    invokeAgentCore<{ messages: Message[]; total_count: number }>(
      'get_messages',
      { session_id: sessionId, limit, offset },
      sessionId
    ),

  sendMessage: (sessionId: string, data: SendMessageRequest) =>
    invokeAgentCore<SendMessageResponse>(
      'send_message',
      { session_id: sessionId, ...data },
      sessionId
    ),

  end: (sessionId: string) =>
    invokeAgentCore<void>('end_session', { session_id: sessionId }, sessionId),
};

// ===========================================
// Direct Chat API (シンプルなプロンプト送信)
// ===========================================

export interface ChatRequest {
  prompt: string;
  session_id?: string;
}

export interface ChatResponse {
  content: string;
  timestamp: string;
}

export const agentCoreChatApi = {
  /**
   * シンプルなプロンプト送信（セッション管理なし）
   */
  send: async (prompt: string, sessionId?: string): Promise<ChatResponse> => {
    const endpoint = getAgentCoreEndpoint();
    
    if (!endpoint) {
      throw new AgentCoreApiError(500, 'Configuration Error', 'AgentCore Runtime ARN is not configured');
    }
    
    const token = await getAuthToken();
    
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    if (sessionId) {
      headers['X-Amzn-Bedrock-AgentCore-Runtime-Session-Id'] = sessionId;
    }
    
    const response = await fetch(endpoint, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        input: { prompt },
      }),
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new AgentCoreApiError(
        response.status,
        response.statusText,
        errorText || `AgentCore API Error: ${response.status}`
      );
    }
    
    const data = await response.json();
    
    // AgentCore Runtimeレスポンス形式
    const content = data.output?.message?.content?.[0]?.text || '';
    const timestamp = data.output?.timestamp || new Date().toISOString();
    
    return { content, timestamp };
  },
};

// ===========================================
// Service API (AgentCore Runtime経由)
// ===========================================

export interface ServiceExecuteRequest {
  instruction: string;
  agent_type?: 'strands' | 'langchain';
  tools?: Record<string, unknown>[];
}

export interface ServiceExecuteResponse {
  response_id: string;
  content: string;
  tool_calls?: Record<string, unknown>[];
  latency_ms: number;
  metadata?: Record<string, unknown>;
}

const createAgentCoreServiceApi = (serviceName: string) => ({
  execute: (data: ServiceExecuteRequest) =>
    invokeAgentCore<ServiceExecuteResponse>(`service_${serviceName}_execute`, data as unknown as Record<string, unknown>),
});

export const agentCoreServiceApi = {
  runtime: createAgentCoreServiceApi('runtime'),
  memory: createAgentCoreServiceApi('memory'),
  gateway: createAgentCoreServiceApi('gateway'),
  identity: createAgentCoreServiceApi('identity'),
  codeInterpreter: createAgentCoreServiceApi('code_interpreter'),
  browser: createAgentCoreServiceApi('browser'),
  observability: createAgentCoreServiceApi('observability'),
  evaluations: createAgentCoreServiceApi('evaluations'),
  policy: createAgentCoreServiceApi('policy'),
};

// ===========================================
// Agent Info API
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

export interface ToolInfo {
  name: string;
  description: string;
  available: boolean;
}

export const agentCoreAgentApi = {
  getInfo: () => invokeAgentCore<AgentInfo>('get_agent_info', {}),
  getComparison: () => invokeAgentCore<AgentComparison>('get_agent_comparison', {}),
  getTools: () =>
    invokeAgentCore<{ agent_type: string; tools: ToolInfo[]; total_count: number }>(
      'get_agent_tools',
      {}
    ),
};

// ===========================================
// Health API
// ===========================================

export const agentCoreHealthApi = {
  check: () => invokeAgentCore<{ status: string }>('health_check', {}),
};

// ===========================================
// Benchmark API
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

export const agentCoreBenchmarkApi = {
  run: (data: BenchmarkRequest) =>
    invokeAgentCore<{ results: BenchmarkResult[] }>('run_benchmark', data),
  getResults: () =>
    invokeAgentCore<{ results: BenchmarkResult[] }>('get_benchmark_results', {}),
};

// ===========================================
// Export convenience functions
// ===========================================

export { getAgentCoreEndpoint, getAuthToken };
