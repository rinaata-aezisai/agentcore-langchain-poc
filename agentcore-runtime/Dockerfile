# AgentCore Runtime Dockerfile
# AWS公式要件: ARM64アーキテクチャ必須
# https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/getting-started-custom.html

FROM --platform=linux/arm64 python:3.11-slim-bookworm

# 環境変数
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 依存関係をインストール
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# アプリケーションコードをコピー
COPY agent.py ./

# ポート8080を公開（AgentCore Runtime要件）
EXPOSE 8080

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8080/ping').raise_for_status()"

# アプリケーション起動
CMD ["uvicorn", "agent:app", "--host", "0.0.0.0", "--port", "8080"]
