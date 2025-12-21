"""Lambda Handler - LangChain Service

AWS Lambda Container Image用のハンドラー。
Lambda Function URL または API Gateway から呼び出される。
"""

import json
import logging
from typing import Any

from agent import ChatRequest, chat, health, info

# ロギング設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)


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

