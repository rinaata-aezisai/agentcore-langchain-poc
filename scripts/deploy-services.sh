#!/bin/bash
# Services Deployment Script
# AgentCore (ECR → AgentCore Runtime) と LangChain (ECR → Lambda) のデプロイ

set -e

# ===========================================
# Configuration
# ===========================================

ENVIRONMENT=${1:-dev}
AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

AGENTCORE_REPO="agentcore-service-${ENVIRONMENT}"
LANGCHAIN_REPO="langchain-service-${ENVIRONMENT}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ===========================================
# Functions
# ===========================================

log_info() {
    echo "ℹ️  $1"
}

log_success() {
    echo "✅ $1"
}

log_error() {
    echo "❌ $1" >&2
}

# ECR リポジトリ作成
create_ecr_repo() {
    local repo_name=$1
    log_info "Creating ECR repository: ${repo_name}"
    
    aws ecr describe-repositories --repository-names "${repo_name}" --region "${AWS_REGION}" 2>/dev/null || \
    aws ecr create-repository \
        --repository-name "${repo_name}" \
        --region "${AWS_REGION}" \
        --image-scanning-configuration scanOnPush=true
    
    log_success "ECR repository ready: ${repo_name}"
}

# ECR ログイン
ecr_login() {
    log_info "Logging in to ECR..."
    aws ecr get-login-password --region "${AWS_REGION}" | \
        docker login --username AWS --password-stdin "${ECR_REGISTRY}"
    log_success "ECR login successful"
}

# AgentCore サービスビルド & プッシュ
build_agentcore() {
    log_info "Building AgentCore service..."
    
    cd "${PROJECT_ROOT}/services/agentcore"
    
    # ARM64 ビルド (AgentCore Runtime 推奨)
    docker build --platform linux/arm64 -t "${AGENTCORE_REPO}:latest" .
    
    docker tag "${AGENTCORE_REPO}:latest" "${ECR_REGISTRY}/${AGENTCORE_REPO}:latest"
    docker tag "${AGENTCORE_REPO}:latest" "${ECR_REGISTRY}/${AGENTCORE_REPO}:$(git rev-parse --short HEAD)"
    
    log_info "Pushing AgentCore service to ECR..."
    docker push "${ECR_REGISTRY}/${AGENTCORE_REPO}:latest"
    docker push "${ECR_REGISTRY}/${AGENTCORE_REPO}:$(git rev-parse --short HEAD)"
    
    log_success "AgentCore service pushed: ${ECR_REGISTRY}/${AGENTCORE_REPO}:latest"
}

# LangChain サービスビルド & プッシュ
build_langchain() {
    log_info "Building LangChain service..."
    
    cd "${PROJECT_ROOT}/services/langchain"
    
    # AMD64 ビルド (Lambda 標準)
    docker build --platform linux/amd64 -t "${LANGCHAIN_REPO}:latest" .
    
    docker tag "${LANGCHAIN_REPO}:latest" "${ECR_REGISTRY}/${LANGCHAIN_REPO}:latest"
    docker tag "${LANGCHAIN_REPO}:latest" "${ECR_REGISTRY}/${LANGCHAIN_REPO}:$(git rev-parse --short HEAD)"
    
    log_info "Pushing LangChain service to ECR..."
    docker push "${ECR_REGISTRY}/${LANGCHAIN_REPO}:latest"
    docker push "${ECR_REGISTRY}/${LANGCHAIN_REPO}:$(git rev-parse --short HEAD)"
    
    log_success "LangChain service pushed: ${ECR_REGISTRY}/${LANGCHAIN_REPO}:latest"
}

# Lambda 関数作成/更新
deploy_lambda() {
    local function_name="langchain-service-${ENVIRONMENT}"
    local image_uri="${ECR_REGISTRY}/${LANGCHAIN_REPO}:latest"
    
    log_info "Deploying Lambda function: ${function_name}"
    
    # Lambda 関数が存在するか確認
    if aws lambda get-function --function-name "${function_name}" --region "${AWS_REGION}" 2>/dev/null; then
        # 更新
        log_info "Updating existing Lambda function..."
        aws lambda update-function-code \
            --function-name "${function_name}" \
            --image-uri "${image_uri}" \
            --region "${AWS_REGION}"
    else
        # 新規作成
        log_info "Creating new Lambda function..."
        
        # IAM ロール作成（存在しない場合）
        create_lambda_role
        
        aws lambda create-function \
            --function-name "${function_name}" \
            --package-type Image \
            --code ImageUri="${image_uri}" \
            --role "arn:aws:iam::${AWS_ACCOUNT_ID}:role/langchain-service-lambda-role" \
            --timeout 300 \
            --memory-size 1024 \
            --environment "Variables={AWS_REGION=${AWS_REGION},BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0}" \
            --region "${AWS_REGION}"
        
        # Function URL 作成
        aws lambda create-function-url-config \
            --function-name "${function_name}" \
            --auth-type AWS_IAM \
            --region "${AWS_REGION}"
    fi
    
    # Function URL を取得
    local function_url=$(aws lambda get-function-url-config \
        --function-name "${function_name}" \
        --region "${AWS_REGION}" \
        --query 'FunctionUrl' \
        --output text 2>/dev/null || echo "")
    
    log_success "Lambda deployed: ${function_name}"
    if [ -n "${function_url}" ]; then
        log_success "Function URL: ${function_url}"
    fi
}

# Lambda 用 IAM ロール作成
create_lambda_role() {
    local role_name="langchain-service-lambda-role"
    
    log_info "Creating IAM role for Lambda..."
    
    # ロールが存在するか確認
    if aws iam get-role --role-name "${role_name}" 2>/dev/null; then
        log_info "IAM role already exists: ${role_name}"
        return
    fi
    
    # Trust policy
    cat > /tmp/trust-policy.json << 'EOF'
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF

    # ロール作成
    aws iam create-role \
        --role-name "${role_name}" \
        --assume-role-policy-document file:///tmp/trust-policy.json
    
    # 基本的な Lambda 実行ポリシー
    aws iam attach-role-policy \
        --role-name "${role_name}" \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
    
    # Bedrock 呼び出しポリシー
    cat > /tmp/bedrock-policy.json << 'EOF'
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": "arn:aws:bedrock:*::foundation-model/*"
        }
    ]
}
EOF

    aws iam put-role-policy \
        --role-name "${role_name}" \
        --policy-name "BedrockInvokePolicy" \
        --policy-document file:///tmp/bedrock-policy.json
    
    # ロールの伝播を待つ
    log_info "Waiting for IAM role to propagate..."
    sleep 10
    
    log_success "IAM role created: ${role_name}"
}

# ===========================================
# Main
# ===========================================

main() {
    echo "================================================"
    echo "🚀 Services Deployment"
    echo "   Environment: ${ENVIRONMENT}"
    echo "   Region: ${AWS_REGION}"
    echo "   Account: ${AWS_ACCOUNT_ID}"
    echo "================================================"
    
    # Docker 確認
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    
    # ECR ログイン
    ecr_login
    
    # ECR リポジトリ作成
    create_ecr_repo "${AGENTCORE_REPO}"
    create_ecr_repo "${LANGCHAIN_REPO}"
    
    # サービスビルド & プッシュ
    case "${2:-all}" in
        agentcore)
            build_agentcore
            ;;
        langchain)
            build_langchain
            deploy_lambda
            ;;
        all)
            build_agentcore
            build_langchain
            deploy_lambda
            ;;
        *)
            log_error "Unknown service: ${2}"
            echo "Usage: $0 [environment] [agentcore|langchain|all]"
            exit 1
            ;;
    esac
    
    echo ""
    echo "================================================"
    echo "✅ Deployment Complete!"
    echo ""
    echo "📦 ECR Images:"
    echo "   AgentCore: ${ECR_REGISTRY}/${AGENTCORE_REPO}:latest"
    echo "   LangChain: ${ECR_REGISTRY}/${LANGCHAIN_REPO}:latest"
    echo ""
    echo "🔗 Next Steps:"
    echo "   1. AgentCore: Register in AgentCore Runtime console"
    echo "   2. LangChain: Lambda function URL is ready"
    echo "   3. Update frontend to call both services"
    echo "================================================"
}

main "$@"

