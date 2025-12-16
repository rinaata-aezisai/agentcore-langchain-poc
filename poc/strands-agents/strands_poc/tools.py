"""Strands Agents Tools - 2025年12月版

AgentCore/Strands用のツール定義。
2025年12月の新機能:
- MCP (Model Context Protocol) 対応
- Gateway統合
- 非同期ツールのネイティブサポート
"""

from datetime import datetime
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
        "San Francisco": {"temp": 20, "condition": "Foggy", "humidity": 75},
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
        "timestamp": datetime.utcnow().isoformat(),
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
    """URLからコンテンツを取得する（非同期）

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


@tool
def get_current_time(timezone: str = "UTC") -> dict[str, Any]:
    """現在時刻を取得する

    Args:
        timezone: タイムゾーン（例: "UTC", "Asia/Tokyo"）

    Returns:
        現在時刻情報
    """
    from zoneinfo import ZoneInfo

    try:
        tz = ZoneInfo(timezone)
        now = datetime.now(tz)
        return {
            "timezone": timezone,
            "datetime": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "day_of_week": now.strftime("%A"),
        }
    except Exception as e:
        return {
            "error": f"Invalid timezone: {timezone}",
            "details": str(e),
        }


@tool
def analyze_text(text: str, analysis_type: str = "summary") -> dict[str, Any]:
    """テキストを分析する

    Args:
        text: 分析するテキスト
        analysis_type: 分析タイプ（"summary", "sentiment", "keywords"）

    Returns:
        分析結果
    """
    word_count = len(text.split())
    char_count = len(text)

    result: dict[str, Any] = {
        "word_count": word_count,
        "char_count": char_count,
        "analysis_type": analysis_type,
    }

    if analysis_type == "summary":
        # 簡易要約（最初の100文字）
        result["summary"] = text[:100] + "..." if len(text) > 100 else text
    elif analysis_type == "sentiment":
        # 簡易感情分析（モック）
        positive_words = ["good", "great", "excellent", "happy", "love"]
        negative_words = ["bad", "terrible", "sad", "hate", "awful"]
        text_lower = text.lower()
        pos_count = sum(1 for w in positive_words if w in text_lower)
        neg_count = sum(1 for w in negative_words if w in text_lower)
        if pos_count > neg_count:
            result["sentiment"] = "positive"
        elif neg_count > pos_count:
            result["sentiment"] = "negative"
        else:
            result["sentiment"] = "neutral"
    elif analysis_type == "keywords":
        # 簡易キーワード抽出（長い単語を抽出）
        words = text.split()
        keywords = [w for w in words if len(w) > 5][:10]
        result["keywords"] = keywords

    return result


# ツールのリスト（エージェントに渡す用）
AVAILABLE_TOOLS = [
    get_current_weather,
    search_documents,
    calculate,
    create_task,
    fetch_url,
    get_current_time,
    analyze_text,
]


def get_tool_definitions() -> list[dict[str, Any]]:
    """ツール定義をJSON形式で取得（LangChainとの比較用）

    MCP (Model Context Protocol) 形式に準拠。
    """
    return [
        {
            "name": "get_current_weather",
            "description": "Get current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name"},
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "default": "celsius",
                    },
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
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results",
                        "default": 5,
                    },
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
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "default": "medium",
                    },
                },
                "required": ["title", "description"],
            },
        },
        {
            "name": "fetch_url",
            "description": "Fetch content from a URL (async)",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch"},
                },
                "required": ["url"],
            },
        },
        {
            "name": "get_current_time",
            "description": "Get current time in a specific timezone",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "Timezone (e.g., UTC, Asia/Tokyo)",
                        "default": "UTC",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "analyze_text",
            "description": "Analyze text (summary, sentiment, or keywords)",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to analyze"},
                    "analysis_type": {
                        "type": "string",
                        "enum": ["summary", "sentiment", "keywords"],
                        "default": "summary",
                    },
                },
                "required": ["text"],
            },
        },
    ]
