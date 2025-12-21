'use client';

/**
 * Backend API Client
 * 
 * Amplify API Gateway または ECSバックエンドAPIを呼び出すクライアント。
 * 優先順位:
 * 1. NEXT_PUBLIC_API_URL環境変数
 * 2. Amplify outputsのcustom.serviceApiUrl
 * 3. デフォルト (localhost:8000)
 */

// Amplify outputsから取得を試みる
let cachedApiUrl: string | null = null;

const getBackendUrl = (): string => {
  if (cachedApiUrl) {
    return cachedApiUrl;
  }
  
  // 1. 環境変数から取得
  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (envUrl) {
    cachedApiUrl = envUrl;
    return envUrl;
  }
  
  // 2. Amplify outputsから取得（ブラウザ環境のみ）
  if (typeof window !== 'undefined') {
    try {
      // amplify_outputs.jsonはビルド時に埋め込まれる
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const outputs = require('@/../amplify_outputs.json');
      if (outputs?.custom?.serviceApiUrl) {
        const apiUrl = outputs.custom.serviceApiUrl as string;
        cachedApiUrl = apiUrl;
        return apiUrl;
      }
    } catch {
      // amplify_outputs.jsonが見つからない場合は無視
    }
  }
  
  // 3. デフォルト
  cachedApiUrl = 'http://localhost:8000';
  return cachedApiUrl;
};

export class BackendApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    message: string
  ) {
    super(message);
    this.name = 'BackendApiError';
  }
}

/**
 * Backend APIを呼び出す
 */
async function callBackendApi<T>(
  endpoint: string,
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' = 'GET',
  body?: Record<string, unknown>
): Promise<T> {
  const baseUrl = getBackendUrl();
  const url = `${baseUrl}${endpoint}`;
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  
  const options: RequestInit = {
    method,
    headers,
  };
  
  if (body) {
    options.body = JSON.stringify(body);
  }
  
  try {
    const response = await fetch(url, options);
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new BackendApiError(
        response.status,
        response.statusText,
        errorText || `Backend API Error: ${response.status}`
      );
    }
    
    return await response.json();
  } catch (error) {
    if (error instanceof BackendApiError) {
      throw error;
    }
    throw new BackendApiError(
      500,
      'Network Error',
      error instanceof Error ? error.message : 'Unknown network error'
    );
  }
}

// ===========================================
// Service API Types
// ===========================================

export interface ServiceExecuteRequest {
  instruction: string;
  agent_type: 'strands' | 'langchain';
  tools?: Record<string, unknown>[];
  use_memory?: boolean;
  session_id?: string;
}

export interface ServiceExecuteResponse {
  response_id: string;
  content: string;
  tool_calls?: Record<string, unknown>[];
  latency_ms: number;
  metadata?: Record<string, unknown>;
  framework_features?: string[];
}

export interface ServiceComparisonResult {
  strands_result?: ServiceExecuteResponse;
  langchain_result?: ServiceExecuteResponse;
  comparison?: Record<string, unknown>;
}

export interface ServiceInfo {
  service: string;
  description: string;
  supported_agents: string[];
  strands_features: string[];
  langchain_features: string[];
  comparison_available: boolean;
}

// ===========================================
// Service API - サービス別エンドポイント
// ===========================================

const createServiceApi = (serviceName: string) => ({
  /**
   * サービス実行
   */
  execute: (data: ServiceExecuteRequest): Promise<ServiceExecuteResponse> =>
    callBackendApi<ServiceExecuteResponse>(
      `/services/${serviceName}/execute`,
      'POST',
      data as unknown as Record<string, unknown>
    ),

  /**
   * ツール付き実行
   */
  executeWithTools: (data: ServiceExecuteRequest): Promise<ServiceExecuteResponse> =>
    callBackendApi<ServiceExecuteResponse>(
      `/services/${serviceName}/execute-with-tools`,
      'POST',
      data as unknown as Record<string, unknown>
    ),

  /**
   * 両フレームワークで比較実行
   */
  compare: (data: ServiceExecuteRequest): Promise<ServiceComparisonResult> =>
    callBackendApi<ServiceComparisonResult>(
      `/services/${serviceName}/compare`,
      'POST',
      data as unknown as Record<string, unknown>
    ),

  /**
   * サービス情報取得
   */
  getInfo: (): Promise<ServiceInfo> =>
    callBackendApi<ServiceInfo>(`/services/${serviceName}/info`),
});

// ===========================================
// 全サービスAPI
// ===========================================

export const backendServiceApi = {
  runtime: createServiceApi('runtime'),
  memory: createServiceApi('memory'),
  gateway: createServiceApi('gateway'),
  identity: createServiceApi('identity'),
  codeInterpreter: createServiceApi('code-interpreter'),
  browser: createServiceApi('browser'),
  observability: createServiceApi('observability'),
  evaluations: createServiceApi('evaluations'),
  policy: createServiceApi('policy'),
};

// ===========================================
// Health API
// ===========================================

export const backendHealthApi = {
  check: (): Promise<{ status: string; version?: string }> =>
    callBackendApi<{ status: string; version?: string }>('/health'),
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

export const backendAgentApi = {
  getInfo: (): Promise<AgentInfo> =>
    callBackendApi<AgentInfo>('/agents/info'),
  
  compare: (): Promise<{ strands: AgentInfo; langchain: AgentInfo }> =>
    callBackendApi<{ strands: AgentInfo; langchain: AgentInfo }>('/agents/compare'),
};

// ===========================================
// Export convenience functions
// ===========================================

export { getBackendUrl, callBackendApi };

