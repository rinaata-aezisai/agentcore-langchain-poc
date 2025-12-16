# AgentCore vs LangChain PoC

AWS Bedrock AgentCore (Strands Agents) と LangChain エコシステムの比較検証プロジェクト

## アーキテクチャ概要

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Presentation Layer                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                     Next.js + React (FSD + Atomic Design)              │  │
│  │   ┌─────────┐  ┌─────────┐  ┌───────────┐  ┌─────────────────────┐   │  │
│  │   │ Widgets │  │Features │  │ Entities  │  │    Shared (UI)       │   │  │
│  │   │         │  │         │  │           │  │  Atoms → Molecules   │   │  │
│  │   │ ChatBox │  │  Send   │  │  Message  │  │     → Organisms      │   │  │
│  │   │         │  │ Message │  │  Session  │  │                      │   │  │
│  │   └─────────┘  └─────────┘  └───────────┘  └─────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                 REST API
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Backend Layer (FastAPI)                            │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         API Layer (Routers)                          │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                      │                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      Application Layer (CQRS)                        │    │
│  │    ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │    │
│  │    │   Commands   │  │   Queries    │  │       Use Cases          │ │    │
│  │    │  (Write Ops) │  │  (Read Ops)  │  │   SendInstruction        │ │    │
│  │    └──────────────┘  └──────────────┘  │   StartSession           │ │    │
│  │                                        └──────────────────────────┘ │    │
│  │    ┌──────────────────────────────────────────────────────────────┐ │    │
│  │    │                      Ports (Interfaces)                      │ │    │
│  │    │    AgentPort  │  EventPublisherPort  │  RepositoryPorts      │ │    │
│  │    └──────────────────────────────────────────────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                      │                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                       Domain Layer (DDD + ES)                        │    │
│  │    ┌────────────┐  ┌──────────────┐  ┌────────────────────────────┐ │    │
│  │    │  Entities  │  │Value Objects │  │       Domain Events        │ │    │
│  │    │   Session  │  │   SessionId  │  │   SessionStarted           │ │    │
│  │    │   Message  │  │   Content    │  │   MessageAdded             │ │    │
│  │    └────────────┘  └──────────────┘  │   ToolCallRequested        │ │    │
│  │    ┌────────────┐  ┌──────────────┐  └────────────────────────────┘ │    │
│  │    │Aggregates  │  │  Repositories│                                 │    │
│  │    │  (Root)    │  │  (Interface) │                                 │    │
│  │    └────────────┘  └──────────────┘                                 │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                      │                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      Infrastructure Layer                            │    │
│  │    ┌─────────────────────────────────────────────────────────────┐  │    │
│  │    │                    Agent Adapters                            │  │    │
│  │    │    ┌──────────────────┐    ┌──────────────────────────────┐ │  │    │
│  │    │    │  StrandsAgent    │    │    LangChainAgent            │ │  │    │
│  │    │    │  (AgentCore)     │    │    (LangGraph)               │ │  │    │
│  │    │    └──────────────────┘    └──────────────────────────────┘ │  │    │
│  │    └─────────────────────────────────────────────────────────────┘  │    │
│  │    ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │    │
│  │    │ Persistence  │  │  Messaging   │  │      External        │   │    │
│  │    │  DynamoDB    │  │  EventBridge │  │      Bedrock         │   │    │
│  │    │  EventStore  │  │  SQS         │  │      Anthropic       │   │    │
│  │    └──────────────┘  └──────────────┘  └──────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AWS Infrastructure                              │
│    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐   │
│    │    Bedrock   │  │   DynamoDB   │  │  EventBridge │  │  CloudWatch │   │
│    │   (Claude)   │  │ (EventStore) │  │   (Events)   │  │   (Logs)    │   │
│    └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 技術スタック

### Backend (Python)

| カテゴリ | 技術 | 用途 |
|---------|------|------|
| **Framework** | FastAPI | 高性能非同期WebAPI |
| **AI Agent** | Strands Agents | AWS AgentCore SDK |
| **AI Agent** | LangChain + LangGraph | Agent orchestration |
| **Observability** | LangFuse | LLM observability |
| **Database** | DynamoDB | Event Store / Read Model |
| **Testing** | pytest | Unit/Integration testing |

### Frontend (TypeScript)

| カテゴリ | 技術 | 用途 |
|---------|------|------|
| **Framework** | Next.js + React | SSR/CSR対応 |
| **State** | TanStack Query | Server state management |
| **Design** | FSD + Atomic Design | アーキテクチャ |
| **Styling** | Tailwind CSS | ユーティリティCSS |
| **Testing** | Vitest | Unit testing |

### Infrastructure

| カテゴリ | 技術 | 用途 |
|---------|------|------|
| **IaC** | AWS CDK (TypeScript) | Infrastructure as Code |
| **AI** | Amazon Bedrock | Claude 3.5 Sonnet |
| **Storage** | DynamoDB | Event sourcing storage |
| **Messaging** | EventBridge / SQS | Event-driven |

## ディレクトリ構成

```
agentcore-langchain-poc/
├── docs/                           # ドキュメント
│   ├── rdra/                       # RDRA: Requirements-Driven Architecture
│   │   ├── system-context.md
│   │   ├── use-cases.md
│   │   ├── requirements-matrix.md
│   │   └── stakeholders.md
│   ├── ddd/                        # DDD: Domain-Driven Design
│   │   ├── domain-model.md
│   │   ├── bounded-contexts.md
│   │   ├── ubiquitous-language.md
│   │   └── context-map.md
│   ├── event-storming/             # Event Storming
│   │   ├── event-flow.md
│   │   ├── commands.md
│   │   ├── aggregates.md
│   │   └── policies.md
│   ├── architecture/               # アーキテクチャ設計
│   │   ├── clean-architecture.md
│   │   ├── event-sourcing.md
│   │   └── cqrs.md
│   └── decisions/                  # ADR (Architecture Decision Records)
│       └── 001-platform-selection.md
│
├── packages/
│   ├── backend/                    # Python FastAPI Backend
│   │   ├── domain/                 # ドメイン層
│   │   │   ├── entities/           # エンティティ
│   │   │   ├── value_objects/      # 値オブジェクト
│   │   │   ├── aggregates/         # アグリゲート
│   │   │   ├── repositories/       # リポジトリIF
│   │   │   ├── events/             # ドメインイベント
│   │   │   └── services/           # ドメインサービス
│   │   ├── application/            # アプリケーション層
│   │   │   ├── use_cases/          # ユースケース
│   │   │   ├── commands/           # CQRS コマンド
│   │   │   ├── queries/            # CQRS クエリ
│   │   │   ├── handlers/           # ハンドラ
│   │   │   └── ports/              # ポート（IF）
│   │   ├── infrastructure/         # インフラ層
│   │   │   ├── persistence/        # 永続化
│   │   │   ├── messaging/          # メッセージング
│   │   │   ├── external/           # 外部サービス連携
│   │   │   └── adapters/           # アダプター実装
│   │   ├── api/                    # API層（FastAPI）
│   │   │   ├── routers/            # ルーター
│   │   │   ├── middleware/         # ミドルウェア
│   │   │   └── schemas/            # スキーマ
│   │   ├── tests/                  # テスト
│   │   │   ├── unit/
│   │   │   └── integration/
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   │
│   └── presentation/               # Next.js Frontend (FSD)
│       ├── app/                    # Next.js App Router
│       ├── features/               # FSD Features
│       │   └── send-message/
│       ├── entities/               # FSD Entities
│       │   └── message/
│       ├── widgets/                # FSD Widgets
│       │   └── chat-window/
│       └── shared/                 # FSD Shared
│           ├── ui/                 # Atomic Design
│           │   ├── atoms/
│           │   ├── molecules/
│           │   └── organisms/
│           ├── lib/
│           └── api/
│
├── poc/                            # PoC実装
│   ├── agentcore/                  # Strands Agents PoC
│   └── langchain/                  # LangChain PoC
│
├── infra/                          # Infrastructure
│   └── cdk/                        # AWS CDK
│       ├── lib/
│       └── bin/
│
├── docker-compose.yml
└── README.md
```

## セットアップ

### 前提条件

- Python 3.11+
- Node.js 20+
- AWS CLI configured
- Docker (optional)

### Backend

```bash
cd packages/backend

# 仮想環境作成
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 依存関係インストール
pip install -e ".[dev]"

# 環境変数設定
cp .env.example .env
# .envファイルを編集

# 開発サーバー起動
uvicorn api.main:app --reload --port 8000
```

### Frontend

```bash
cd packages/presentation

# 依存関係インストール
npm install

# 開発サーバー起動
npm run dev
```

### Infrastructure

```bash
cd infra/cdk

# 依存関係インストール
npm install

# CDK デプロイ
cdk deploy
```

## 比較ポイント

### Strands Agents (AgentCore) vs LangChain

| 観点 | Strands Agents | LangChain |
|------|----------------|-----------|
| **AWSネイティブ** | ◎ 完全統合 | ○ langchain-aws |
| **エコシステム** | △ 新しい | ◎ 成熟 |
| **学習曲線** | ○ シンプル | △ 複雑 |
| **カスタマイズ** | ○ 標準的 | ◎ 高度 |
| **Observability** | ○ CloudWatch | ◎ LangSmith/LangFuse |
| **ワークフロー** | △ 限定的 | ◎ LangGraph |

## 開発ワークフロー

1. **RDRA** → 要件定義・分析
2. **DDD + Event Storming** → ドメインモデル設計
3. **Clean Architecture** → レイヤー構造設計
4. **Event Sourcing + CQRS** → データフロー設計
5. **FSD + Atomic Design** → フロントエンド設計
6. **TDD** → テスト駆動開発

## ライセンス

UNLICENSED - Internal PoC
