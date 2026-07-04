FROM python:3.12-slim AS deps

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY shared /app/shared
COPY services/gateway/pyproject.toml /app/services/gateway/pyproject.toml

WORKDIR /app/services/gateway

RUN uv sync --no-dev

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/services/gateway/.venv/bin:$PATH" \
    PYTHONPATH=/app:/app/services/gateway \
    SERVICE_PORT=8000

WORKDIR /app/services/gateway

COPY --from=deps /app/services/gateway/.venv ./.venv
COPY --from=deps /app/shared /app/shared
COPY infra/__init__.py /app/infra/__init__.py
COPY infra/postgres/__init__.py /app/infra/postgres/__init__.py
COPY infra/postgres/chat_ui_db /app/infra/postgres/chat_ui_db
COPY infra/postgres/notification_db /app/infra/postgres/notification_db
COPY services/gateway/app ./app

RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; response = httpx.get('http://localhost:8000/health'); assert response.status_code == 200"

CMD ["sh", "-c", "cd /app/infra/postgres/chat_ui_db && alembic upgrade head && cd /app/infra/postgres/notification_db && alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
