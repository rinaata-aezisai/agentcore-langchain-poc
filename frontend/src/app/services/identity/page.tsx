"use client";

import { ServiceTest } from "@/widgets/service-test";

const testCases = [
  {
    id: "identity-auth",
    name: "認証テスト",
    endpoint: "/services/identity/authenticate",
    method: "POST" as const,
    body: { credentials: { api_key: "demo-api-key-test" } },
    expectedBehavior: "APIキーで認証を実行",
  },
  {
    id: "identity-validate",
    name: "トークン検証",
    endpoint: "/services/identity/validate",
    method: "POST" as const,
    body: { token: "test-token-123" },
    expectedBehavior: "トークンの有効性を検証",
  },
  {
    id: "identity-permissions",
    name: "権限一覧取得",
    endpoint: "/services/identity/permissions/test-identity",
    method: "GET" as const,
    expectedBehavior: "アイデンティティの権限一覧を取得",
  },
];

export default function IdentityPage() {
  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-2 text-sm text-slate-400 mb-2">
          <span>Services</span>
          <span>/</span>
          <span className="text-white">Identity</span>
        </div>
        <h1 className="text-2xl font-bold text-white">Identity Service</h1>
      </div>

      <ServiceTest
        serviceName="Identity"
        serviceKey="identity"
        serviceDescription="エージェント認証・認可管理。トークン発行、権限チェック、セッション管理。"
        testCases={testCases}
        strandsFeatures={[
          "AgentCore Identity統合",
          "AWS IAM連携",
          "自動トークン管理",
          "クロスアカウントアクセス",
        ]}
        langchainFeatures={[
          "カスタム認証実装",
          "JWT/OAuth2対応",
          "AWS Cognito統合",
          "柔軟なプロバイダー",
        ]}
        strandsExample={`# AgentCore Identity
# AWS IAMベースの認証が自動適用

# Bedrock Agent呼び出し時は
# IAMロールで認証
import boto3

client = boto3.client('bedrock-agent-runtime')
response = client.invoke_agent(
    agentId='<agent-id>',
    sessionId='<session-id>',
)`}
        langchainExample={`import jwt

# JWT認証
def authenticate(token: str):
    payload = jwt.decode(
        token,
        SECRET_KEY,
        algorithms=["HS256"]
    )
    return payload

# AWS Cognito統合
from langchain.auth import CognitoAuth

auth = CognitoAuth(
    user_pool_id="us-east-1_xxx"
)`}
      />
    </div>
  );
}
