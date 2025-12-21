# Services - AgentCore vs LangChain 比較検証

AgentCore (Strands Agents) と LangChain/LangGraph の比較検証用サービス。

## アーキテクチャ

```
Frontend (Amplify + Cognito)
     │
     │ IAM認証 (SigV4)
     │
     ├──▶ AgentCore Service (services/agentcore/)
     │         │
     │         └─ ECR → AgentCore Runtime
     │                  └─ Strands Agent → Bedrock
     │
     └──▶ LangChain Service (services/langchain/)
               │
               └─ ECR → Lambda Container
                        └─ LangChain/LangGraph → Bedrock
```

## 統一 API 仕様

両サービスは同じ API インターフェースを実装:

### POST /api/v1/chat

チャット実行

**Request:**
```json
{
  "instruction": "東京の天気を教えて",
  "session_id": "optional-session-id",
  "use_tools": true
}
```

**Response:**
```json
{
  "response_id": "uuid",
  "content": "応答テキスト",
  "tool_calls": [
    {
      "tool_name": "get_current_weather",
      "tool_input": {"location": "Tokyo"},
      "tool_output": {"temperature": 22}
    }
  ],
  "latency_ms": 1234,
  "metadata": {
    "service": "agentcore|langchain",
    "framework": "strands-agents|langchain + langgraph",
    "model_id": "..."
  }
}
```

### GET /api/v1/health

ヘルスチェック

### GET /api/v1/info

サービス情報

## 実装ツール（同一）

| ツール | 説明 |
|--------|------|
| `get_current_weather` | 天気情報取得 |
| `search_documents` | ドキュメント検索 |
| `calculate` | 数式計算 |
| `create_task` | タスク作成 |
| `fetch_url` | URL取得 |
| `get_current_time` | 現在時刻取得 |
| `analyze_text` | テキスト分析 |

## デプロイ

```bash
# 両サービスをビルド & デプロイ
./scripts/deploy-services.sh dev all

# AgentCore のみ
./scripts/deploy-services.sh dev agentcore

# LangChain のみ
./scripts/deploy-services.sh dev langchain
```

## 比較ポイント

| 観点 | AgentCore (Strands) | LangChain |
|------|---------------------|-----------|
| **ホスティング** | AgentCore Runtime | Lambda Container |
| **メモリ管理** | AgentCore Memory API | 自前実装 / Checkpointing |
| **ツール実行** | 自動ループ | StateGraph + ToolNode |
| **キャッシング** | プロンプト/ツールキャッシング | なし |
| **コスト** | AgentCore課金 | Lambda課金 |
| **スケーリング** | 自動（マネージド） | Lambda自動 |
| **コールドスタート** | なし（常時起動） | あり（5-15秒） |

## ローカル開発

### AgentCore Service

```bash
cd services/agentcore
pip install -e .
uvicorn agent:app --reload --port 8080
```

### LangChain Service

```bash
cd services/langchain
pip install -e .
python handler.py  # ローカルテスト
```

## 環境変数

| 変数 | 説明 | デフォルト |
|------|------|-----------|
| `BEDROCK_MODEL_ID` | Bedrock モデル ID | `us.anthropic.claude-sonnet-4-20250514-v1:0` |
| `AWS_REGION` | AWS リージョン | `us-east-1` |

