"""FastAPI Main Application

AgentCore vs LangChain PoC - 9サービス比較API
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import sessions, agents, health
from api.routers.services import services_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up AI Agent API...")
    print("Available services: runtime, memory, gateway, identity, code-interpreter, browser, observability, evaluations, policy")
    yield
    print("Shutting down...")


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Agent API",
        description="""
AgentCore vs LangChain PoC API

## サービス一覧
- **Runtime**: エージェント実行環境
- **Memory**: 会話履歴・長期記憶
- **Gateway**: API管理
- **Identity**: 認証・認可
- **Code Interpreter**: コード実行
- **Browser**: ブラウザ自動化
- **Observability**: 監視・トレーシング
- **Evaluations**: 評価・ベンチマーク
- **Policy**: Guardrails・ポリシー

各サービスは `agent_type` パラメータで `strands` (AgentCore) または `langchain` を切り替え可能。
        """,
        version="0.2.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:3001"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Legacy routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])
    app.include_router(agents.router, prefix="/agents", tags=["Agents"])
    
    # 9サービス用ルーター
    app.include_router(services_router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)


