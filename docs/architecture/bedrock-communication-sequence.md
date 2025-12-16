# AWS Bedrock 通信シーケンス図

## 概要

このドキュメントでは、フロントエンドからAWS Bedrockまでの通信フローを示します。

## 全体アーキテクチャ

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│  PoC Layer  │────▶│AWS Bedrock  │
│  (Next.js)  │◀────│  (FastAPI)  │◀────│ (Adapters)  │◀────│  (Claude)   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

## シーケンス図

### 1. 基本的なチャットフロー

```mermaid
sequenceDiagram
    autonumber
    participant User
    participant Frontend as Frontend<br/>(Next.js/Amplify)
    participant API as Backend API<br/>(FastAPI)
    participant Handler as Command Handler<br/>(CQRS)
    participant Port as AgentPort<br/>(Interface)
    participant Strands as StrandsAgentAdapter<br/>(or LangChainAdapter)
    participant Bedrock as AWS Bedrock<br/>(Claude)

    User->>Frontend: メッセージ入力
    Frontend->>Frontend: Zustand Store更新
    
    Frontend->>API: POST /sessions/{id}/messages
    Note over Frontend,API: Authorization: Cognito JWT
    
    API->>Handler: SendMessageCommand
    Handler->>Handler: Session取得・バリデーション
    
    Handler->>Port: execute(context, instruction)
    Note over Handler,Port: Dependency Injection<br/>(FastAPI Depends)
    
    alt Strands Agents (AgentCore)
        Port->>Strands: execute()
        Strands->>Strands: Agent インスタンス作成
        Strands->>Bedrock: InvokeModel API
        Note over Strands,Bedrock: Region: us-east-1<br/>Model: claude-3-haiku
        Bedrock-->>Strands: Response (JSON)
        Strands-->>Port: AgentResponse
    else LangChain + LangGraph
        Port->>Strands: execute()
        Strands->>Strands: ChatBedrock 初期化
        Strands->>Bedrock: InvokeModel API
        Bedrock-->>Strands: Response (JSON)
        Strands-->>Port: AgentResponse
    end
    
    Port-->>Handler: AgentResponse
    Handler->>Handler: Event発行 (MessageAdded)
    Handler-->>API: Response DTO
    
    API-->>Frontend: 200 OK + Response
    Frontend->>Frontend: UI更新
    Frontend-->>User: レスポンス表示
```

### 2. ツール付きエージェント実行フロー

```mermaid
sequenceDiagram
    autonumber
    participant User
    participant Frontend as Frontend
    participant API as Backend API
    participant Handler as ExecuteAgentHandler
    participant Adapter as Strands/LangChain Adapter
    participant Bedrock as AWS Bedrock
    participant Tool as External Tool<br/>(Weather/Calculator)

    User->>Frontend: 「東京の天気を教えて」
    Frontend->>API: POST /sessions/{id}/messages
    API->>Handler: ExecuteAgentCommand
    
    Handler->>Adapter: execute_with_tools(context, instruction, tools)
    Adapter->>Bedrock: InvokeModel (tool_use enabled)
    
    Bedrock-->>Adapter: tool_use response
    Note over Bedrock,Adapter: tool: get_weather<br/>input: {"city": "Tokyo"}
    
    Adapter->>Tool: get_weather("Tokyo")
    Tool-->>Adapter: {"temp": 20, "condition": "sunny"}
    
    Adapter->>Bedrock: InvokeModel (tool_result)
    Bedrock-->>Adapter: Final response
    
    Adapter-->>Handler: AgentResponse
    Handler-->>API: Response
    API-->>Frontend: 200 OK
    Frontend-->>User: 「東京は20度で晴れです」
```

### 3. セッション管理フロー

```mermaid
sequenceDiagram
    autonumber
    participant User
    participant Frontend as Frontend
    participant Cognito as AWS Cognito<br/>(via Amplify)
    participant API as Backend API
    participant EventStore as Event Store<br/>(DynamoDB)
    participant Repository as Session Repository

    User->>Frontend: アプリ起動
    Frontend->>Cognito: signIn()
    Cognito-->>Frontend: JWT Token
    Frontend->>Frontend: Token保存
    
    User->>Frontend: 新規チャット開始
    Frontend->>API: POST /sessions
    Note over Frontend,API: Header: Authorization: Bearer {jwt}
    
    API->>Repository: start_session(agent_id, user_id)
    Repository->>EventStore: append(SessionStarted)
    EventStore-->>Repository: OK
    Repository-->>API: Session Entity
    
    API-->>Frontend: session_id
    Frontend->>Frontend: セッションID保存
    
    loop メッセージ送受信
        User->>Frontend: メッセージ入力
        Frontend->>API: POST /sessions/{id}/messages
        API->>Repository: add_message()
        Repository->>EventStore: append(MessageAdded)
        API-->>Frontend: Response
    end
    
    User->>Frontend: セッション終了
    Frontend->>API: DELETE /sessions/{id}
    API->>Repository: end_session()
    Repository->>EventStore: append(SessionEnded)
    API-->>Frontend: 204 No Content
```

### 4. 認証・認可フロー (Amplify Gen2)

```mermaid
sequenceDiagram
    autonumber
    participant User
    participant Frontend as Next.js<br/>(Amplify Client)
    participant Amplify as Amplify Auth<br/>(Library)
    participant Cognito as AWS Cognito<br/>User Pool
    participant API as Backend API
    participant IAM as AWS IAM

    User->>Frontend: ログインボタン
    Frontend->>Amplify: signIn(email, password)
    Amplify->>Cognito: InitiateAuth
    
    alt MFA有効
        Cognito-->>Amplify: MFA Required
        Amplify-->>Frontend: MFA Challenge
        Frontend-->>User: MFAコード入力
        User->>Frontend: コード入力
        Frontend->>Amplify: confirmSignIn(code)
        Amplify->>Cognito: RespondToAuthChallenge
    end
    
    Cognito-->>Amplify: AuthenticationResult
    Note over Cognito,Amplify: Access Token<br/>ID Token<br/>Refresh Token
    
    Amplify-->>Frontend: Session
    Frontend->>Frontend: トークン自動管理
    
    User->>Frontend: API呼び出し
    Frontend->>Amplify: getSession()
    Amplify-->>Frontend: Current Session (refreshed if needed)
    
    Frontend->>API: Request + Authorization Header
    API->>Cognito: Verify JWT
    Cognito-->>API: Token Valid + Claims
    
    API->>IAM: AssumeRoleWithWebIdentity
    Note over API,IAM: Cognito Identity Pool経由
    IAM-->>API: Temporary Credentials
    
    API->>API: Bedrock呼び出し (IAM認証)
```

## コンポーネント詳細

### Frontend (Next.js + Amplify Gen2)

```typescript
// Amplify設定
import { Amplify } from 'aws-amplify';
import outputs from '@/amplify_outputs.json';

Amplify.configure(outputs);

// API呼び出し (認証付き)
import { fetchAuthSession } from 'aws-amplify/auth';

async function callApi(endpoint: string, data: any) {
  const session = await fetchAuthSession();
  const token = session.tokens?.idToken?.toString();
  
  return fetch(`${API_URL}${endpoint}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
}
```

### Backend (FastAPI)

```python
# JWT検証
from fastapi import Depends, HTTPException
from jose import jwt, JWTError

async def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(
            token,
            COGNITO_PUBLIC_KEYS,
            algorithms=["RS256"],
            audience=COGNITO_CLIENT_ID,
        )
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### PoC Adapters

```python
# Strands Agents (AgentCore)
from strands import Agent
from strands.models import BedrockModel

model = BedrockModel(
    model_id="anthropic.claude-3-haiku-20240307-v1:0",
    region_name="us-east-1"
)
agent = Agent(model=model)
response = agent(instruction)

# LangChain
from langchain_aws import ChatBedrock

model = ChatBedrock(
    model_id="anthropic.claude-3-haiku-20240307-v1:0",
    region_name="us-east-1"
)
response = await model.ainvoke(messages)
```

## エラーハンドリング

```mermaid
sequenceDiagram
    participant Frontend
    participant API
    participant Adapter
    participant Bedrock

    Frontend->>API: Request
    API->>Adapter: execute()
    
    alt Token期限切れ
        Adapter->>Bedrock: InvokeModel
        Bedrock-->>Adapter: ExpiredTokenException
        Adapter-->>API: raise TokenExpiredError
        API-->>Frontend: 401 Unauthorized
        Frontend->>Frontend: Token Refresh
        Frontend->>API: Retry Request
    else Throttling
        Adapter->>Bedrock: InvokeModel
        Bedrock-->>Adapter: ThrottlingException
        Adapter->>Adapter: Exponential Backoff
        Adapter->>Bedrock: Retry
    else Model Not Found
        Adapter->>Bedrock: InvokeModel
        Bedrock-->>Adapter: ModelNotFound
        Adapter-->>API: raise ConfigurationError
        API-->>Frontend: 500 Internal Server Error
    end
```

## レイテンシ分析

| ステップ | 想定レイテンシ | 備考 |
|----------|---------------|------|
| Frontend → Backend | 10-50ms | ネットワーク遅延 |
| JWT検証 | 5-20ms | キャッシュ有効時 |
| Handler処理 | 1-5ms | ビジネスロジック |
| Bedrock API呼び出し | 500-3000ms | モデル・プロンプト依存 |
| Response処理 | 1-5ms | シリアライゼーション |
| **合計** | **520-3100ms** | |

## 次のステップ

1. Amplify Gen2でフロントエンド認証を実装
2. Cognito User Pool設定
3. E2Eテスト実行

