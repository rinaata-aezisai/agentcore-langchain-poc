# AgentCore Runtime 実装レポート

**作成日**: 2025-12-17  
**ステータス**: 進行中  
**リポジトリ**: https://github.com/aezisai-inc/agentcore-langchain-poc

---

## 1. 概要

本レポートは、AWS Bedrock AgentCore Runtimeの実装過程で遭遇した課題、解決策、および今後の対応をまとめたものです。

### 1.1 目標

- ECRにデプロイされたエージェントをAgentCore Runtime経由で呼び出す
- フロントエンド（Amplify）からAgentCore Runtimeに接続する
- Strands AgentとLangChainの比較検証環境を構築する

### 1.2 現在のアーキテクチャ

```
Frontend (Amplify/Next.js)
    ↓
AgentCore Runtime Endpoint
    ↓
ECR Container (/invocations, /ping)
    ↓
Strands Agent → Bedrock
```

---

## 2. 実装済み項目

### 2.1 AgentCore Runtime用コンテナ

**ファイル**: `agentcore-runtime/`

| ファイル | 説明 |
|---------|------|
| `agent.py` | FastAPI + Strands Agentの統合実装 |
| `Dockerfile` | ARM64アーキテクチャ対応（AWS公式要件） |
| `pyproject.toml` | 依存関係定義 |

**エンドポイント**:
- `POST /invocations` - エージェント呼び出し（AgentCore Runtime必須）
- `GET /ping` - ヘルスチェック（AgentCore Runtime必須）
- `GET /health` - 拡張ヘルスチェック
- `POST /sessions` - セッション作成
- `GET /sessions/{id}` - セッション取得
- `POST /sessions/{id}/messages` - メッセージ送信
- `DELETE /sessions/{id}` - セッション終了

### 2.2 GitHub Actions CI/CD

**ファイル**: `.github/workflows/deploy-agentcore-runtime.yml`

**機能**:
- ECRリポジトリの自動作成
- ARM64 Dockerイメージのビルド・プッシュ
- IAMロールの作成（AgentCoreRuntimeRole）
- AgentCore Runtimeの作成/更新
- ステータス監視（READY状態まで待機）

### 2.3 バックエンド統合

**ファイル**: `backend/src/infrastructure/agents/agentcore_runtime_adapter.py`

- `invoke_agent_runtime` APIを使用したAgentCore Runtime接続
- `AgentPort`インターフェース準拠

**ファイル**: `backend/src/api/dependencies.py`

- `AGENT_RUNTIME_ARN`環境変数のサポート
- 接続モードの優先順位:
  1. 開発環境: MockAgentPort
  2. AGENT_RUNTIME_ARN設定時: AgentCore Runtime
  3. フォールバック: Direct Bedrock

### 2.4 CDK IAMポリシー更新

**ファイル**: `infra/cdk/lib/ecs-stack.ts`, `infra/cdk/lib/api-stack.ts`

- `bedrock-agentcore:InvokeAgentRuntime`権限を追加

---

## 3. 遭遇した課題と解決策

### 3.1 AWS CLI引数エラー

**問題**:
```
ERROR: the following arguments are required: --agent-runtime-id, --role-arn, --network-configuration
```

**原因**: `update-agent-runtime`コマンドで`--agent-runtime-arn`を使用していたが、正しくは`--agent-runtime-id`が必要

**解決策**: ワークフローを修正
```yaml
# 修正前
aws bedrock-agentcore-control update-agent-runtime \
  --agent-runtime-arn "$EXISTING_ARN"

# 修正後
aws bedrock-agentcore-control update-agent-runtime \
  --agent-runtime-id "$EXISTING_ID" \
  --agent-runtime-artifact "{...}" \
  --role-arn "$ROLE_ARN" \
  --network-configuration '{"networkMode":"PUBLIC"}'
```

**参照**: https://docs.aws.amazon.com/cli/latest/reference/bedrock-agentcore-control/update-agent-runtime.html

### 3.2 agentRuntimeName正規表現エラー

**問題**:
```
ValidationException: agentRuntimeName 'agentcore-poc-strands' did not satisfy regex pattern [a-zA-Z][a-zA-Z0-9_]{0,47}
```

**原因**: ハイフン(`-`)は使用不可、アンダースコア(`_`)のみ許可

**解決策**: `AGENT_NAME`を`agentcore_poc_strands`に変更

### 3.3 ECR権限エラー

**問題**:
```
Access denied: execution role requires ecr:GetAuthorizationToken, ecr:BatchGetImage, ecr:GetDownloadUrlForLayer
```

**原因**: IAMロールにECR権限が不足

**解決策**: IAMポリシーにECR権限を追加
```json
{
  "Effect": "Allow",
  "Action": [
    "ecr:GetAuthorizationToken",
    "ecr:BatchGetImage",
    "ecr:GetDownloadUrlForLayer"
  ],
  "Resource": "*"
}
```

### 3.4 Dockerfile hatchビルドエラー

**問題**:
```
metadata-generation-failed: tool.hatch.build.targets.wheel requires at least one file selection option
```

**原因**: pyproject.tomlでhatchのwheel設定が不足

**解決策**: pyproject.tomlに以下を追加
```toml
[tool.hatch.build.targets.wheel]
packages = ["."]
```

Dockerfileも修正:
```dockerfile
# 修正前
RUN pip install .

# 修正後
RUN pip install fastapi uvicorn strands-agents boto3 httpx pydantic
```

### 3.5 GitHub Appワークフロー権限

**問題**:
```
Permission denied: GitHub App is not allowed to create or update workflow without 'workflows' permission
```

**原因**: GitHub App Installationトークンに`workflows`スコープがない

**解決策**: ワークフローファイルはWeb UIから手動で編集

### 3.6 フロントエンド404エラー（現在進行中）

**問題**:
```
POST https://7pdc7e2ulnj3l2uhkgqsmn2awa0yzkaf.lambda-url.ap-northeast-1.on.aws/services/runtime/execute 404 (Not Found)
```

**原因**: フロントエンドが古いLambda URLに接続している

**解決策**: AgentCore Runtimeエンドポイントに接続先を変更（次セクション参照）

---

## 4. AgentCore Runtime エンドポイント仕様

### 4.1 エンドポイントURL形式

AWS公式ドキュメントによると、AgentCore Runtimeには直接HTTPエンドポイントが存在します:

```
https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{EncodedAgentARN}/invocations
```

**参照**: https://aws.amazon.com/blogs/machine-learning/set-up-custom-domain-names-for-amazon-bedrock-agentcore-runtime-agents/

### 4.2 認証要件

- **Bearer Token**（Cognito JWT）が必要
- ヘッダー: `Authorization: Bearer {token}`
- セッションID: `X-Amzn-Bedrock-AgentCore-Runtime-Session-Id`

### 4.3 カスタムドメイン設定（オプション）

CloudFrontをリバースプロキシとして使用することで、カスタムドメインを設定可能:
- `https://agent.yourcompany.com/` → AgentCore Runtime

---

## 5. 次のステップ

### 5.1 即時対応

1. **AgentCore Runtime ARNの取得**
   - GitHub Actionsログまたは AWS Console から取得
   - 形式: `arn:aws:bedrock-agentcore:us-east-1:226484346947:runtime/agentcore_poc_strands`

2. **フロントエンド接続先の更新**
   - `NEXT_PUBLIC_API_URL`環境変数をAgentCore Runtimeエンドポイントに変更
   - Amplify環境変数を更新

3. **接続テスト**
   - curlでAgentCore Runtimeエンドポイントを直接テスト
   - フロントエンドからの接続確認

### 5.2 中期対応

1. **CloudFront + カスタムドメイン設定**
   - CORS問題の解消
   - ブランドドメインの使用

2. **CodeDeploy移行検討**
   - 本番環境ではBlue/Greenデプロイメント
   - 自動ロールバック機能

### 5.3 長期対応

1. **AgentCore Memory統合**
   - 現在はin-memoryセッション管理
   - 本番ではAgentCore Memory推奨

2. **マルチエージェント対応**
   - Strands / LangChain切り替え
   - A2Aプロトコル対応

---

## 6. 参考資料

### AWS公式ドキュメント

| ドキュメント | URL |
|-------------|-----|
| AgentCore Runtime概要 | https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agents-tools-runtime.html |
| Runtime Service Contract | https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-service-contract.html |
| カスタムエージェントデプロイ | https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/getting-started-custom.html |
| invoke-agent-runtime API | https://docs.aws.amazon.com/cli/latest/reference/bedrock-agentcore/invoke-agent-runtime.html |
| update-agent-runtime API | https://docs.aws.amazon.com/cli/latest/reference/bedrock-agentcore-control/update-agent-runtime.html |
| エンドポイントとクォータ | https://docs.aws.amazon.com/general/latest/gr/bedrock_agentcore.html |
| カスタムドメイン設定 | https://aws.amazon.com/blogs/machine-learning/set-up-custom-domain-names-for-amazon-bedrock-agentcore-runtime-agents/ |

### 関連PR

| PR | 説明 |
|----|------|
| #5 | Dockerfile build fix |
| #8 | Unified API in AgentCore Runtime |

---

## 7. 変更履歴

| 日付 | 変更内容 |
|------|----------|
| 2025-12-17 | 初版作成、実装状況と課題をまとめ |

---

## 付録A: 環境変数一覧

| 変数名 | 説明 | 例 |
|--------|------|-----|
| `AGENT_RUNTIME_ARN` | AgentCore Runtime ARN | `arn:aws:bedrock-agentcore:us-east-1:...` |
| `NEXT_PUBLIC_API_URL` | フロントエンドAPI接続先 | `https://bedrock-agentcore.us-east-1.amazonaws.com/runtimes/...` |
| `AWS_REGION` | AWSリージョン | `us-east-1` |
| `BEDROCK_MODEL_ID` | Bedrockモデル | `anthropic.claude-3-haiku-20240307-v1:0` |

## 付録B: AgentCore Runtimeリージョン

| リージョン | Control Plane | Data Plane |
|-----------|---------------|------------|
| us-east-1 | bedrock-agentcore-control.us-east-1.amazonaws.com | bedrock-agentcore.us-east-1.amazonaws.com |
| us-east-2 | bedrock-agentcore-control.us-east-2.amazonaws.com | bedrock-agentcore.us-east-2.amazonaws.com |
| us-west-2 | bedrock-agentcore-control.us-west-2.amazonaws.com | bedrock-agentcore.us-west-2.amazonaws.com |
| ap-northeast-1 | bedrock-agentcore-control.ap-northeast-1.amazonaws.com | bedrock-agentcore.ap-northeast-1.amazonaws.com |
| eu-central-1 | bedrock-agentcore-control.eu-central-1.amazonaws.com | bedrock-agentcore.eu-central-1.amazonaws.com |
