# LangChain Service - Lambda Container

AWS Lambda Container Image で動作する LangChain/LangGraph 実装。

## 概要

- **フレームワーク**: LangChain + LangGraph
- **デプロイ先**: Lambda Container Image (Function URL)
- **認証**: IAM (AWS_IAM auth type)

## ディレクトリ構成

```
services/langchain/
├── handler.py        # Lambda ハンドラー
├── agent.py          # LangChain/LangGraph Agent 実装
├── tools.py          # ツール定義
├── Dockerfile        # Lambda Container 用
├── pyproject.toml    # 依存関係
└── README.md
```

## API エンドポイント

### 比較検証用 API (AgentCore と統一)

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
      "tool_input": {"location": "Tokyo"}
    }
  ],
  "latency_ms": 1234,
  "metadata": {
    "service": "langchain",
    "framework": "langchain + langgraph",
    "model_id": "us.anthropic.claude-sonnet-4-20250514-v1:0"
  }
}
```

## ローカル実行

```bash
# 依存関係インストール
pip install -e .

# ローカルテスト
python handler.py
```

## Docker ビルド

```bash
# ビルド
docker build -t langchain-service .

# ローカル実行（Lambda Runtime Interface Emulator使用）
docker run -p 9000:8080 \
  -e AWS_REGION=us-east-1 \
  -e BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0 \
  langchain-service

# テスト
curl -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -d '{"requestContext":{"http":{"method":"POST"}},"rawPath":"/api/v1/chat","body":"{\"instruction\":\"Hello!\"}"}'
```

## Lambda デプロイ

```bash
# ECR にプッシュ
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
docker tag langchain-service:latest <account>.dkr.ecr.us-east-1.amazonaws.com/langchain-service:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/langchain-service:latest

# Lambda 作成（CDK or CLI）
aws lambda create-function \
  --function-name langchain-service \
  --package-type Image \
  --code ImageUri=<account>.dkr.ecr.us-east-1.amazonaws.com/langchain-service:latest \
  --role arn:aws:iam::<account>:role/lambda-bedrock-role \
  --timeout 300 \
  --memory-size 1024

# Function URL 作成
aws lambda create-function-url-config \
  --function-name langchain-service \
  --auth-type AWS_IAM
```

## 環境変数

| 変数 | 説明 | デフォルト |
|------|------|-----------|
| `BEDROCK_MODEL_ID` | Bedrock モデル ID | `us.anthropic.claude-sonnet-4-20250514-v1:0` |
| `AWS_REGION` | AWS リージョン | `us-east-1` |
| `ENABLE_CHECKPOINTING` | Checkpointing 有効化 | `true` |

## LangChain/LangGraph の特徴

- **マルチプロバイダー**: 複数の LLM プロバイダーに対応
- **StateGraph**: 状態管理とワークフロー制御
- **Checkpointing**: 状態の保存・復元
- **条件分岐**: 柔軟なエージェントフロー
- **ToolNode**: ツール実行の自動化

## コスト

Lambda Container の料金:
- **リクエスト課金**: 100万リクエストあたり $0.20
- **実行時間課金**: 1ms あたり $0.0000166667 (1024MB)
- **未使用時**: $0 (ECSと異なり常時起動不要)

PoC/検証用途に最適！

