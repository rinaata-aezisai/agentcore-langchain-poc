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
    # 基本フィールド（チャット用）
    prompt: str | None = None
    messages: list[dict[str, Any]] | None = None
    tools: list[dict[str, Any]] | None = None
    # アクションベースルーティング用
    action: str | None = None
    # セッション関連
    session_id: str | None = None
    user_id: str | None = None
    agent_id: str | None = None
    agent_type: str | None = None
    instruction: str | None = None
    limit: int | None = None
    offset: int | None = None
    # ベンチマーク関連
    test_cases: list[str] | None = None
    iterations: int | None = None


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

@app.post("/invocations")
async def invoke_agent(request: InvocationRequest):
    """エージェント呼び出しエンドポイント (AgentCore必須)
    
    アクションベースルーティング:
    - action=None or prompt指定: 通常のチャット
    - action="create_session": セッション作成
    - action="get_session": セッション取得
    - action="send_message": メッセージ送信
    - action="get_messages": メッセージ一覧取得
    - action="end_session": セッション終了
    - action="get_agent_info": エージェント情報
    - action="get_agent_comparison": エージェント比較
    - action="get_agent_tools": ツール一覧
    - action="health_check": ヘルスチェック
    - action="service_*_execute": サービス実行
    """
    try:
        action = request.input.action
        
        # アクションベースルーティング
        if action:
            result = await handle_action(action, request.input)
            return make_invocation_response(json.dumps(result, ensure_ascii=False, default=str))
        
        # 通常のチャット処理
        user_message = request.input.prompt or request.input.instruction
        
        if not user_message:
            raise HTTPException(
                status_code=400,
                detail="No prompt or action found in input.",
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
        
        return make_invocation_response(response_text)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Agent processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def make_invocation_response(text: str) -> dict:
    """InvocationResponse形式のレスポンスを生成"""
    return {
        "output": {
            "message": {
                "role": "assistant",
                "content": [{"text": text}],
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    }


async def handle_action(action: str, input_data: InvocationInput) -> dict:
    """アクションに応じた処理を実行"""
    logger.info(f"Handling action: {action}")
    
    # セッション関連
    if action == "create_session":
        return await _create_session(input_data)
    elif action == "get_session":
        return await _get_session(input_data.session_id)
    elif action == "send_message":
        return await _send_message(input_data)
    elif action == "get_messages":
        return await _get_messages(input_data)
    elif action == "end_session":
        return await _end_session(input_data.session_id)
    
    # エージェント情報
    elif action == "get_agent_info":
        return await _get_agent_info()
    elif action == "get_agent_comparison":
        return await _get_agent_comparison()
    elif action == "get_agent_tools":
        return await _get_agent_tools()
    
    # ヘルスチェック
    elif action == "health_check":
        return {"status": "healthy", "version": "1.0.0", "agent_type": "strands", "model_id": MODEL_ID}
    
    # サービス実行（runtime, memory, etc.）
    elif action.startswith("service_") and action.endswith("_execute"):
        service_name = action.replace("service_", "").replace("_execute", "")
        return await _execute_service(service_name, input_data)
    
    # ベンチマーク
    elif action == "run_benchmark":
        return await _run_benchmark(input_data)
    elif action == "get_benchmark_results":
        return {"results": []}  # TODO: 実装
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")


async def _create_session(input_data: InvocationInput) -> dict:
    """セッション作成"""
    session_id = str(uuid.uuid4())
    agent_id = input_data.agent_id or "strands-agent"
    created_at = datetime.utcnow().isoformat()
    
    sessions[session_id] = {
        "session_id": session_id,
        "agent_id": agent_id,
        "user_id": input_data.user_id,
        "agent_type": input_data.agent_type or "strands",
        "state": "active",
        "created_at": created_at,
        "messages": [],
    }
    
    logger.info(f"Session created: {session_id}")
    
    return {
        "session_id": session_id,
        "agent_id": agent_id,
        "agent_type": input_data.agent_type or "strands",
        "created_at": created_at,
    }


async def _get_session(session_id: str | None) -> dict:
    """セッション取得"""
    if not session_id or session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    return {
        "session_id": session["session_id"],
        "agent_id": session["agent_id"],
        "agent_type": session.get("agent_type", "strands"),
        "state": session["state"],
        "created_at": session["created_at"],
        "message_count": len(session["messages"]),
    }


async def _send_message(input_data: InvocationInput) -> dict:
    """メッセージ送信"""
    session_id = input_data.session_id
    instruction = input_data.instruction or input_data.prompt
    
    if not session_id or session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not instruction:
        raise HTTPException(status_code=400, detail="No instruction provided")
    
    start_time = time.time()
    
    # ユーザーメッセージを保存
    user_msg_id = str(uuid.uuid4())
    sessions[session_id]["messages"].append({
        "id": user_msg_id,
        "role": "user",
        "content": instruction,
        "created_at": datetime.utcnow().isoformat(),
    })
    
    # Strands Agentで応答生成
    logger.info(f"Processing message in session {session_id}: {instruction[:100]}...")
    result = strands_agent(instruction)
    
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
    sessions[session_id]["messages"].append({
        "id": assistant_msg_id,
        "role": "assistant",
        "content": response_text,
        "created_at": datetime.utcnow().isoformat(),
    })
    
    logger.info(f"Response generated in {latency_ms}ms")
    
    return {
        "response_id": assistant_msg_id,
        "content": response_text,
        "tool_calls": None,
        "latency_ms": latency_ms,
        "metadata": {
            "model_id": MODEL_ID,
            "provider": "strands",
        },
    }


async def _get_messages(input_data: InvocationInput) -> dict:
    """メッセージ一覧取得"""
    session_id = input_data.session_id
    limit = input_data.limit or 50
    offset = input_data.offset or 0
    
    if not session_id or session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = sessions[session_id]["messages"]
    return {
        "messages": messages[offset:offset + limit],
        "total_count": len(messages),
    }


async def _end_session(session_id: str | None) -> dict:
    """セッション終了"""
    if not session_id or session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    sessions[session_id]["state"] = "ended"
    logger.info(f"Session ended: {session_id}")
    
    return {"status": "ended", "session_id": session_id}


async def _get_agent_info() -> dict:
    """エージェント情報"""
    return {
        "agent_type": "strands",
        "model_id": MODEL_ID,
        "provider": "AWS Bedrock AgentCore",
        "capabilities": ["conversation", "tool_use", "memory", "streaming"],
    }


async def _get_agent_comparison() -> dict:
    """エージェント比較"""
    return {
        "strands": {
            "name": "AWS Strands Agents",
            "strengths": [
                "AWS Bedrockネイティブ統合",
                "AgentCore Memory/Identity連携",
                "サーバーレス実行",
                "エンタープライズセキュリティ",
            ],
            "features": {
                "bedrock_native": True,
                "memory_api": True,
                "serverless": True,
                "multi_provider": False,
                "open_source": True,
            },
        },
        "langchain": {
            "name": "LangChain + LangGraph",
            "strengths": [
                "豊富なエコシステム",
                "マルチプロバイダー対応",
                "柔軟なワークフロー",
                "コミュニティサポート",
            ],
            "features": {
                "bedrock_native": False,
                "memory_api": False,
                "serverless": False,
                "multi_provider": True,
                "open_source": True,
            },
        },
    }


async def _get_agent_tools() -> dict:
    """ツール一覧"""
    return {
        "agent_type": "strands",
        "tools": [
            {"name": "get_current_weather", "description": "現在の天気を取得", "available": True},
            {"name": "search_documents", "description": "ドキュメント検索", "available": True},
            {"name": "calculate", "description": "数式計算", "available": True},
            {"name": "create_task", "description": "タスク作成", "available": True},
            {"name": "fetch_url", "description": "URL取得", "available": True},
        ],
        "total_count": 5,
    }


async def _execute_service(service_name: str, input_data: InvocationInput) -> dict:
    """サービス実行"""
    instruction = input_data.instruction or input_data.prompt
    
    if not instruction:
        raise HTTPException(status_code=400, detail="No instruction provided")
    
    start_time = time.time()
    
    logger.info(f"Executing service '{service_name}': {instruction[:100]}...")
    
    # Strands Agentで処理
    result = strands_agent(instruction)
    
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
    
    return {
        "response_id": str(uuid.uuid4()),
        "content": response_text,
        "tool_calls": None,
        "latency_ms": latency_ms,
        "metadata": {
            "service": service_name,
            "model_id": MODEL_ID,
            "provider": "strands",
        },
    }


async def _run_benchmark(input_data: InvocationInput) -> dict:
    """ベンチマーク実行"""
    test_cases = input_data.test_cases or []
    iterations = input_data.iterations or 1
    
    results = []
    for test_case in test_cases:
        start_time = time.time()
        try:
            result = strands_agent(test_case)
            response_text = str(result)
            success = True
        except Exception as e:
            response_text = str(e)
            success = False
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        results.append({
            "test_name": test_case[:50],
            "strands_latency_ms": latency_ms,
            "langchain_latency_ms": 0,  # LangChain未実装
            "strands_success": success,
            "langchain_success": False,
            "strands_response": response_text[:500],
            "langchain_response": None,
        })
    
    return {"results": results}


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
