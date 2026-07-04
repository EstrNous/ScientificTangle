FROM python:3.12-slim AS deps

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY shared /app/shared
COPY services/notification/pyproject.toml /app/services/notification/pyproject.toml

WORKDIR /app/services/notification

RUN uv sync --no-dev

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/services/notification/.venv/bin:$PATH" \
    PYTHONPATH=/app:/app/services/notification \
    SERVICE_PORT=8008

WORKDIR /app/services/notification

COPY --from=deps /app/services/notification/.venv ./.venv
COPY --from=deps /app/shared /app/shared
COPY infra/__init__.py /app/infra/__init__.py
COPY infra/postgres /app/infra/postgres
COPY services/notification/app ./app

RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8008

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; response = httpx.get('http://localhost:8008/health'); assert response.status_code == 200"

CMD ["sh", "-c", "cd /app/infra/postgres/notification_db && alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8008"]
