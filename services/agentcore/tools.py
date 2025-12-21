"""Strands Agents Tools - AgentCore Service

AgentCore/Strands用のツール定義。
比較検証のため、LangChain側と同じツールセットを実装。
"""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

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
    weather_data = {
        "Tokyo": {"temp": 22, "condition": "Sunny", "humidity": 65},
        "New York": {"temp": 18, "condition": "Cloudy", "humidity": 70},
        "London": {"temp": 15, "condition": "Rainy", "humidity": 85},
        "San Francisco": {"temp": 20, "condition": "Foggy", "humidity": 75},
        "Paris": {"temp": 17, "condition": "Partly Cloudy", "humidity": 60},
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
        "provider": "strands-agents",
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
    mock_results = [
        {
            "id": "doc-001",
            "title": f"Document about {query}",
            "snippet": f"This document contains information about {query}...",
            "relevance_score": 0.95,
            "source": "strands-agents",
        },
        {
            "id": "doc-002",
            "title": f"Related to {query}",
            "snippet": f"A related topic discussing {query} in detail...",
            "relevance_score": 0.87,
            "source": "strands-agents",
        },
        {
            "id": "doc-003",
            "title": f"Advanced {query} guide",
            "snippet": f"An advanced guide covering {query} comprehensively...",
            "relevance_score": 0.82,
            "source": "strands-agents",
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
        allowed_chars = set("0123456789+-*/().^ ")
        if not all(c in allowed_chars for c in expression):
            return {"error": "Invalid characters in expression", "success": False}

        expr = expression.replace("^", "**")
        result = eval(expr)

        return {
            "expression": expression,
            "result": result,
            "success": True,
            "provider": "strands-agents",
        }
    except Exception as e:
        return {
            "expression": expression,
            "error": str(e),
            "success": False,
            "provider": "strands-agents",
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
        "provider": "strands-agents",
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
                "provider": "strands-agents",
            }
    except Exception as e:
        return {
            "url": url,
            "error": str(e),
            "provider": "strands-agents",
        }


@tool
def get_current_time(timezone: str = "UTC") -> dict[str, Any]:
    """現在時刻を取得する

    Args:
        timezone: タイムゾーン（例: "UTC", "Asia/Tokyo"）

    Returns:
        現在時刻情報
    """
    try:
        tz = ZoneInfo(timezone)
        now = datetime.now(tz)
        return {
            "timezone": timezone,
            "datetime": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "day_of_week": now.strftime("%A"),
            "provider": "strands-agents",
        }
    except Exception as e:
        return {
            "error": f"Invalid timezone: {timezone}",
            "details": str(e),
            "provider": "strands-agents",
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
        "provider": "strands-agents",
    }

    if analysis_type == "summary":
        result["summary"] = text[:100] + "..." if len(text) > 100 else text
    elif analysis_type == "sentiment":
        positive_words = ["good", "great", "excellent", "happy", "love", "wonderful", "amazing"]
        negative_words = ["bad", "terrible", "sad", "hate", "awful", "horrible", "worst"]
        text_lower = text.lower()
        pos_count = sum(1 for w in positive_words if w in text_lower)
        neg_count = sum(1 for w in negative_words if w in text_lower)
        if pos_count > neg_count:
            result["sentiment"] = "positive"
            result["confidence"] = min(0.5 + pos_count * 0.1, 1.0)
        elif neg_count > pos_count:
            result["sentiment"] = "negative"
            result["confidence"] = min(0.5 + neg_count * 0.1, 1.0)
        else:
            result["sentiment"] = "neutral"
            result["confidence"] = 0.5
    elif analysis_type == "keywords":
        words = text.split()
        keywords = list(set(w.lower() for w in words if len(w) > 5))[:10]
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


def get_tools() -> list:
    """ツールリストを取得"""
    return AVAILABLE_TOOLS

