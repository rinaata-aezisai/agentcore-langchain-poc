#!/bin/bash
# Deploy Infrastructure Script
# Usage: ./scripts/deploy-infra.sh <environment>

set -e

ENVIRONMENT=${1:-dev}
AWS_REGION=${AWS_REGION:-us-east-1}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CDK_DIR="${PROJECT_ROOT}/infra/cdk"

echo "🚀 Deploying infrastructure for environment: ${ENVIRONMENT}"
echo "📁 CDK directory: ${CDK_DIR}"

# Change to CDK directory
cd "${CDK_DIR}"

# Install dependencies
echo "📦 Installing CDK dependencies..."
npm install

# Bootstrap if needed (first time only)
echo "🔧 Checking CDK bootstrap..."
npx cdk bootstrap --context environment=${ENVIRONMENT} 2>/dev/null || true

# Deploy all stacks
echo "🏗️  Deploying CDK stacks..."
npx cdk deploy --all --context environment=${ENVIRONMENT} --require-approval never

echo ""
echo "✅ Infrastructure deployment complete!"
echo ""
echo "Next steps:"
echo "1. Build and push Docker images: ./scripts/build-and-push.sh ${ENVIRONMENT}"
echo "2. Update ECS services if already deployed"

