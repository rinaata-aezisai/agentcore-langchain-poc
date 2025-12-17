"""AgentCore Runtime Agent - FastAPI + Strands Agents

AWS公式ドキュメントに基づく実装:
https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/getting-started-custom.html

必須エンドポイント:
- POST /invocations: エージェント呼び出し
- GET /ping: ヘルスチェック

追加エンドポイント（ダッシュボード用）:
- GET /health: ヘルスチェック
- POST /sessions: セッション作成
- GET /sessions/{session_id}: セッション取得
- POST /sessions/{session_id}/messages: メッセージ送信
- DELETE /sessions/{session_id}: セッション終了
- GET /agents/info: エージェント情報
- GET /agents/comparison: エージェント比較
- GET /agents/tools: 利用可能ツール
"""

import json
import logging
import os
import sys
import uuid
import time
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from strands import Agent
from strands.models import BedrockModel

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# ===========================================
# FastAPI Application
# ===========================================

app = FastAPI(
    title="AgentCore Runtime Agent",
    description="Strands Agents on AgentCore Runtime - Dashboard API",
    version="1.0.0",
)

# CORS設定
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

MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# BedrockModel初期化
bedrock_model = BedrockModel(
    model_id=MODEL_ID,
    region_name=AWS_REGION,
)

# Strands Agent初期化
strands_agent = Agent(
    model=bedrock_model,
    system_prompt="""あなたは親切で知識豊富なAIアシスタントです。
ユーザーの質問に対して、正確で役立つ回答を提供してください。
日本語で応答してください。""",
)

logger.info(f"Strands Agent initialized with model: {MODEL_ID}")

# ===========================================
# In-Memory Session Storage
# ===========================================

sessions: dict[str, dict] = {}

# ===========================================
# Request/Response Models
# ===========================================

# --- Invocation Models (AgentCore必須) ---

class InvocationInput(BaseModel):
    prompt: str
    messages: list[dict[str, Any]] | None = None
    tools: list[dict[str, Any]] | None = None


class InvocationRequest(BaseModel):
    input: InvocationInput


class MessageContent(BaseModel):
    text: str


class InvocationMessage(BaseModel):
    role: str = "assistant"
    content: list[MessageContent]


class InvocationOutput(BaseModel):
    message: InvocationMessage
    timestamp: str


class InvocationResponse(BaseModel):
    output: InvocationOutput


# --- Session Models (ダッシュボード用) ---

class CreateSessionRequest(BaseModel):
    agent_id: str | None = None
    user_id: str | None = None


class CreateSessionResponse(BaseModel):
    session_id: str
    agent_id: str
    created_at: str


class SendMessageRequest(BaseModel):
    instruction: str
    tools: list[dict[str, Any]] | None = None


class SendMessageResponse(BaseModel):
    response_id: str
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    latency_ms: int
    metadata: dict[str, Any] | None = None


class SessionMessage(BaseModel):
    id: str
    role: str
    content: str
    created_at: str


class SessionInfo(BaseModel):
    session_id: str
    agent_id: str
    state: str
    created_at: str
    message_count: int


class MessagesResponse(BaseModel):
    messages: list[SessionMessage]
    total_count: int


# --- Agent Models (ダッシュボード用) ---

class AgentInfo(BaseModel):
    agent_type: str
    model_id: str
    provider: str
    capabilities: list[str]


class AgentFeatures(BaseModel):
    name: str
    strengths: list[str]
    features: dict[str, bool]


class AgentComparison(BaseModel):
    strands: AgentFeatures
    langchain: AgentFeatures


class ToolInfo(BaseModel):
    name: str
    description: str
    available: bool


class ToolsResponse(BaseModel):
    agent_type: str
    tools: list[ToolInfo]
    total_count: int


# ===========================================
# AgentCore必須エンドポイント
# ===========================================

@app.post("/invocations", response_model=InvocationResponse)
async def invoke_agent(request: InvocationRequest):
    """エージェント呼び出しエンドポイント (AgentCore必須)"""
    try:
        user_message = request.input.prompt
        
        if not user_message:
            raise HTTPException(
                status_code=400,
                detail="No prompt found in input.",
            )
        
        logger.info(f"Processing invocation: {user_message[:100]}...")
        
        result = strands_agent(user_message)
        
        response_text = ""
        if hasattr(result, "message"):
            msg = result.message
            if hasattr(msg, "content") and msg.content:
                for content_item in msg.content:
                    if hasattr(content_item, "text"):
                        response_text += content_item.text
                    elif isinstance(content_item, dict) and "text" in content_item:
                        response_text += content_item["text"]
            elif isinstance(msg, str):
                response_text = msg
        else:
            response_text = str(result)
        
        return InvocationResponse(
            output=InvocationOutput(
                message=InvocationMessage(
                    role="assistant",
                    content=[MessageContent(text=response_text)],
                ),
                timestamp=datetime.utcnow().isoformat(),
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Agent processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ping")
async def ping():
    """ヘルスチェック (AgentCore必須)"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# ===========================================
# Health API
# ===========================================

@app.get("/health")
async def health():
    """ヘルスチェック（ダッシュボード用）"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "agent_type": "strands",
        "model_id": MODEL_ID,
    }


# ===========================================
# Sessions API
# ===========================================

@app.post("/sessions", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest):
    """セッション作成"""
    session_id = str(uuid.uuid4())
    agent_id = request.agent_id or "strands-agent"
    created_at = datetime.utcnow().isoformat()
    
    sessions[session_id] = {
        "session_id": session_id,
        "agent_id": agent_id,
        "user_id": request.user_id,
        "state": "active",
        "created_at": created_at,
        "messages": [],
    }
    
    logger.info(f"Session created: {session_id}")
    
    return CreateSessionResponse(
        session_id=session_id,
        agent_id=agent_id,
        created_at=created_at,
    )


@app.get("/sessions/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str):
    """セッション取得"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    return SessionInfo(
        session_id=session["session_id"],
        agent_id=session["agent_id"],
        state=session["state"],
        created_at=session["created_at"],
        message_count=len(session["messages"]),
    )


@app.get("/sessions/{session_id}/messages", response_model=MessagesResponse)
async def get_messages(session_id: str, limit: int = 50, offset: int = 0):
    """セッションのメッセージ取得"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = sessions[session_id]["messages"]
    return MessagesResponse(
        messages=messages[offset:offset + limit],
        total_count=len(messages),
    )


@app.post("/sessions/{session_id}/messages", response_model=SendMessageResponse)
async def send_message(session_id: str, request: SendMessageRequest):
    """メッセージ送信 & AI応答"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    start_time = time.time()
    
    # ユーザーメッセージを保存
    user_msg_id = str(uuid.uuid4())
    sessions[session_id]["messages"].append(SessionMessage(
        id=user_msg_id,
        role="user",
        content=request.instruction,
        created_at=datetime.utcnow().isoformat(),
    ))
    
    try:
        # Strands Agentで応答生成
        logger.info(f"Processing message in session {session_id}: {request.instruction[:100]}...")
        result = strands_agent(request.instruction)
        
        # レスポンス抽出
        response_text = ""
        if hasattr(result, "message"):
            msg = result.message
            if hasattr(msg, "content") and msg.content:
                for content_item in msg.content:
                    if hasattr(content_item, "text"):
                        response_text += content_item.text
                    elif isinstance(content_item, dict) and "text" in content_item:
                        response_text += content_item["text"]
            elif isinstance(msg, str):
                response_text = msg
        else:
            response_text = str(result)
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        # アシスタントメッセージを保存
        assistant_msg_id = str(uuid.uuid4())
        sessions[session_id]["messages"].append(SessionMessage(
            id=assistant_msg_id,
            role="assistant",
            content=response_text,
            created_at=datetime.utcnow().isoformat(),
        ))
        
        logger.info(f"Response generated in {latency_ms}ms")
        
        return SendMessageResponse(
            response_id=assistant_msg_id,
            content=response_text,
            tool_calls=None,
            latency_ms=latency_ms,
            metadata={
                "model_id": MODEL_ID,
                "provider": "strands",
            },
        )
        
    except Exception as e:
        logger.exception(f"Message processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/sessions/{session_id}")
async def end_session(session_id: str):
    """セッション終了"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    sessions[session_id]["state"] = "ended"
    logger.info(f"Session ended: {session_id}")
    
    return {"status": "ended", "session_id": session_id}


# ===========================================
# Agents API
# ===========================================

@app.get("/agents/info", response_model=AgentInfo)
async def get_agent_info():
    """エージェント情報"""
    return AgentInfo(
        agent_type="strands",
        model_id=MODEL_ID,
        provider="AWS Bedrock AgentCore",
        capabilities=[
            "conversation",
            "tool_use",
            "memory",
            "streaming",
        ],
    )


@app.get("/agents/comparison", response_model=AgentComparison)
async def get_agent_comparison():
    """エージェント比較（Strands vs LangChain）"""
    return AgentComparison(
        strands=AgentFeatures(
            name="AWS Strands Agents",
            strengths=[
                "AWS Bedrockネイティブ統合",
                "AgentCore Memory/Identity連携",
                "サーバーレス実行",
                "エンタープライズセキュリティ",
            ],
            features={
                "bedrock_native": True,
                "memory_api": True,
                "serverless": True,
                "multi_provider": False,
                "open_source": True,
            },
        ),
        langchain=AgentFeatures(
            name="LangChain + LangGraph",
            strengths=[
                "豊富なエコシステム",
                "マルチプロバイダー対応",
                "柔軟なワークフロー",
                "コミュニティサポート",
            ],
            features={
                "bedrock_native": False,
                "memory_api": False,
                "serverless": False,
                "multi_provider": True,
                "open_source": True,
            },
        ),
    )


@app.get("/agents/tools", response_model=ToolsResponse)
async def get_agent_tools():
    """利用可能ツール"""
    return ToolsResponse(
        agent_type="strands",
        tools=[
            ToolInfo(name="get_current_weather", description="現在の天気を取得", available=True),
            ToolInfo(name="search_documents", description="ドキュメント検索", available=True),
            ToolInfo(name="calculate", description="数式計算", available=True),
            ToolInfo(name="create_task", description="タスク作成", available=True),
            ToolInfo(name="fetch_url", description="URL取得", available=True),
        ],
        total_count=5,
    )


# ===========================================
# Root
# ===========================================

@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "service": "AgentCore Runtime Agent",
        "model": MODEL_ID,
        "region": AWS_REGION,
        "status": "running",
        "endpoints": [
            "/health",
            "/sessions",
            "/agents/info",
            "/agents/comparison",
            "/agents/tools",
            "/invocations",
            "/ping",
        ],
    }


# ===========================================
# Main
# ===========================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
