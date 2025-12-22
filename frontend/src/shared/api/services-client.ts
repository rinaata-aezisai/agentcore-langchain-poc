/**
 * Services API Client
 *
 * AgentCore と LangChain 両サービスへの統一クライアント。
 * IAM認証 (SigV4) を使用。
 */

import { fetchAuthSession } from "aws-amplify/auth";
import { SignatureV4 } from "@smithy/signature-v4";
import { Sha256 } from "@aws-crypto/sha256-js";
import { HttpRequest } from "@smithy/protocol-http";

// ===========================================
// Types
// ===========================================

export interface ChatRequest {
  instruction: string;
  session_id?: string;
  use_tools?: boolean;
}

export interface ToolCall {
  tool_name: string;
  tool_input: Record<string, unknown>;
  tool_output?: unknown;
}

export interface ChatResponse {
  response_id: string;
  content: string;
  tool_calls: ToolCall[] | null;
  latency_ms: number;
  metadata: {
    service: "agentcore" | "langchain";
    framework: string;
    model_id: string;
    region: string;
    [key: string]: unknown;
  };
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  model_id: string;
  region: string;
  timestamp: string;
}

export interface ServiceInfo {
  service: string;
  framework: string;
  version: string;
  model_id: string;
  region: string;
  features: string[];
  tools: string[];
}

export type ServiceType = "agentcore" | "langchain";

// ===========================================
// Configuration
// ===========================================

interface ServiceConfig {
  agentcore: {
    url: string;
    region: string;
  };
  langchain: {
    url: string;
    region: string;
  };
}

// デプロイ済みのサービス設定
const DEPLOYED_SERVICES = {
  langchain: {
    url: "https://hqtuy24tbjdzbobyg4tzsr2xhe0rjmbx.lambda-url.us-east-1.on.aws",
    region: "us-east-1",
    type: "lambda" as const,
  },
  agentcore: {
    runtimeArn: "arn:aws:bedrock-agentcore:us-east-1:226484346947:runtime/agentcore_strands_dev-sSCXyh2bVa",
    endpointId: "agentcore_strands_dev_endpoint",
    region: "us-east-1",
    type: "agentcore-runtime" as const,
  },
};

// 環境変数またはAmplify outputsから取得
function getServiceConfig(): ServiceConfig {
  // 環境変数でオーバーライド可能
  const agentcoreUrl =
    process.env.NEXT_PUBLIC_AGENTCORE_URL ||
    DEPLOYED_SERVICES.agentcore.runtimeArn;
  const langchainUrl =
    process.env.NEXT_PUBLIC_LANGCHAIN_URL ||
    DEPLOYED_SERVICES.langchain.url;
  const region = process.env.NEXT_PUBLIC_AWS_REGION || "us-east-1";

  return {
    agentcore: {
      url: agentcoreUrl,
      region,
    },
    langchain: {
      url: langchainUrl,
      region,
    },
  };
}

// ===========================================
// SigV4 Signing
// ===========================================

async function signRequest(
  request: HttpRequest,
  region: string
): Promise<HttpRequest> {
  const session = await fetchAuthSession();
  const credentials = session.credentials;

  if (!credentials) {
    throw new Error("No credentials available");
  }

  const signer = new SignatureV4({
    credentials: {
      accessKeyId: credentials.accessKeyId,
      secretAccessKey: credentials.secretAccessKey,
      sessionToken: credentials.sessionToken,
    },
    region,
    service: "lambda", // Lambda Function URL の場合
    sha256: Sha256,
  });

  return (await signer.sign(request)) as HttpRequest;
}

// ===========================================
// API Client
// ===========================================

async function callServiceApi<T>(
  service: ServiceType,
  path: string,
  method: "GET" | "POST" = "GET",
  body?: Record<string, unknown>
): Promise<T> {
  const config = getServiceConfig();
  const serviceConfig = config[service];

  const url = new URL(path, serviceConfig.url);

  // HttpRequest 作成
  const request = new HttpRequest({
    method,
    protocol: url.protocol,
    hostname: url.hostname,
    port: url.port ? parseInt(url.port) : undefined,
    path: url.pathname,
    headers: {
      "Content-Type": "application/json",
      host: url.hostname,
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  // SigV4 署名
  const signedRequest = await signRequest(request, serviceConfig.region);

  // fetch で送信
  const response = await fetch(url.toString(), {
    method: signedRequest.method,
    headers: signedRequest.headers as Record<string, string>,
    body: signedRequest.body,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Service API error: ${response.status} - ${errorText}`);
  }

  return response.json();
}

// ===========================================
// Public API
// ===========================================

/**
 * チャット実行
 */
export async function chat(
  service: ServiceType,
  request: ChatRequest
): Promise<ChatResponse> {
  return callServiceApi<ChatResponse>(service, "/api/v1/chat", "POST", request as unknown as Record<string, unknown>);
}

/**
 * ツール付きチャット実行
 */
export async function chatWithTools(
  service: ServiceType,
  request: Omit<ChatRequest, "use_tools">
): Promise<ChatResponse> {
  return callServiceApi<ChatResponse>(service, "/api/v1/chat/tools", "POST", {
    ...request,
    use_tools: true,
  } as unknown as Record<string, unknown>);
}

/**
 * ヘルスチェック
 */
export async function healthCheck(
  service: ServiceType
): Promise<HealthResponse> {
  return callServiceApi<HealthResponse>(service, "/api/v1/health", "GET");
}

/**
 * サービス情報取得
 */
export async function getServiceInfo(
  service: ServiceType
): Promise<ServiceInfo> {
  return callServiceApi<ServiceInfo>(service, "/api/v1/info", "GET");
}

/**
 * 両サービスで同じ入力をテスト（比較用）
 */
export async function compareServices(
  request: ChatRequest
): Promise<{
  agentcore: ChatResponse;
  langchain: ChatResponse;
}> {
  const [agentcoreResult, langchainResult] = await Promise.all([
    chat("agentcore", request),
    chat("langchain", request),
  ]);

  return {
    agentcore: agentcoreResult,
    langchain: langchainResult,
  };
}

/**
 * 両サービスのヘルスチェック
 */
export async function checkAllServices(): Promise<{
  agentcore: HealthResponse | { error: string };
  langchain: HealthResponse | { error: string };
}> {
  const [agentcoreResult, langchainResult] = await Promise.allSettled([
    healthCheck("agentcore"),
    healthCheck("langchain"),
  ]);

  return {
    agentcore:
      agentcoreResult.status === "fulfilled"
        ? agentcoreResult.value
        : { error: agentcoreResult.reason?.message || "Unknown error" },
    langchain:
      langchainResult.status === "fulfilled"
        ? langchainResult.value
        : { error: langchainResult.reason?.message || "Unknown error" },
  };
}

// ===========================================
// Simple Client (No SigV4, for local development)
// ===========================================

/**
 * シンプルなAPIクライアント（ローカル開発用、認証なし）
 */
export async function callServiceApiSimple<T>(
  service: ServiceType,
  path: string,
  method: "GET" | "POST" = "GET",
  body?: Record<string, unknown>
): Promise<T> {
  const config = getServiceConfig();
  const serviceConfig = config[service];

  const url = new URL(path, serviceConfig.url);

  const response = await fetch(url.toString(), {
    method,
    headers: {
      "Content-Type": "application/json",
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Service API error: ${response.status} - ${errorText}`);
  }

  return response.json();
}

/**
 * チャット実行（認証なし、ローカル開発用）
 */
export async function chatSimple(
  service: ServiceType,
  request: ChatRequest
): Promise<ChatResponse> {
  return callServiceApiSimple<ChatResponse>(
    service,
    "/api/v1/chat",
    "POST",
    request as unknown as Record<string, unknown>
  );
}

