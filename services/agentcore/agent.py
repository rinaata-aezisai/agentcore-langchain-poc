"""AgentCore Runtime Service - Strands Agents Implementation

AWS Bedrock AgentCore Runtime用のFastAPIサービス。
POST /invocations と GET /ping の必須エンドポイントを実装。

比較検証用の統一APIも提供:
- POST /api/v1/chat: チャット実行
- POST /api/v1/chat/tools: ツール付きチャット実行
- GET /api/v1/health: ヘルスチェック
- GET /api/v1/info: サービス情報
"""

import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from strands import Agent
from strands.models import BedrockModel

from tools import AVAILABLE_TOOLS

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# ===========================================
# Configuration
# ===========================================

MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
ENABLE_CACHING = os.getenv("ENABLE_CACHING", "true").lower() == "true"

# ===========================================
# FastAPI Application
# ===========================================

app = FastAPI(
    title="AgentCore Service - Strands Agents",
    description="AWS Bedrock AgentCore Runtime with Strands Agents",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===========================================
# Strands Agent Setup
# ===========================================

bedrock_model = BedrockModel(
    model_id=MODEL_ID,
    region_name=AWS_REGION,
    temperature=0.7,
    max_tokens=4096,
)

SYSTEM_PROMPT = """あなたは AWS Bedrock AgentCore (Strands Agents) を使用した親切なAIアシスタントです。

## 特徴
- AWS Bedrockとのネイティブ統合
- AgentCore Memory APIによる高度なメモリ管理
- プロンプト/ツールキャッシングによる効率化
- ツール呼び出しの自動ループ

## 原則
1. 正確で有用な情報を提供する
2. 不確かな場合は明確に伝える
3. ツールが利用可能な場合は適切に活用する
4. 日本語で応答する（ユーザーが英語の場合は英語で）

## 利用可能なツール
- get_current_weather: 天気情報取得
- search_documents: ドキュメント検索
- calculate: 数式計算
- create_task: タスク作成
- fetch_url: URL取得
- get_current_time: 現在時刻取得
- analyze_text: テキスト分析
"""

logger.info(f"Strands Agent initialized with model: {MODEL_ID}")

# ===========================================
# Request/Response Models
# ===========================================


class ChatRequest(BaseModel):
    """統一チャットリクエスト"""

    instruction: str = Field(..., description="ユーザーの入力")
    session_id: str | None = Field(None, description="セッションID")
    use_tools: bool = Field(False, description="ツールを使用するか")


class ChatResponse(BaseModel):
    """統一チャットレスポンス"""

    response_id: str
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    latency_ms: int
    metadata: dict[str, Any]


class InvocationInput(BaseModel):
    """AgentCore Invocation入力"""

    prompt: str | None = None
    instruction: str | None = None
    messages: list[dict[str, Any]] | None = None
    tools: list[dict[str, Any]] | None = None
    session_id: str | None = None
    use_tools: bool = False


class InvocationRequest(BaseModel):
    """AgentCore Invocationリクエスト"""

    input: InvocationInput


class HealthResponse(BaseModel):
    """ヘルスチェックレスポンス"""

    status: str
    service: str
    version: str
    model_id: str
    region: str
    timestamp: str


class ServiceInfo(BaseModel):
    """サービス情報"""

    service: str
    framework: str
    version: str
    model_id: str
    region: str
    features: list[str]
    tools: list[str]


# ===========================================
# Helper Functions
# ===========================================


def create_agent(use_tools: bool = False) -> Agent:
    """Strands Agentを作成"""
    agent_kwargs = {
        "model": bedrock_model,
        "system_prompt": SYSTEM_PROMPT,
    }
    if use_tools:
        agent_kwargs["tools"] = AVAILABLE_TOOLS

    return Agent(**agent_kwargs)


def extract_response_text(result: Any) -> str:
    """Strands Agentのレスポンスからテキストを抽出"""
    if hasattr(result, "message"):
        msg = result.message
        if hasattr(msg, "content") and msg.content:
            texts = []
            for content_item in msg.content:
                if hasattr(content_item, "text"):
                    texts.append(content_item.text)
                elif isinstance(content_item, dict) and "text" in content_item:
                    texts.append(content_item["text"])
            return "".join(texts)
        elif isinstance(msg, str):
            return msg
    return str(result)


def extract_tool_calls(result: Any) -> list[dict[str, Any]] | None:
    """ツール呼び出し情報を抽出"""
    if hasattr(result, "tool_calls") and result.tool_calls:
        return [
            {
                "tool_name": tc.name if hasattr(tc, "name") else str(tc),
                "tool_input": tc.input if hasattr(tc, "input") else {},
                "tool_output": tc.output if hasattr(tc, "output") else None,
            }
            for tc in result.tool_calls
        ]
    return None


# ===========================================
# AgentCore Required Endpoints
# ===========================================


@app.post("/invocations")
async def invoke_agent(request: InvocationRequest):
    """AgentCore Runtime必須エンドポイント: エージェント呼び出し"""
    try:
        user_message = request.input.prompt or request.input.instruction

        if not user_message:
            raise HTTPException(status_code=400, detail="No prompt or instruction provided")

        start_time = time.time()
        logger.info(f"Processing invocation: {user_message[:100]}...")

        use_tools = request.input.use_tools or bool(request.input.tools)
        agent = create_agent(use_tools=use_tools)
        result = agent(user_message)

        response_text = extract_response_text(result)
        tool_calls = extract_tool_calls(result)
        latency_ms = int((time.time() - start_time) * 1000)

        logger.info(f"Response generated in {latency_ms}ms")

        return {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [{"text": response_text}],
                },
                "tool_calls": tool_calls,
                "timestamp": datetime.utcnow().isoformat(),
            },
            "metadata": {
                "latency_ms": latency_ms,
                "model_id": MODEL_ID,
                "provider": "strands-agents",
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Agent processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ping")
async def ping():
    """AgentCore Runtime必須エンドポイント: ヘルスチェック"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# ===========================================
# Unified Comparison API
# ===========================================


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """統一チャットAPI（比較検証用）"""
    try:
        start_time = time.time()
        logger.info(f"Chat request: {request.instruction[:100]}...")

        agent = create_agent(use_tools=request.use_tools)
        result = agent(request.instruction)

        response_text = extract_response_text(result)
        tool_calls = extract_tool_calls(result)
        latency_ms = int((time.time() - start_time) * 1000)

        return ChatResponse(
            response_id=str(uuid.uuid4()),
            content=response_text,
            tool_calls=tool_calls,
            latency_ms=latency_ms,
            metadata={
                "service": "agentcore",
                "framework": "strands-agents",
                "model_id": MODEL_ID,
                "region": AWS_REGION,
                "caching_enabled": ENABLE_CACHING,
                "tools_used": len(tool_calls) if tool_calls else 0,
            },
        )

    except Exception as e:
        logger.exception(f"Chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/chat/tools", response_model=ChatResponse)
async def chat_with_tools(request: ChatRequest):
    """ツール付きチャットAPI（比較検証用）"""
    request.use_tools = True
    return await chat(request)


@app.get("/api/v1/health", response_model=HealthResponse)
async def health():
    """ヘルスチェックAPI"""
    return HealthResponse(
        status="healthy",
        service="agentcore",
        version="1.0.0",
        model_id=MODEL_ID,
        region=AWS_REGION,
        timestamp=datetime.utcnow().isoformat(),
    )


@app.get("/api/v1/info", response_model=ServiceInfo)
async def info():
    """サービス情報API"""
    return ServiceInfo(
        service="agentcore",
        framework="strands-agents",
        version="1.0.0",
        model_id=MODEL_ID,
        region=AWS_REGION,
        features=[
            "bedrock_native_integration",
            "agentcore_memory_api",
            "prompt_caching",
            "tool_caching",
            "automatic_tool_loop",
            "streaming_support",
        ],
        tools=[t.__name__ if hasattr(t, "__name__") else str(t) for t in AVAILABLE_TOOLS],
    )


@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "service": "AgentCore Service - Strands Agents",
        "version": "1.0.0",
        "model": MODEL_ID,
        "region": AWS_REGION,
        "endpoints": {
            "agentcore_required": ["/invocations", "/ping"],
            "comparison_api": [
                "/api/v1/chat",
                "/api/v1/chat/tools",
                "/api/v1/health",
                "/api/v1/info",
            ],
        },
    }


# ===========================================
# Main
# ===========================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)

