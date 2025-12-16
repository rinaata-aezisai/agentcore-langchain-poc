"use client";

import { ServiceTest } from "@/widgets/service-test";

const testCases = [
  {
    id: "gateway-routes",
    name: "ルート一覧取得",
    endpoint: "/services/gateway/routes",
    method: "GET" as const,
    expectedBehavior: "登録済みルートの一覧を取得",
  },
  {
    id: "gateway-metrics",
    name: "メトリクス取得",
    endpoint: "/services/gateway/metrics",
    method: "GET" as const,
    expectedBehavior: "API使用状況のメトリクスを取得",
  },
  {
    id: "gateway-ratelimit",
    name: "レート制限状態",
    endpoint: "/services/gateway/rate-limit",
    method: "GET" as const,
    expectedBehavior: "レート制限の現在状態を取得",
  },
];

export default function GatewayPage() {
  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-2 text-sm text-slate-400 mb-2">
          <span>Services</span>
          <span>/</span>
          <span className="text-white">Gateway</span>
        </div>
        <h1 className="text-2xl font-bold text-white">Gateway Service</h1>
      </div>

      <ServiceTest
        serviceName="Gateway"
        serviceKey="gateway"
        serviceDescription="エージェントAPIのルーティングとレート制限管理。認証・認可の統合。"
        testCases={testCases}
        strandsFeatures={[
          "AgentCore Gateway統合",
          "自動認証フロー",
          "内蔵レート制限",
          "AWS API Gateway連携",
        ]}
        langchainFeatures={[
          "LangServe統合",
          "FastAPI自動生成",
          "OpenAPI/Swagger対応",
          "Playground UI",
        ]}
        strandsExample={`# AgentCore Gateway
# 自動的にエンドポイントが生成される

# AWS経由でデプロイ
# bedrock-agent-runtime invoke-agent \\
#   --agent-id <agent-id> \\
#   --session-id <session-id>`}
        langchainExample={`from langserve import add_routes
from fastapi import FastAPI

app = FastAPI()

# LangChain Runnableをルートとして登録
add_routes(
    app,
    runnable,
    path="/chat",
)

# 自動生成されるエンドポイント:
# POST /chat/invoke
# POST /chat/stream
# GET /chat/playground`}
      />
    </div>
  );
}
