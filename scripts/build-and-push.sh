#!/bin/bash
# ECR Build and Push Script
# Usage: ./scripts/build-and-push.sh <environment> [backend|frontend|all]

set -e

ENVIRONMENT=${1:-dev}
TARGET=${2:-all}
AWS_REGION=${AWS_REGION:-us-east-1}

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Get project root (where this script is located)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "🔧 Project root: ${PROJECT_ROOT}"

# Login to ECR
echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

# Build and push backend
build_backend() {
    echo "🏗️  Building backend..."
    REPO_NAME="agentcore-poc-backend-${ENVIRONMENT}"
    
    # Build from project root with backend Dockerfile
    cd "${PROJECT_ROOT}"
    docker build \
        -f backend/Dockerfile \
        -t $REPO_NAME:latest \
        .
    
    docker tag $REPO_NAME:latest $ECR_REGISTRY/$REPO_NAME:latest
    docker tag $REPO_NAME:latest $ECR_REGISTRY/$REPO_NAME:$(git rev-parse --short HEAD 2>/dev/null || echo "latest")
    
    echo "📤 Pushing backend to ECR..."
    docker push $ECR_REGISTRY/$REPO_NAME:latest
    docker push $ECR_REGISTRY/$REPO_NAME:$(git rev-parse --short HEAD 2>/dev/null || echo "latest")
    
    echo "✅ Backend pushed: $ECR_REGISTRY/$REPO_NAME:latest"
}

# Build and push frontend
build_frontend() {
    echo "🏗️  Building frontend..."
    REPO_NAME="agentcore-poc-frontend-${ENVIRONMENT}"
    
    # ALB DNS name (you may need to pass this or fetch from CloudFormation)
    API_URL=${API_URL:-"http://localhost:8000"}
    
    cd "${PROJECT_ROOT}"
    docker build \
        --build-arg NEXT_PUBLIC_API_URL=$API_URL \
        -t $REPO_NAME:latest \
        ./frontend
    docker tag $REPO_NAME:latest $ECR_REGISTRY/$REPO_NAME:latest
    docker tag $REPO_NAME:latest $ECR_REGISTRY/$REPO_NAME:$(git rev-parse --short HEAD 2>/dev/null || echo "latest")
    
    echo "📤 Pushing frontend to ECR..."
    docker push $ECR_REGISTRY/$REPO_NAME:latest
    docker push $ECR_REGISTRY/$REPO_NAME:$(git rev-parse --short HEAD 2>/dev/null || echo "latest")
    
    echo "✅ Frontend pushed: $ECR_REGISTRY/$REPO_NAME:latest"
}

case $TARGET in
    backend)
        build_backend
        ;;
    frontend)
        build_frontend
        ;;
    all)
        build_backend
        build_frontend
        ;;
    *)
        echo "Usage: $0 <environment> [backend|frontend|all]"
        exit 1
        ;;
esac

echo ""
echo "🎉 Build and push complete!"
echo ""
echo "To update ECS services, run:"
echo "  aws ecs update-service --cluster agentcore-poc-${ENVIRONMENT} --service agentcore-poc-backend-${ENVIRONMENT} --force-new-deployment"
echo "  aws ecs update-service --cluster agentcore-poc-${ENVIRONMENT} --service agentcore-poc-frontend-${ENVIRONMENT} --force-new-deployment"
