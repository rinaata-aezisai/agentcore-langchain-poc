# AgentCore Runtime Dockerfile
# AWS公式要件: ARM64アーキテクチャ推奨
# https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/getting-started-custom.html

FROM python:3.11-slim-bookworm

# 環境変数
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 依存関係インストール
COPY pyproject.toml ./
RUN pip install --no-cache-dir \
    "fastapi>=0.115.0" \
    "uvicorn[standard]>=0.32.0" \
    "pydantic>=2.0.0" \
    "strands-agents>=1.20.0" \
    "boto3>=1.35.0" \
    "httpx>=0.27.0" \
    "python-ulid>=2.0.0"

# アプリケーションコードをコピー
COPY agent.py ./
COPY tools.py ./

# ポート8080を公開（AgentCore Runtime要件）
EXPOSE 8080

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8080/ping').raise_for_status()"

# アプリケーション起動
CMD ["uvicorn", "agent:app", "--host", "0.0.0.0", "--port", "8080"]

