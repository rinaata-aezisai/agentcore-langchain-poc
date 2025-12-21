# AgentCore Service - Strands Agents

AWS Bedrock AgentCore Runtime で動作する Strands Agents 実装。

## 概要

- **フレームワーク**: Strands Agents (AWS公式)
- **デプロイ先**: AgentCore Runtime (ECR経由)
- **認証**: IAM SigV4

## ディレクトリ構成

```
services/agentcore/
├── agent.py          # FastAPI + Strands Agent 実装
├── tools.py          # ツール定義
├── Dockerfile        # AgentCore Runtime 用
├── pyproject.toml    # 依存関係
└── README.md
```

## API エンドポイント

### AgentCore 必須エンドポイント

| Method | Path | Description |
|--------|------|-------------|
| POST | `/invocations` | エージェント呼び出し |
| GET | `/ping` | ヘルスチェック |

### 比較検証用 API (LangChain と統一)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/chat` | チャット実行 |
| POST | `/api/v1/chat/tools` | ツール付きチャット |
| GET | `/api/v1/health` | ヘルスチェック |
| GET | `/api/v1/info` | サービス情報 |

## リクエスト/レスポンス形式

### Chat Request

```json
{
  "instruction": "東京の天気を教えて",
  "session_id": "optional-session-id",
  "use_tools": true
}
```

### Chat Response

```json
{
  "response_id": "uuid",
  "content": "東京の現在の天気は晴れで、気温は22度です。",
  "tool_calls": [
    {
      "tool_name": "get_current_weather",
      "tool_input": {"location": "Tokyo"},
      "tool_output": {"temperature": 22, "condition": "Sunny"}
    }
  ],
  "latency_ms": 1234,
  "metadata": {
    "service": "agentcore",
    "framework": "strands-agents",
    "model_id": "us.anthropic.claude-sonnet-4-20250514-v1:0"
  }
}
```

## ローカル実行

```bash
# 依存関係インストール
pip install -e .

# サーバー起動
python agent.py
# または
uvicorn agent:app --reload --port 8080

# テスト
curl http://localhost:8080/api/v1/health
curl -X POST http://localhost:8080/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"instruction": "Hello!", "use_tools": false}'
```

## Docker ビルド

```bash
# ビルド
docker build -t agentcore-service .

# ローカル実行
docker run -p 8080:8080 \
  -e AWS_REGION=us-east-1 \
  -e BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0 \
  agentcore-service
```

## AgentCore Runtime デプロイ

```bash
# ECR にプッシュ
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
docker tag agentcore-service:latest <account>.dkr.ecr.us-east-1.amazonaws.com/agentcore-service:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/agentcore-service:latest

# AgentCore Runtime に登録
# (AWSコンソール or CDK で設定)
```

## 環境変数

| 変数 | 説明 | デフォルト |
|------|------|-----------|
| `BEDROCK_MODEL_ID` | Bedrock モデル ID | `us.anthropic.claude-sonnet-4-20250514-v1:0` |
| `AWS_REGION` | AWS リージョン | `us-east-1` |
| `ENABLE_CACHING` | キャッシング有効化 | `true` |
| `PORT` | サーバーポート | `8080` |

## Strands Agents の特徴

- **Bedrock ネイティブ**: AWS Bedrock と直接統合
- **自動ツールループ**: ツール呼び出しを自動的にループ
- **メモリ API**: AgentCore Memory との統合
- **キャッシング**: プロンプト/ツールキャッシング対応

