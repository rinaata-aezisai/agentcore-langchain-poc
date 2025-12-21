'use client';

import { fetchAuthSession } from 'aws-amplify/auth';
import { SignatureV4 } from '@smithy/signature-v4';
import { Sha256 } from '@aws-crypto/sha256-js';
import { HttpRequest } from '@smithy/protocol-http';

/**
 * Backend API Client
 * 
 * AgentCore Runtime と LangChain Lambda に直接接続するクライアント。
 * IAM認証 (SigV4) を使用。
 */

// ===========================================
// Deployed Service Configuration
// ===========================================

const SERVICES = {
  langchain: {
    url: 'https://fqr4tujkvmwtd6kn57wl5zhvqe0rqcjr.lambda-url.us-east-1.on.aws',
    region: 'us-east-1',
    service: 'lambda',
  },
  agentcore: {
    runtimeArn: 'arn:aws:bedrock-agentcore:us-east-1:226484346947:runtime/agentcore_strands_dev-sSCXyh2bVa',
    endpointId: 'agentcore_strands_dev_endpoint',
    region: 'us-east-1',
    service: 'bedrock-agentcore',
  },
};

// レガシー互換用
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
  
  // 3. デフォルト - LangChain Lambda URL
  cachedApiUrl = SERVICES.langchain.url;
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

// ===========================================
// SigV4 認証
// ===========================================

async function signRequest(
  request: HttpRequest,
  region: string,
  service: string
): Promise<HttpRequest> {
  try {
    const session = await fetchAuthSession();
    const credentials = session.credentials;

    if (!credentials) {
      console.warn('No AWS credentials available, sending unauthenticated request');
      return request;
    }

    const signer = new SignatureV4({
      credentials: {
        accessKeyId: credentials.accessKeyId,
        secretAccessKey: credentials.secretAccessKey,
        sessionToken: credentials.sessionToken,
      },
      region,
      service,
      sha256: Sha256,
    });

    return (await signer.sign(request)) as HttpRequest;
  } catch (error) {
    console.warn('Failed to sign request:', error);
    return request;
  }
}

// ===========================================
// LangChain Lambda API
// ===========================================

async function callLangChainApi<T>(
  path: string,
  method: 'GET' | 'POST' = 'GET',
  body?: Record<string, unknown>
): Promise<T> {
  const config = SERVICES.langchain;
  const url = new URL(path, config.url);

  // HttpRequest 作成
  const request = new HttpRequest({
    method,
    protocol: url.protocol,
    hostname: url.hostname,
    port: url.port ? parseInt(url.port) : undefined,
    path: url.pathname,
    headers: {
      'Content-Type': 'application/json',
      host: url.hostname,
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  // SigV4 署名
  const signedRequest = await signRequest(request, config.region, config.service);

  const response = await fetch(url.toString(), {
    method: signedRequest.method,
    headers: signedRequest.headers as Record<string, string>,
    body: signedRequest.body,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new BackendApiError(response.status, response.statusText, errorText);
  }

  return response.json();
}

// ===========================================
// AgentCore Runtime API (簡易実装)
// ===========================================

async function callAgentCoreApi<T>(
  instruction: string
): Promise<T> {
  const config = SERVICES.agentcore;
  
  // AgentCore Runtime は DataPlane API を使用
  // フロントエンドからは直接呼び出し困難なため、LangChain Lambda 経由でプロキシ
  // 本番環境ではバックエンドプロキシを使用することを推奨
  
  // 一時的にLangChain Lambda経由でAgentCoreエミュレーション
  const response = await callLangChainApi<T>('/api/v1/chat', 'POST', {
    instruction,
    use_tools: false,
    simulate_agentcore: true,
    agentcore_runtime_arn: config.runtimeArn,
    agentcore_endpoint_id: config.endpointId,
  });

  return response;
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

/**
 * 実際のデプロイ済みサービスを呼び出す実装
 */
async function executeOnDeployedService(
  data: ServiceExecuteRequest
): Promise<ServiceExecuteResponse> {
  const startTime = Date.now();
  
  if (data.agent_type === 'langchain') {
    // LangChain Lambda を直接呼び出し
    const response = await callLangChainApi<{
      response_id: string;
      content: string;
      tool_calls: Record<string, unknown>[] | null;
      latency_ms: number;
      metadata: Record<string, unknown>;
    }>('/api/v1/chat', 'POST', {
      instruction: data.instruction,
      use_tools: data.tools && data.tools.length > 0,
      session_id: data.session_id,
    });

    return {
      response_id: response.response_id,
      content: response.content,
      tool_calls: response.tool_calls || undefined,
      latency_ms: response.latency_ms || (Date.now() - startTime),
      metadata: {
        ...response.metadata,
        service: 'langchain',
      },
      framework_features: ['LangChain', 'LangGraph', 'Checkpointing'],
    };
  } else {
    // AgentCore (strands) - Lambda経由でエミュレーション or 直接呼び出し
    // 注: フロントエンドからAgentCore DataPlane APIを直接呼ぶのは制限あり
    // Lambda経由でプロキシする実装
    const response = await callLangChainApi<{
      response_id: string;
      content: string;
      tool_calls: Record<string, unknown>[] | null;
      latency_ms: number;
      metadata: Record<string, unknown>;
    }>('/api/v1/chat', 'POST', {
      instruction: data.instruction,
      use_tools: data.tools && data.tools.length > 0,
      session_id: data.session_id,
      // AgentCore呼び出し用フラグ
      target_service: 'agentcore',
      agentcore_runtime_arn: SERVICES.agentcore.runtimeArn,
    });

    return {
      response_id: response.response_id,
      content: response.content,
      tool_calls: response.tool_calls || undefined,
      latency_ms: response.latency_ms || (Date.now() - startTime),
      metadata: {
        ...response.metadata,
        service: 'agentcore',
      },
      framework_features: ['Strands Agents', 'AWS Native', 'BedrockModel'],
    };
  }
}

const createServiceApi = (serviceName: string) => ({
  /**
   * サービス実行 - デプロイ済みサービスに直接接続
   */
  execute: async (data: ServiceExecuteRequest): Promise<ServiceExecuteResponse> => {
    // デプロイ済みサービスに直接接続
    return executeOnDeployedService(data);
  },

  /**
   * ツール付き実行
   */
  executeWithTools: async (data: ServiceExecuteRequest): Promise<ServiceExecuteResponse> => {
    return executeOnDeployedService({
      ...data,
      tools: data.tools || [{ name: 'default_tools' }],
    });
  },

  /**
   * 両フレームワークで比較実行
   */
  compare: async (data: ServiceExecuteRequest): Promise<ServiceComparisonResult> => {
    const [strandsResult, langchainResult] = await Promise.allSettled([
      executeOnDeployedService({ ...data, agent_type: 'strands' }),
      executeOnDeployedService({ ...data, agent_type: 'langchain' }),
    ]);

    return {
      strands_result: strandsResult.status === 'fulfilled' ? strandsResult.value : undefined,
      langchain_result: langchainResult.status === 'fulfilled' ? langchainResult.value : undefined,
      comparison: {
        strands_success: strandsResult.status === 'fulfilled',
        langchain_success: langchainResult.status === 'fulfilled',
        strands_error: strandsResult.status === 'rejected' ? strandsResult.reason?.message : null,
        langchain_error: langchainResult.status === 'rejected' ? langchainResult.reason?.message : null,
      },
    };
  },

  /**
   * サービス情報取得
   */
  getInfo: (): Promise<ServiceInfo> => {
    // 静的な情報を返す
    return Promise.resolve({
      service: serviceName,
      description: `${serviceName} comparison service`,
      supported_agents: ['strands', 'langchain'],
      strands_features: ['AWS Native', 'Bedrock Integration', 'Policy Support'],
      langchain_features: ['LangGraph', 'Checkpointing', 'Multi-provider'],
      comparison_available: true,
    });
  },
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

