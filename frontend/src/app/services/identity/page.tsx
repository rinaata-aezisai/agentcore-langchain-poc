"use client";

import { ServiceTest } from "@/widgets/service-test";

const testCases = [
  {
    id: "identity-auth",
    name: "認証情報管理",
    prompt: "現在のユーザー認証状態を確認してください。",
    expectedBehavior: "認証情報の適切な管理",
  },
  {
    id: "identity-oauth",
    name: "OAuth連携",
    prompt: "外部サービスとのOAuth認証フローを説明してください。",
    expectedBehavior: "OAuth対応の確認",
  },
  {
    id: "identity-role",
    name: "ロールベースアクセス",
    prompt: "ユーザーロールに基づいたアクセス制御を行ってください。",
    expectedBehavior: "RBAC実装の確認",
  },
  {
    id: "identity-token",
    name: "トークン管理",
    prompt: "セッショントークンの有効期限を確認してください。",
    expectedBehavior: "トークンライフサイクル管理",
  },
];

export default function IdentityPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-8">
      <div className="mb-6">
        <div className="flex items-center gap-2 text-sm text-slate-400 mb-2">
          <span>Services</span>
          <span>/</span>
          <span className="text-white">Identity</span>
        </div>
        <h1 className="text-2xl font-bold text-white">Identity Service</h1>
      </div>

      <ServiceTest
        serviceName="Identity"
        serviceDescription="エージェント用のアイデンティティ・アクセス管理。OAuth、RBAC対応。"
        testCases={testCases}
        strandsFeatures={[
          "AWS IAM統合",
          "OAuth 2.0サポート",
          "エージェント間認証",
          "動的クレデンシャル管理",
        ]}
        langchainFeatures={[
          "カスタム実装が必要",
          "外部認証サービス連携",
          "ミドルウェアでの実装",
        ]}
        strandsExample={`from strands.identity import Identity

identity = Identity(
    oauth_provider="cognito",
    scopes=["read", "write"]
)
agent = Agent(
    model=model,
    identity=identity
)`}
        langchainExample={`# LangChainでは標準機能なし
# カスタム実装が必要

class AuthMiddleware:
    def __init__(self, auth_service):
        self.auth = auth_service
    
    async def authenticate(self, request):
        return await self.auth.verify(request.token)`}
      />
    </div>
  );
}

