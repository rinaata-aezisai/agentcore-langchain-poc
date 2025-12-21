# Backend Dockerfile - FastAPI + Python 3.11
# AgentCore vs LangChain PoC Backend

FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy backend dependencies
COPY backend/pyproject.toml ./backend/
COPY poc/strands-agents/pyproject.toml ./poc/strands-agents/
COPY poc/langchain/pyproject.toml ./poc/langchain/

# Install pip and dependencies
RUN pip install --upgrade pip

# Install backend dependencies
WORKDIR /app/backend
RUN pip install --no-cache-dir -e .

# Install PoC dependencies (Strands Agents)
WORKDIR /app/poc/strands-agents
RUN pip install --no-cache-dir strands-agents>=1.20.0 || true

# Install PoC dependencies (LangChain)
WORKDIR /app/poc/langchain
RUN pip install --no-cache-dir langchain>=0.3.0 langgraph>=0.2.0 langchain-aws>=0.2.0 langchain-anthropic>=0.3.0

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY backend/src/ ./src/
COPY poc/strands-agents/strands_poc/ ./strands_poc/
COPY poc/langchain/langchain_poc/ ./langchain_poc/

# Add src and poc directories to Python path
ENV PYTHONPATH=/app/src:/app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run with uvicorn
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
