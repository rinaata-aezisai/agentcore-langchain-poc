"""AgentCore Runtime Agent - FastAPI + Strands Agents

AWS公式ドキュメントに基づく実装:
https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/getting-started-custom.html

必須エンドポイント:
- POST /invocations: エージェント呼び出し
- GET /ping: ヘルスチェック

AgentCore Runtimeにデプロイ後、invoke_agent_runtime()で呼び出し可能。
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
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
    description="Strands Agents on AgentCore Runtime",
    version="1.0.0",
)

# ===========================================
# Strands Agent Setup
# ===========================================

# モデル設定
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
# Request/Response Models
# ===========================================

class InvocationInput(BaseModel):
    """入力ペイロード"""
    prompt: str
    messages: list[dict[str, Any]] | None = None
    tools: list[dict[str, Any]] | None = None


class InvocationRequest(BaseModel):
    """AgentCore Runtimeからのリクエスト"""
    input: InvocationInput


class MessageContent(BaseModel):
    """メッセージコンテンツ"""
    text: str


class Message(BaseModel):
    """レスポンスメッセージ"""
    role: str = "assistant"
    content: list[MessageContent]


class InvocationOutput(BaseModel):
    """出力ペイロード"""
    message: Message
    timestamp: str


class InvocationResponse(BaseModel):
    """AgentCore Runtimeへのレスポンス"""
    output: InvocationOutput


# ===========================================
# Endpoints
# ===========================================

@app.post("/invocations", response_model=InvocationResponse)
async def invoke_agent(request: InvocationRequest):
    """エージェント呼び出しエンドポイント (必須)
    
    AgentCore Runtimeからのリクエストを処理し、
    Strands Agentを使用してレスポンスを生成。
    """
    try:
        user_message = request.input.prompt
        
        if not user_message:
            raise HTTPException(
                status_code=400,
                detail="No prompt found in input. Please provide a 'prompt' key.",
            )
        
        logger.info(f"Processing request: {user_message[:100]}...")
        
        # 会話履歴がある場合は考慮（将来の拡張用）
        messages = request.input.messages or []
        
        # Strands Agentを呼び出し
        result = strands_agent(user_message)
        
        # レスポンス構築
        response_text = ""
        if hasattr(result, "message"):
            # result.messageからテキストを抽出
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
        
        logger.info(f"Response generated: {response_text[:100]}...")
        
        return InvocationResponse(
            output=InvocationOutput(
                message=Message(
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
        raise HTTPException(
            status_code=500,
            detail=f"Agent processing failed: {str(e)}",
        )


@app.get("/ping")
async def ping():
    """ヘルスチェックエンドポイント (必須)
    
    AgentCore Runtimeがコンテナの健全性を確認するために使用。
    """
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/")
async def root():
    """ルートエンドポイント（情報表示用）"""
    return {
        "service": "AgentCore Runtime Agent",
        "model": MODEL_ID,
        "region": AWS_REGION,
        "status": "running",
    }


# ===========================================
# Main Entry Point
# ===========================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
