"""Strands Agents Tools

AgentCore/Strands用のツール定義。
MCPサーバー連携やカスタムツールの実装。
"""

from typing import Any

import httpx
from strands import tool


@tool
def get_current_weather(location: str, unit: str = "celsius") -> dict[str, Any]:
    """指定された場所の現在の天気を取得する

    Args:
        location: 都市名（例: "Tokyo", "New York"）
        unit: 温度単位（"celsius" または "fahrenheit"）

    Returns:
        天気情報を含む辞書
    """
    # デモ用のモックレスポンス
    # 実際のプロダクションではWeather APIを呼び出す
    weather_data = {
        "Tokyo": {"temp": 22, "condition": "Sunny", "humidity": 65},
        "New York": {"temp": 18, "condition": "Cloudy", "humidity": 70},
        "London": {"temp": 15, "condition": "Rainy", "humidity": 85},
    }

    data = weather_data.get(location, {"temp": 20, "condition": "Unknown", "humidity": 50})

    if unit == "fahrenheit":
        data["temp"] = data["temp"] * 9 / 5 + 32

    return {
        "location": location,
        "temperature": data["temp"],
        "unit": unit,
        "condition": data["condition"],
        "humidity": data["humidity"],
    }


@tool
def search_documents(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """ドキュメントを検索する

    Args:
        query: 検索クエリ
        max_results: 最大結果数

    Returns:
        検索結果のリスト
    """
    # デモ用のモックレスポンス
    # 実際のプロダクションではベクトルDBやElasticsearchを使用
    mock_results = [
        {
            "id": "doc-001",
            "title": f"Document about {query}",
            "snippet": f"This document contains information about {query}...",
            "relevance_score": 0.95,
        },
        {
            "id": "doc-002",
            "title": f"Related to {query}",
            "snippet": f"A related topic discussing {query} in detail...",
            "relevance_score": 0.87,
        },
    ]
    return mock_results[:max_results]


@tool
def calculate(expression: str) -> dict[str, Any]:
    """数式を計算する

    Args:
        expression: 計算式（例: "2 + 2 * 3"）

    Returns:
        計算結果
    """
    try:
        # 安全な計算のため、許可された文字のみ使用
        allowed_chars = set("0123456789+-*/().^ ")
        if not all(c in allowed_chars for c in expression):
            return {"error": "Invalid characters in expression"}

        # ^をべき乗に変換
        expr = expression.replace("^", "**")
        result = eval(expr)

        return {
            "expression": expression,
            "result": result,
            "success": True,
        }
    except Exception as e:
        return {
            "expression": expression,
            "error": str(e),
            "success": False,
        }


@tool
def create_task(title: str, description: str, priority: str = "medium") -> dict[str, Any]:
    """タスクを作成する

    Args:
        title: タスクのタイトル
        description: タスクの説明
        priority: 優先度（"low", "medium", "high"）

    Returns:
        作成されたタスク情報
    """
    from datetime import datetime

    from ulid import ULID

    task_id = str(ULID())
    return {
        "task_id": task_id,
        "title": title,
        "description": description,
        "priority": priority,
        "status": "created",
        "created_at": datetime.utcnow().isoformat(),
    }


@tool
async def fetch_url(url: str) -> dict[str, Any]:
    """URLからコンテンツを取得する

    Args:
        url: 取得するURL

    Returns:
        レスポンス情報
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            return {
                "url": url,
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type"),
                "content_length": len(response.content),
                "content_preview": response.text[:500] if response.status_code == 200 else None,
            }
    except Exception as e:
        return {
            "url": url,
            "error": str(e),
        }


# ツールのリスト（エージェントに渡す用）
AVAILABLE_TOOLS = [
    get_current_weather,
    search_documents,
    calculate,
    create_task,
    fetch_url,
]


def get_tool_definitions() -> list[dict[str, Any]]:
    """ツール定義をJSON形式で取得（LangChainとの比較用）"""
    return [
        {
            "name": "get_current_weather",
            "description": "Get current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name"},
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                },
                "required": ["location"],
            },
        },
        {
            "name": "search_documents",
            "description": "Search documents by query",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {"type": "integer", "description": "Maximum results"},
                },
                "required": ["query"],
            },
        },
        {
            "name": "calculate",
            "description": "Calculate a mathematical expression",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Math expression"},
                },
                "required": ["expression"],
            },
        },
        {
            "name": "create_task",
            "description": "Create a new task",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                },
                "required": ["title", "description"],
            },
        },
        {
            "name": "fetch_url",
            "description": "Fetch content from a URL",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch"},
                },
                "required": ["url"],
            },
        },
    ]

