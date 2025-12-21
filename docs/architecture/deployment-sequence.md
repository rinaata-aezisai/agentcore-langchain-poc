# AgentCore vs LangChain 比較検証 - アーキテクチャ & シーケンス図

## デプロイ状況 (2025-12-22)

### デプロイ済みリソース

| サービス | デプロイ先 | エンドポイント | 認証 |
|---------|----------|---------------|------|
| **LangChain** | Lambda Container | `https://hqtuy24tbjdzbobyg4tzsr2xhe0rjmbx.lambda-url.us-east-1.on.aws/` | AWS_IAM (SigV4) |
| **AgentCore** | AgentCore Runtime | `arn:aws:bedrock-agentcore:us-east-1:226484346947:runtime/agentcore_strands_dev-sSCXyh2bVa` | AWS_IAM |

---

## 全体アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Frontend                                    │
│                         (Amplify + Cognito)                             │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                     services-client.ts                           │    │
│  │  ┌──────────────────────┐  ┌───────────────────────────────────┐ │    │
│  │  │ chatWithAgentCore()  │  │ chatWithLangChain()               │ │    │
│  │  └──────────────────────┘  └───────────────────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 │ IAM SigV4 認証
                                 │
          ┌──────────────────────┴──────────────────────┐
          │                                              │
          ▼                                              ▼
┌─────────────────────────────┐        ┌─────────────────────────────────┐
│     AgentCore Runtime       │        │         AWS Lambda              │
│                             │        │     (Container Image)           │
│  ┌───────────────────────┐  │        │  ┌───────────────────────────┐  │
│  │  agentcore_strands_dev│  │        │  │  langchain-service-dev   │  │
│  │                       │  │        │  │                           │  │
│  │  ┌─────────────────┐  │  │        │  │  ┌─────────────────────┐  │  │
│  │  │  Strands Agent  │  │  │        │  │  │ LangChain + LangGraph│  │  │
│  │  │                 │  │  │        │  │  │                      │  │  │
│  │  │  - agent.py     │  │  │        │  │  │  - handler.py        │  │  │
│  │  │  - tools.py     │  │  │        │  │  │  - agent.py          │  │  │
│  │  └────────┬────────┘  │  │        │  │  │  - tools.py          │  │  │
│  │           │           │  │        │  │  └──────────┬───────────┘  │  │
│  └───────────┼───────────┘  │        │  └─────────────┼──────────────┘  │
│              │              │        │                │                 │
└──────────────┼──────────────┘        └────────────────┼─────────────────┘
               │                                        │
               │                                        │
               └────────────────┬───────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │    AWS Bedrock        │
                    │                       │
                    │  Claude Sonnet 4      │
                    │                       │
                    └───────────────────────┘
```

---

## チャット実行シーケンス図

### 1. LangChain サービス呼び出し

```mermaid
sequenceDiagram
    participant User as ユーザー
    participant Frontend as Frontend<br/>(Amplify)
    participant Cognito as Cognito
    participant Lambda as Lambda<br/>(LangChain)
    participant Bedrock as AWS Bedrock

    User->>Frontend: チャット入力
    Frontend->>Cognito: 認証トークン取得
    Cognito-->>Frontend: IAM Credentials

    Frontend->>Lambda: POST /api/v1/chat<br/>(SigV4署名)
    Note over Frontend,Lambda: Function URL:<br/>https://hqtuy24...lambda-url.us-east-1.on.aws/

    Lambda->>Lambda: handler.py: リクエスト解析
    Lambda->>Lambda: agent.py: LangGraph実行
    
    loop ツール実行ループ
        Lambda->>Bedrock: InvokeModel (Claude)
        Bedrock-->>Lambda: AIレスポンス
        alt ツール呼び出しあり
            Lambda->>Lambda: tools.py: ツール実行
            Lambda->>Lambda: 結果をコンテキストに追加
        end
    end

    Lambda-->>Frontend: ChatResponse<br/>{content, tool_calls, latency_ms, metadata}
    Frontend-->>User: レスポンス表示
```

### 2. AgentCore サービス呼び出し

```mermaid
sequenceDiagram
    participant User as ユーザー
    participant Frontend as Frontend<br/>(Amplify)
    participant Cognito as Cognito
    participant Runtime as AgentCore<br/>Runtime
    participant Container as Strands<br/>Container
    participant Bedrock as AWS Bedrock

    User->>Frontend: チャット入力
    Frontend->>Cognito: 認証トークン取得
    Cognito-->>Frontend: IAM Credentials

    Frontend->>Runtime: POST /invocations<br/>(SigV4署名)
    Note over Frontend,Runtime: Runtime ID:<br/>agentcore_strands_dev-sSCXyh2bVa

    Runtime->>Container: リクエスト転送
    Container->>Container: agent.py: Strands Agent作成
    
    loop 自動ツールループ (Strands)
        Container->>Bedrock: InvokeModel (Claude)
        Bedrock-->>Container: AIレスポンス
        alt ツール呼び出しあり
            Container->>Container: tools.py: ツール実行
            Note over Container: Strandsの自動ツールループ
        end
    end

    Container-->>Runtime: InvocationResponse
    Runtime-->>Frontend: ChatResponse<br/>{content, tool_calls, latency_ms, metadata}
    Frontend-->>User: レスポンス表示
```

---

## 比較実行シーケンス図

```mermaid
sequenceDiagram
    participant User as ユーザー
    participant Frontend as Frontend
    participant Lambda as Lambda<br/>(LangChain)
    participant Runtime as AgentCore<br/>Runtime
    participant Bedrock as AWS Bedrock

    User->>Frontend: 比較テスト実行<br/>「東京の天気を教えて」

    par 並列実行
        Frontend->>Lambda: POST /api/v1/chat/tools
        Lambda->>Bedrock: InvokeModel
        Bedrock-->>Lambda: Response
        Lambda->>Lambda: get_current_weather("Tokyo")
        Lambda-->>Frontend: LangChain結果
    and
        Frontend->>Runtime: POST /invocations
        Runtime->>Bedrock: InvokeModel
        Bedrock-->>Runtime: Response
        Runtime->>Runtime: get_current_weather("Tokyo")
        Runtime-->>Frontend: AgentCore結果
    end

    Frontend->>Frontend: 結果比較<br/>- latency_ms<br/>- content<br/>- tool_calls

    Frontend-->>User: 比較結果表示
```

---

## ツール実行フロー比較

### LangChain (LangGraph StateGraph)

```mermaid
stateDiagram-v2
    [*] --> agent: 入力メッセージ
    agent --> should_continue: モデル呼び出し
    should_continue --> tools: tool_callsあり
    should_continue --> [*]: tool_callsなし
    tools --> agent: ツール結果を追加
```

### AgentCore (Strands自動ループ)

```mermaid
stateDiagram-v2
    [*] --> strands_agent: 入力メッセージ
    strands_agent --> check_tools: モデル呼び出し
    check_tools --> execute_tool: tool_useあり
    check_tools --> [*]: 完了
    execute_tool --> strands_agent: 自動的に継続
    
    note right of execute_tool: Strandsが自動で<br/>ツールループを管理
```

---

## デプロイシーケンス (AWS CodeBuild)

```mermaid
sequenceDiagram
    participant Dev as 開発者
    participant Git as GitHub
    participant CB as CodeBuild
    participant ECR as ECR
    participant Lambda as Lambda
    participant Runtime as AgentCore<br/>Runtime

    Dev->>Git: git push
    Git->>CB: Webhook / 手動トリガー

    rect rgb(200, 220, 240)
        Note over CB,ECR: LangChain ビルド
        CB->>CB: docker build (services/langchain)
        CB->>ECR: docker push<br/>langchain-service-dev:latest
        CB->>Lambda: update-function-code
    end

    rect rgb(220, 240, 200)
        Note over CB,Runtime: AgentCore ビルド
        CB->>CB: docker build (services/agentcore)
        CB->>ECR: docker push<br/>agentcore-service-dev:latest
        Note over Runtime: Runtime は自動で<br/>最新イメージを使用
    end

    CB-->>Dev: ビルド完了通知
```

---

## 統一API仕様

両サービスは同じAPIインターフェースを実装:

### Request

```json
POST /api/v1/chat
Content-Type: application/json

{
  "instruction": "東京の天気を教えて",
  "session_id": "optional-session-id",
  "use_tools": true
}
```

### Response

```json
{
  "response_id": "uuid",
  "content": "東京の現在の天気は晴れで、気温は22度です。",
  "tool_calls": [
    {
      "tool_name": "get_current_weather",
      "tool_input": {"location": "Tokyo", "unit": "celsius"},
      "tool_output": {"temperature": 22, "condition": "Sunny"}
    }
  ],
  "latency_ms": 1234,
  "metadata": {
    "service": "agentcore|langchain",
    "framework": "strands-agents|langchain + langgraph",
    "model_id": "us.anthropic.claude-sonnet-4-20250514-v1:0",
    "region": "us-east-1"
  }
}
```

---

## 比較評価項目

| 評価項目 | AgentCore (Strands) | LangChain |
|---------|---------------------|-----------|
| **レイテンシ** | latency_ms で測定 | latency_ms で測定 |
| **ツール実行回数** | tool_calls.length | tool_calls.length |
| **応答品質** | content の比較 | content の比較 |
| **コスト** | AgentCore Runtime課金 | Lambda課金 |
| **コールドスタート** | なし (常時起動) | あり (5-15秒) |

---

## 環境情報

```
AWS Account: 226484346947
Region: us-east-1
Model: us.anthropic.claude-sonnet-4-20250514-v1:0

LangChain Service:
  - Lambda Function: langchain-service-dev
  - Function URL: https://hqtuy24tbjdzbobyg4tzsr2xhe0rjmbx.lambda-url.us-east-1.on.aws/
  - ECR: 226484346947.dkr.ecr.us-east-1.amazonaws.com/langchain-service-dev:latest

AgentCore Service:
  - Runtime ID: agentcore_strands_dev-sSCXyh2bVa
  - Runtime ARN: arn:aws:bedrock-agentcore:us-east-1:226484346947:runtime/agentcore_strands_dev-sSCXyh2bVa
  - Endpoint: agentcore_strands_dev_endpoint
  - ECR: 226484346947.dkr.ecr.us-east-1.amazonaws.com/agentcore-service-dev:latest
```

