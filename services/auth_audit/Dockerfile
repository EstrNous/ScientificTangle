FROM python:3.12-slim AS deps

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY shared /app/shared
COPY services/auth_audit/pyproject.toml /app/services/auth_audit/pyproject.toml

WORKDIR /app/services/auth_audit

RUN uv sync --no-dev

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/services/auth_audit/.venv/bin:$PATH" \
    PYTHONPATH=/app:/app/services/auth_audit \
    SERVICE_PORT=8001

WORKDIR /app/services/auth_audit

COPY --from=deps /app/services/auth_audit/.venv ./.venv
COPY --from=deps /app/shared /app/shared
COPY infra/__init__.py /app/infra/__init__.py
COPY infra/postgres /app/infra/postgres
COPY services/auth_audit/alembic.ini ./alembic.ini
COPY services/auth_audit/storage ./storage
COPY services/auth_audit/app ./app

RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; response = httpx.get('http://localhost:8001/health'); assert response.status_code == 200"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
