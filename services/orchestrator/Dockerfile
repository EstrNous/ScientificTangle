FROM python:3.12-slim AS deps

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY shared /app/shared
COPY services/orchestrator/pyproject.toml /app/services/orchestrator/pyproject.toml

WORKDIR /app/services/orchestrator

RUN uv sync --no-dev

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/services/orchestrator/.venv/bin:$PATH" \
    PYTHONPATH=/app \
    SERVICE_PORT=8002

WORKDIR /app/services/orchestrator

COPY --from=deps /app/services/orchestrator/.venv ./.venv
COPY --from=deps /app/shared /app/shared
COPY services/orchestrator/alembic.ini ./alembic.ini
COPY services/orchestrator/storage ./storage
COPY services/orchestrator/app ./app

RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; response = httpx.get('http://localhost:8002/health'); assert response.status_code == 200"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
