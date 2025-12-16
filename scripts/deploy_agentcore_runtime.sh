#!/bin/bash
# AgentCore Runtime デプロイスクリプト
# 
# 使用方法:
#   ./scripts/deploy_agentcore_runtime.sh
#
# 必要な環境変数 (GitHub Secretsから設定):
#   - AWS_ACCESS_KEY_ID
#   - AWS_SECRET_ACCESS_KEY
#   - AWS_REGION (デフォルト: us-east-1)
#
# オプション環境変数:
#   - AGENT_NAME (デフォルト: agentcore-poc-strands)
#   - ECR_REPO_NAME (デフォルト: agentcore-poc-runtime)

set -euo pipefail

# ===========================================
# 設定
# ===========================================

AWS_REGION="${AWS_REGION:-us-east-1}"
AGENT_NAME="${AGENT_NAME:-agentcore-poc-strands}"
ECR_REPO_NAME="${ECR_REPO_NAME:-agentcore-poc-runtime}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RUNTIME_DIR="$PROJECT_ROOT/agentcore-runtime"

# 色付き出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ===========================================
# 前提条件チェック
# ===========================================

check_prerequisites() {
    log_info "前提条件をチェック中..."
    
    # AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI がインストールされていません"
        exit 1
    fi
    
    # Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker がインストールされていません"
        exit 1
    fi
    
    # AWS認証
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS認証に失敗しました。認証情報を確認してください。"
        exit 1
    fi
    
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    log_info "AWS Account ID: $AWS_ACCOUNT_ID"
    log_info "AWS Region: $AWS_REGION"
}

# ===========================================
# ECR リポジトリ作成
# ===========================================

create_ecr_repository() {
    log_info "ECRリポジトリを確認/作成中: $ECR_REPO_NAME"
    
    if aws ecr describe-repositories --repository-names "$ECR_REPO_NAME" --region "$AWS_REGION" &> /dev/null; then
        log_info "ECRリポジトリは既に存在します"
    else
        log_info "ECRリポジトリを作成中..."
        aws ecr create-repository \
            --repository-name "$ECR_REPO_NAME" \
            --region "$AWS_REGION" \
            --image-scanning-configuration scanOnPush=true
        log_info "ECRリポジトリを作成しました"
    fi
    
    ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME"
    log_info "ECR URI: $ECR_URI"
}

# ===========================================
# Docker イメージビルド & プッシュ
# ===========================================

build_and_push_image() {
    log_info "Dockerイメージをビルド中 (ARM64)..."
    
    cd "$RUNTIME_DIR"
    
    # Docker buildx セットアップ
    docker buildx create --use --name agentcore-builder 2>/dev/null || true
    
    # ECRログイン
    log_info "ECRにログイン中..."
    aws ecr get-login-password --region "$AWS_REGION" | \
        docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
    
    # ARM64イメージをビルド & プッシュ
    log_info "ARM64イメージをビルド & プッシュ中..."
    docker buildx build \
        --platform linux/arm64 \
        -t "$ECR_URI:latest" \
        -t "$ECR_URI:$(date +%Y%m%d-%H%M%S)" \
        --push \
        .
    
    log_info "イメージをプッシュしました: $ECR_URI:latest"
}

# ===========================================
# IAMロール作成
# ===========================================

create_iam_role() {
    ROLE_NAME="AgentCoreRuntimeRole-$AGENT_NAME"
    
    log_info "IAMロールを確認/作成中: $ROLE_NAME"
    
    if aws iam get-role --role-name "$ROLE_NAME" &> /dev/null; then
        log_info "IAMロールは既に存在します"
    else
        log_info "IAMロールを作成中..."
        
        # 信頼ポリシー
        TRUST_POLICY=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "bedrock-agentcore.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF
)
        
        aws iam create-role \
            --role-name "$ROLE_NAME" \
            --assume-role-policy-document "$TRUST_POLICY"
        
        # Bedrock呼び出し権限を付与
        BEDROCK_POLICY=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "*"
        }
    ]
}
EOF
)
        
        aws iam put-role-policy \
            --role-name "$ROLE_NAME" \
            --policy-name "BedrockInvokePolicy" \
            --policy-document "$BEDROCK_POLICY"
        
        # ロールが利用可能になるまで待機
        log_info "IAMロールの伝播を待機中..."
        sleep 10
        
        log_info "IAMロールを作成しました"
    fi
    
    ROLE_ARN="arn:aws:iam::$AWS_ACCOUNT_ID:role/$ROLE_NAME"
    log_info "Role ARN: $ROLE_ARN"
}

# ===========================================
# AgentCore Runtime 作成
# ===========================================

create_agent_runtime() {
    log_info "AgentCore Runtimeを作成中: $AGENT_NAME"
    
    # 既存のRuntimeを確認
    EXISTING_RUNTIME=$(aws bedrock-agentcore-control list-agent-runtimes \
        --region "$AWS_REGION" \
        --query "agentRuntimes[?agentRuntimeName=='$AGENT_NAME'].agentRuntimeArn" \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$EXISTING_RUNTIME" ] && [ "$EXISTING_RUNTIME" != "None" ]; then
        log_info "AgentCore Runtimeは既に存在します"
        log_info "既存のRuntimeを更新中..."
        
        # 既存のRuntimeを更新
        RESPONSE=$(aws bedrock-agentcore-control update-agent-runtime \
            --agent-runtime-arn "$EXISTING_RUNTIME" \
            --agent-runtime-artifact "{\"containerConfiguration\":{\"containerUri\":\"$ECR_URI:latest\"}}" \
            --region "$AWS_REGION" \
            --output json)
        
        AGENT_RUNTIME_ARN="$EXISTING_RUNTIME"
    else
        log_info "新しいAgentCore Runtimeを作成中..."
        
        RESPONSE=$(aws bedrock-agentcore-control create-agent-runtime \
            --agent-runtime-name "$AGENT_NAME" \
            --agent-runtime-artifact "{\"containerConfiguration\":{\"containerUri\":\"$ECR_URI:latest\"}}" \
            --network-configuration '{"networkMode":"PUBLIC"}' \
            --role-arn "$ROLE_ARN" \
            --region "$AWS_REGION" \
            --output json)
        
        AGENT_RUNTIME_ARN=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['agentRuntimeArn'])")
    fi
    
    log_info "AgentCore Runtime ARN: $AGENT_RUNTIME_ARN"
    
    # ステータス確認
    log_info "AgentCore Runtimeのステータスを確認中..."
    for i in {1..30}; do
        STATUS=$(aws bedrock-agentcore-control get-agent-runtime \
            --agent-runtime-arn "$AGENT_RUNTIME_ARN" \
            --region "$AWS_REGION" \
            --query "status" \
            --output text 2>/dev/null || echo "UNKNOWN")
        
        log_info "ステータス: $STATUS"
        
        if [ "$STATUS" = "READY" ]; then
            log_info "AgentCore Runtimeが準備完了しました！"
            break
        elif [ "$STATUS" = "CREATE_FAILED" ] || [ "$STATUS" = "UPDATE_FAILED" ]; then
            log_error "AgentCore Runtimeの作成/更新に失敗しました"
            exit 1
        fi
        
        sleep 10
    done
}

# ===========================================
# 結果出力
# ===========================================

output_results() {
    echo ""
    echo "=========================================="
    echo -e "${GREEN}デプロイ完了！${NC}"
    echo "=========================================="
    echo ""
    echo "AgentCore Runtime ARN:"
    echo "  $AGENT_RUNTIME_ARN"
    echo ""
    echo "次のステップ:"
    echo "  1. 環境変数を設定:"
    echo "     export AGENT_RUNTIME_ARN=$AGENT_RUNTIME_ARN"
    echo ""
    echo "  2. GitHub Secretsに追加:"
    echo "     AGENT_RUNTIME_ARN=$AGENT_RUNTIME_ARN"
    echo ""
    echo "  3. バックエンドを再デプロイして疎通確認"
    echo ""
}

# ===========================================
# メイン処理
# ===========================================

main() {
    log_info "AgentCore Runtime デプロイを開始します..."
    echo ""
    
    check_prerequisites
    create_ecr_repository
    build_and_push_image
    create_iam_role
    create_agent_runtime
    output_results
}

main "$@"
