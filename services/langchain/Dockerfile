# Lambda Container Image - LangChain Service
# AWS Lambda Python 3.11 ベースイメージ使用

FROM public.ecr.aws/lambda/python:3.11

# 環境変数
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# pipアップグレードと依存関係インストール
# numpy<2.0でプリビルドホイールを使用
COPY pyproject.toml ${LAMBDA_TASK_ROOT}/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir \
    "numpy<2.0" \
    "langchain>=0.3.0" \
    "langchain-aws>=0.2.0" \
    "langchain-core>=0.3.0" \
    "langgraph>=0.2.0" \
    "boto3>=1.35.0" \
    "httpx>=0.27.0" \
    "python-ulid>=2.0.0" \
    "pydantic>=2.0.0"

# アプリケーションコードをコピー
COPY handler.py ${LAMBDA_TASK_ROOT}/
COPY agent.py ${LAMBDA_TASK_ROOT}/
COPY tools.py ${LAMBDA_TASK_ROOT}/

# Lambda handler設定
CMD ["handler.lambda_handler"]

