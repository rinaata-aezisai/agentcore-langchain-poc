"""Lambda Handler - LangChain Service

AWS Lambda Container Image用のハンドラー。
Lambda Function URL または API Gateway から呼び出される。
AgentCore Runtimeへのプロキシ機能も提供。
"""

import base64
import json
import logging
import os
from typing import Any

import boto3

from agent import ChatRequest, chat, health, info

# ロギング設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AgentCore client
bedrock_agentcore_client = None


def get_agentcore_client():
    """AgentCore クライアントを取得（遅延初期化）"""
    global bedrock_agentcore_client
    if bedrock_agentcore_client is None:
        # Lambda環境ではAWS_REGIONが自動設定、BEDROCK_REGIONも使用可能
        region = os.getenv("BEDROCK_REGION") or os.getenv("AWS_REGION", "us-east-1")
        bedrock_agentcore_client = boto3.client(
            "bedrock-agentcore",
            region_name=region,
        )
    return bedrock_agentcore_client


def invoke_agentcore(
    runtime_arn: str,
    instruction: str,
    endpoint_id: str | None = None,
) -> dict[str, Any]:
    """AgentCore Runtime を呼び出す"""
    import time

    start_time = time.time()

    client = get_agentcore_client()

    # ペイロード作成 - CLIと同じ形式
    payload = {"input": {"prompt": instruction}}
    payload_json = json.dumps(payload)
    # SDK は bytes を期待する場合がある
    payload_bytes = payload_json.encode("utf-8")

    logger.info(f"Invoking AgentCore: {runtime_arn}")
    logger.info(f"Payload (raw): {payload_json}")

    try:
        # SDK呼び出し - bytes形式で渡す
        response = client.invoke_agent_runtime(
            agentRuntimeArn=runtime_arn,
            payload=payload_bytes,
        )

        logger.info(f"Response keys: {list(response.keys())}")

        # SDK レスポンスからデータを読み取り
        # SDK は 'response' キーを使用（CLI は outfile に body を書き込む）
        body = response.get("response") or response.get("body")
        if body is None:
            # response全体からメタデータを除いて探す
            for key in ["output", "result", "data"]:
                if key in response:
                    body = response[key]
                    break

        if body is None:
            logger.error(f"Full response: {response}")
            raise ValueError(f"No body in AgentCore response. Keys: {list(response.keys())}")

        # StreamingBody の場合は read() でバイトを取得
        if hasattr(body, "read"):
            body_bytes = body.read()
            output_data = json.loads(body_bytes.decode("utf-8"))
        elif isinstance(body, bytes):
            output_data = json.loads(body.decode("utf-8"))
        elif isinstance(body, str):
            output_data = json.loads(body)
        elif isinstance(body, dict):
            output_data = body
        else:
            output_data = {"raw": str(body)}

        latency_ms = int((time.time() - start_time) * 1000)

        # メタデータに latency を追加
        if "metadata" not in output_data:
            output_data["metadata"] = {}
        output_data["metadata"]["latency_ms"] = latency_ms
        output_data["metadata"]["runtime_arn"] = runtime_arn

        logger.info(f"AgentCore response received in {latency_ms}ms")

        return output_data

    except Exception as e:
        logger.error(f"AgentCore SDK call failed: {type(e).__name__}: {e}")
        raise


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda Handler

    Lambda Function URL からのリクエストを処理。

    エンドポイント:
    - POST /api/v1/chat: チャット実行
    - POST /api/v1/chat/tools: ツール付きチャット
    - GET /api/v1/health: ヘルスチェック
    - GET /api/v1/info: サービス情報
    """
    try:
        # リクエスト情報を抽出
        http_method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
        path = event.get("rawPath", "/")

        logger.info(f"Request: {http_method} {path}")

        # CORS headers
        headers = {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        }

        # OPTIONS (CORS preflight)
        if http_method == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": headers,
                "body": "",
            }

        # ルーティング
        if path == "/api/v1/health" and http_method == "GET":
            response = health()
            return {
                "statusCode": 200,
                "headers": headers,
                "body": response.model_dump_json(),
            }

        elif path == "/api/v1/info" and http_method == "GET":
            response = info()
            return {
                "statusCode": 200,
                "headers": headers,
                "body": response.model_dump_json(),
            }

        elif path == "/api/v1/chat" and http_method == "POST":
            body = json.loads(event.get("body", "{}"))

            # AgentCoreへのプロキシ
            target_service = body.get("target_service")
            if target_service == "agentcore":
                runtime_arn = body.get(
                    "agentcore_runtime_arn",
                    "arn:aws:bedrock-agentcore:us-east-1:226484346947:runtime/agentcore_strands_dev-sSCXyh2bVa",
                )
                endpoint_id = body.get("agentcore_endpoint_id", "agentcore_strands_dev_endpoint")

                try:
                    agentcore_response = invoke_agentcore(
                        runtime_arn=runtime_arn,
                        instruction=body.get("instruction", ""),
                        endpoint_id=endpoint_id,
                    )

                    # AgentCoreレスポンスをフォーマット
                    output = agentcore_response.get("output", {})
                    message = output.get("message", {})
                    content_list = message.get("content", [])
                    content_text = ""
                    for item in content_list:
                        if isinstance(item, dict) and "text" in item:
                            content_text += item["text"]

                    formatted_response = {
                        "response_id": agentcore_response.get("metadata", {}).get("request_id", "agentcore-response"),
                        "content": content_text,
                        "tool_calls": output.get("tool_calls"),
                        "latency_ms": agentcore_response.get("metadata", {}).get("latency_ms", 0),
                        "metadata": {
                            "service": "agentcore",
                            "framework": "strands-agents",
                            "model_id": agentcore_response.get("metadata", {}).get("model_id", "unknown"),
                            "region": os.getenv("AWS_REGION", "us-east-1"),
                        },
                    }

                    return {
                        "statusCode": 200,
                        "headers": headers,
                        "body": json.dumps(formatted_response),
                    }
                except Exception as e:
                    logger.exception(f"AgentCore invoke error: {e}")
                    return {
                        "statusCode": 500,
                        "headers": headers,
                        "body": json.dumps({"error": "AgentCore Error", "details": str(e)}),
                    }

            # 通常のLangChain処理
            request = ChatRequest(
                instruction=body.get("instruction", ""),
                session_id=body.get("session_id"),
                use_tools=body.get("use_tools", False),
            )
            response = chat(request)
            return {
                "statusCode": 200,
                "headers": headers,
                "body": response.model_dump_json(),
            }

        elif path == "/api/v1/chat/tools" and http_method == "POST":
            body = json.loads(event.get("body", "{}"))
            request = ChatRequest(
                instruction=body.get("instruction", ""),
                session_id=body.get("session_id"),
                use_tools=True,  # ツール使用を強制
            )
            response = chat(request)
            return {
                "statusCode": 200,
                "headers": headers,
                "body": response.model_dump_json(),
            }

        # ルート
        elif path == "/" and http_method == "GET":
            return {
                "statusCode": 200,
                "headers": headers,
                "body": json.dumps(
                    {
                        "service": "LangChain Service",
                        "version": "1.0.0",
                        "endpoints": [
                            "/api/v1/chat",
                            "/api/v1/chat/tools",
                            "/api/v1/health",
                            "/api/v1/info",
                        ],
                    }
                ),
            }

        # 404 Not Found
        else:
            return {
                "statusCode": 404,
                "headers": headers,
                "body": json.dumps({"error": "Not Found", "path": path}),
            }

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Invalid JSON", "details": str(e)}),
        }
    except Exception as e:
        logger.exception(f"Handler error: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Internal Server Error", "details": str(e)}),
        }


# ローカルテスト用
if __name__ == "__main__":
    # テストイベント
    test_event = {
        "requestContext": {"http": {"method": "POST"}},
        "rawPath": "/api/v1/chat",
        "body": json.dumps({"instruction": "東京の天気を教えて", "use_tools": True}),
    }

    result = lambda_handler(test_event, None)
    print(json.dumps(json.loads(result["body"]), indent=2, ensure_ascii=False))

