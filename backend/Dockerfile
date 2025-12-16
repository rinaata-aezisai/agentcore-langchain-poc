FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir hatch

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

COPY src/ ./src/

ENV PYTHONPATH=/app/src
EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]


