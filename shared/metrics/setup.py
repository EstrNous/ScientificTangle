from __future__ import annotations

import time
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
)
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

if TYPE_CHECKING:
    from fastapi import FastAPI

LATENCY_BUCKETS = (0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10)


def normalize_metric_prefix(service_name: str) -> str:
    return service_name.replace("-", "_").replace(".", "_")


def setup_metrics(app: FastAPI, service_name: str) -> None:
    prefix = normalize_metric_prefix(service_name)
    registry = CollectorRegistry()
    request_counter = Counter(
        f"{prefix}_http_requests_total",
        f"Количество HTTP-запросов к сервису {service_name}",
        ["method", "path", "status"],
        registry=registry,
    )
    request_duration = Histogram(
        f"{prefix}_http_request_duration_seconds",
        f"Длительность HTTP-запросов к сервису {service_name}",
        ["method", "path"],
        buckets=LATENCY_BUCKETS,
        registry=registry,
    )
    app.state.metrics_registry = registry

    @app.middleware("http")
    async def metrics_middleware(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        started_at = time.perf_counter()
        response = await call_next(request)
        route = request.scope.get("route")
        path = getattr(route, "path", "unmatched")
        duration = time.perf_counter() - started_at
        request_counter.labels(request.method, path, str(response.status_code)).inc()
        request_duration.labels(request.method, path).observe(duration)
        return response


def build_metrics_router() -> APIRouter:
    router = APIRouter(tags=["metrics"])

    @router.get("/metrics", response_class=PlainTextResponse)
    async def metrics(request: Request) -> PlainTextResponse:
        content = generate_latest(request.app.state.metrics_registry)
        return PlainTextResponse(content=content, media_type=CONTENT_TYPE_LATEST)

    return router
