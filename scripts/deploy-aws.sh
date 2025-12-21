#!/bin/bash
# AWS完結デプロイスクリプト
# CloudShell または CodeBuild で実行
# ローカルDocker不要

set -e

ENVIRONMENT=${1:-dev}
AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICES_DIR="${PROJECT_ROOT}/services"

echo "================================================"
echo "🚀 AWS Deploy (Docker不要)"
echo "   Environment: ${ENVIRONMENT}"
echo "   Region: ${AWS_REGION}"
echo "   Account: ${AWS_ACCOUNT_ID}"
echo "================================================"

# ===========================================
# Step 1: ECRリポジトリ作成
# ===========================================
create_ecr_repos() {
    echo "📦 Creating ECR repositories..."
    
    for repo in "agentcore-service-${ENVIRONMENT}" "langchain-service-${ENVIRONMENT}"; do
        aws ecr describe-repositories --repository-names "${repo}" --region "${AWS_REGION}" 2>/dev/null || \
        aws ecr create-repository \
            --repository-name "${repo}" \
            --region "${AWS_REGION}" \
            --image-scanning-configuration scanOnPush=true \
            --image-tag-mutability MUTABLE
        echo "✅ ECR repo ready: ${repo}"
    done
}

# ===========================================
# Step 2: CodeBuildプロジェクト作成
# ===========================================
create_codebuild_projects() {
    echo "🔨 Creating CodeBuild projects..."
    
    # CodeBuild用IAMロール
    CODEBUILD_ROLE_NAME="codebuild-services-role-${ENVIRONMENT}"
    
    # ロールが存在するか確認
    if ! aws iam get-role --role-name "${CODEBUILD_ROLE_NAME}" 2>/dev/null; then
        echo "Creating IAM role for CodeBuild..."
        
        cat > /tmp/codebuild-trust.json << 'EOF'
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "codebuild.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF
        
        aws iam create-role \
            --role-name "${CODEBUILD_ROLE_NAME}" \
            --assume-role-policy-document file:///tmp/codebuild-trust.json
        
        # ECR権限
        aws iam attach-role-policy \
            --role-name "${CODEBUILD_ROLE_NAME}" \
            --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser
        
        # CloudWatch Logs権限
        aws iam attach-role-policy \
            --role-name "${CODEBUILD_ROLE_NAME}" \
            --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess
        
        # Lambda更新権限
        cat > /tmp/lambda-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "lambda:UpdateFunctionCode",
                "lambda:GetFunction"
            ],
            "Resource": "arn:aws:lambda:${AWS_REGION}:${AWS_ACCOUNT_ID}:function:langchain-service-${ENVIRONMENT}"
        }
    ]
}
EOF
        aws iam put-role-policy \
            --role-name "${CODEBUILD_ROLE_NAME}" \
            --policy-name "LambdaUpdatePolicy" \
            --policy-document file:///tmp/lambda-policy.json
        
        echo "Waiting for IAM role propagation..."
        sleep 10
    fi
    
    CODEBUILD_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${CODEBUILD_ROLE_NAME}"
    
    # AgentCore CodeBuildプロジェクト
    echo "Creating AgentCore CodeBuild project..."
    cat > /tmp/agentcore-codebuild.json << EOF
{
    "name": "agentcore-service-build-${ENVIRONMENT}",
    "description": "Build AgentCore Service",
    "source": {
        "type": "NO_SOURCE",
        "buildspec": "version: 0.2\nphases:\n  pre_build:\n    commands:\n      - echo Logging in to ECR...\n      - aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com\n  build:\n    commands:\n      - echo Building AgentCore service...\n      - cd services/agentcore\n      - docker build -t agentcore-service .\n      - docker tag agentcore-service:latest ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/agentcore-service-${ENVIRONMENT}:latest\n  post_build:\n    commands:\n      - docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/agentcore-service-${ENVIRONMENT}:latest\n      - echo AgentCore service pushed!"
    },
    "artifacts": {
        "type": "NO_ARTIFACTS"
    },
    "environment": {
        "type": "ARM_CONTAINER",
        "image": "aws/codebuild/amazonlinux2-aarch64-standard:3.0",
        "computeType": "BUILD_GENERAL1_SMALL",
        "privilegedMode": true
    },
    "serviceRole": "${CODEBUILD_ROLE_ARN}",
    "timeoutInMinutes": 30
}
EOF
    
    aws codebuild create-project --cli-input-json file:///tmp/agentcore-codebuild.json --region "${AWS_REGION}" 2>/dev/null || \
    aws codebuild update-project --cli-input-json file:///tmp/agentcore-codebuild.json --region "${AWS_REGION}"
    
    # LangChain CodeBuildプロジェクト
    echo "Creating LangChain CodeBuild project..."
    cat > /tmp/langchain-codebuild.json << EOF
{
    "name": "langchain-service-build-${ENVIRONMENT}",
    "description": "Build LangChain Service",
    "source": {
        "type": "NO_SOURCE",
        "buildspec": "version: 0.2\nphases:\n  pre_build:\n    commands:\n      - echo Logging in to ECR...\n      - aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com\n  build:\n    commands:\n      - echo Building LangChain service...\n      - cd services/langchain\n      - docker build -t langchain-service .\n      - docker tag langchain-service:latest ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/langchain-service-${ENVIRONMENT}:latest\n  post_build:\n    commands:\n      - docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/langchain-service-${ENVIRONMENT}:latest\n      - aws lambda update-function-code --function-name langchain-service-${ENVIRONMENT} --image-uri ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/langchain-service-${ENVIRONMENT}:latest --region ${AWS_REGION} || echo 'Lambda not yet created'\n      - echo LangChain service pushed!"
    },
    "artifacts": {
        "type": "NO_ARTIFACTS"
    },
    "environment": {
        "type": "LINUX_CONTAINER",
        "image": "aws/codebuild/amazonlinux2-x86_64-standard:5.0",
        "computeType": "BUILD_GENERAL1_SMALL",
        "privilegedMode": true
    },
    "serviceRole": "${CODEBUILD_ROLE_ARN}",
    "timeoutInMinutes": 30
}
EOF
    
    aws codebuild create-project --cli-input-json file:///tmp/langchain-codebuild.json --region "${AWS_REGION}" 2>/dev/null || \
    aws codebuild update-project --cli-input-json file:///tmp/langchain-codebuild.json --region "${AWS_REGION}"
    
    echo "✅ CodeBuild projects ready"
}

# ===========================================
# Step 3: Lambda関数作成
# ===========================================
create_lambda_function() {
    echo "λ Creating Lambda function..."
    
    FUNCTION_NAME="langchain-service-${ENVIRONMENT}"
    LAMBDA_ROLE_NAME="langchain-lambda-role-${ENVIRONMENT}"
    
    # Lambda実行ロール作成
    if ! aws iam get-role --role-name "${LAMBDA_ROLE_NAME}" 2>/dev/null; then
        echo "Creating Lambda execution role..."
        
        cat > /tmp/lambda-trust.json << 'EOF'
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
        
        aws iam create-role \
            --role-name "${LAMBDA_ROLE_NAME}" \
            --assume-role-policy-document file:///tmp/lambda-trust.json
        
        aws iam attach-role-policy \
            --role-name "${LAMBDA_ROLE_NAME}" \
            --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
        
        # Bedrock権限
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
            --role-name "${LAMBDA_ROLE_NAME}" \
            --policy-name "BedrockInvokePolicy" \
            --policy-document file:///tmp/bedrock-policy.json
        
        echo "Waiting for IAM role propagation..."
        sleep 15
    fi
    
    LAMBDA_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${LAMBDA_ROLE_NAME}"
    ECR_IMAGE_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/langchain-service-${ENVIRONMENT}:latest"
    
    # Lambda関数が存在するか確認
    if aws lambda get-function --function-name "${FUNCTION_NAME}" --region "${AWS_REGION}" 2>/dev/null; then
        echo "Lambda function already exists"
    else
        echo "Creating Lambda function (will update image after CodeBuild)..."
        
        # 初回はプレースホルダー（CodeBuildでイメージプッシュ後に更新）
        # まずCodeBuildでイメージをプッシュする必要がある
        echo "⚠️  Lambda function will be created after first CodeBuild run"
    fi
    
    # Function URL設定
    aws lambda get-function-url-config --function-name "${FUNCTION_NAME}" --region "${AWS_REGION}" 2>/dev/null || \
    echo "Function URL will be created after Lambda function is ready"
    
    echo "✅ Lambda setup prepared"
}

# ===========================================
# Step 4: CodeBuildビルド実行
# ===========================================
run_codebuild() {
    local project_name=$1
    echo "🏗️  Starting CodeBuild: ${project_name}..."
    
    # ソースをS3にアップロード（CodeBuildで使用）
    BUCKET_NAME="codebuild-source-${AWS_ACCOUNT_ID}-${AWS_REGION}"
    
    # バケット作成（存在しない場合）
    if ! aws s3api head-bucket --bucket "${BUCKET_NAME}" 2>/dev/null; then
        if [ "${AWS_REGION}" = "us-east-1" ]; then
            aws s3api create-bucket --bucket "${BUCKET_NAME}" --region "${AWS_REGION}"
        else
            aws s3api create-bucket --bucket "${BUCKET_NAME}" --region "${AWS_REGION}" \
                --create-bucket-configuration LocationConstraint="${AWS_REGION}"
        fi
    fi
    
    # servicesディレクトリをzip化してS3にアップロード
    echo "Uploading source to S3..."
    cd "${PROJECT_ROOT}"
    zip -r /tmp/services-source.zip services/
    aws s3 cp /tmp/services-source.zip "s3://${BUCKET_NAME}/services-source.zip"
    
    # CodeBuildプロジェクトのソースをS3に更新
    aws codebuild update-project \
        --name "${project_name}" \
        --source "type=S3,location=${BUCKET_NAME}/services-source.zip" \
        --region "${AWS_REGION}"
    
    # ビルド開始
    BUILD_ID=$(aws codebuild start-build \
        --project-name "${project_name}" \
        --region "${AWS_REGION}" \
        --query 'build.id' \
        --output text)
    
    echo "Build started: ${BUILD_ID}"
    echo "Waiting for build to complete..."
    
    # ビルド完了を待機
    while true; do
        STATUS=$(aws codebuild batch-get-builds \
            --ids "${BUILD_ID}" \
            --region "${AWS_REGION}" \
            --query 'builds[0].buildStatus' \
            --output text)
        
        if [ "${STATUS}" = "SUCCEEDED" ]; then
            echo "✅ Build succeeded: ${project_name}"
            break
        elif [ "${STATUS}" = "FAILED" ] || [ "${STATUS}" = "FAULT" ] || [ "${STATUS}" = "STOPPED" ]; then
            echo "❌ Build failed: ${project_name} (${STATUS})"
            # ログを表示
            aws codebuild batch-get-builds \
                --ids "${BUILD_ID}" \
                --region "${AWS_REGION}" \
                --query 'builds[0].logs.deepLink' \
                --output text
            exit 1
        fi
        
        echo "  Status: ${STATUS}..."
        sleep 10
    done
}

# ===========================================
# Step 5: Lambda関数作成（イメージプッシュ後）
# ===========================================
create_lambda_with_image() {
    echo "λ Creating/Updating Lambda function with image..."
    
    FUNCTION_NAME="langchain-service-${ENVIRONMENT}"
    LAMBDA_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/langchain-lambda-role-${ENVIRONMENT}"
    ECR_IMAGE_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/langchain-service-${ENVIRONMENT}:latest"
    
    if aws lambda get-function --function-name "${FUNCTION_NAME}" --region "${AWS_REGION}" 2>/dev/null; then
        echo "Updating Lambda function code..."
        aws lambda update-function-code \
            --function-name "${FUNCTION_NAME}" \
            --image-uri "${ECR_IMAGE_URI}" \
            --region "${AWS_REGION}"
    else
        echo "Creating Lambda function..."
        aws lambda create-function \
            --function-name "${FUNCTION_NAME}" \
            --package-type Image \
            --code ImageUri="${ECR_IMAGE_URI}" \
            --role "${LAMBDA_ROLE_ARN}" \
            --timeout 300 \
            --memory-size 1024 \
            --environment "Variables={AWS_REGION=${AWS_REGION},BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0}" \
            --region "${AWS_REGION}"
        
        echo "Waiting for function to be active..."
        aws lambda wait function-active --function-name "${FUNCTION_NAME}" --region "${AWS_REGION}"
        
        # Function URL作成
        echo "Creating Function URL..."
        aws lambda add-permission \
            --function-name "${FUNCTION_NAME}" \
            --statement-id "FunctionURLAllowPublicAccess" \
            --action "lambda:InvokeFunctionUrl" \
            --principal "*" \
            --function-url-auth-type "AWS_IAM" \
            --region "${AWS_REGION}" 2>/dev/null || true
        
        aws lambda create-function-url-config \
            --function-name "${FUNCTION_NAME}" \
            --auth-type AWS_IAM \
            --cors "AllowOrigins=*,AllowMethods=*,AllowHeaders=*" \
            --region "${AWS_REGION}"
    fi
    
    # Function URL取得
    FUNCTION_URL=$(aws lambda get-function-url-config \
        --function-name "${FUNCTION_NAME}" \
        --region "${AWS_REGION}" \
        --query 'FunctionUrl' \
        --output text)
    
    echo "✅ Lambda function ready: ${FUNCTION_URL}"
}

# ===========================================
# Main
# ===========================================
main() {
    # Step 1: ECRリポジトリ作成
    create_ecr_repos
    
    # Step 2: CodeBuildプロジェクト作成
    create_codebuild_projects
    
    # Step 3: Lambda準備
    create_lambda_function
    
    # Step 4: LangChainビルド実行
    run_codebuild "langchain-service-build-${ENVIRONMENT}"
    
    # Step 5: Lambda作成（イメージプッシュ後）
    create_lambda_with_image
    
    # Step 6: AgentCoreビルド実行
    run_codebuild "agentcore-service-build-${ENVIRONMENT}"
    
    echo ""
    echo "================================================"
    echo "✅ Deployment Complete!"
    echo ""
    echo "📦 ECR Images:"
    echo "   AgentCore: ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/agentcore-service-${ENVIRONMENT}:latest"
    echo "   LangChain: ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/langchain-service-${ENVIRONMENT}:latest"
    echo ""
    echo "λ Lambda Function URL:"
    FUNCTION_URL=$(aws lambda get-function-url-config \
        --function-name "langchain-service-${ENVIRONMENT}" \
        --region "${AWS_REGION}" \
        --query 'FunctionUrl' \
        --output text 2>/dev/null || echo "Not available")
    echo "   ${FUNCTION_URL}"
    echo ""
    echo "🔗 Next Steps:"
    echo "   1. AgentCore: Register ECR image in AgentCore Runtime console"
    echo "   2. Update frontend .env with service URLs"
    echo "================================================"
}

main "$@"

