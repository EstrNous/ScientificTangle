from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.api.jobs import router as jobs_router
from app.schemas import ExportJobProcessResponse
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared.web import install_error_handlers, request_id_middleware


def sample_payload() -> dict:
    return {
        "job_id": str(uuid4()),
        "user_id": str(uuid4()),
        "query_run_id": str(uuid4()),
        "format": "markdown",
        "document": {
            "query_run_id": str(uuid4()),
            "question": "demo",
            "role": "researcher",
            "access_scope": ["internal"],
            "dictionary_version_id": None,
            "generated_at": datetime.now(UTC).isoformat(),
            "status": "completed",
            "latency_ms": 1,
            "answer": "demo",
            "confidence": 0.5,
            "sources_count": 0,
            "query_ir": {"raw_query": "demo", "filters": {}},
            "evidence": [],
            "sources": [],
            "graph": {"nodes": [], "links": []},
            "gaps": [],
            "conflicts": [],
            "warnings": [],
            "retrieval_trace": {},
        },
    }


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.middleware("http")(request_id_middleware)
    install_error_handlers(app)
    app.include_router(jobs_router)
    app.state.export_service = AsyncMock()
    app.state.export_service.create_job = AsyncMock(
        return_value=ExportJobProcessResponse(
            job_id=uuid4(),
            status="completed",
            format="markdown",
            content_type="text/markdown",
            content="# demo",
        )
    )
    app.state.internal_service_token = "test-internal-token"
    with TestClient(app) as test_client:
        yield test_client


def test_create_job_requires_internal_token(client: TestClient) -> None:
    response = client.post("/v1/jobs", json=sample_payload())

    assert response.status_code == 401
    assert response.json()["code"] == "authentication_required"


def test_create_job_accepts_internal_token(client: TestClient) -> None:
    response = client.post(
        "/v1/jobs",
        headers={"X-Internal-Service-Token": "test-internal-token"},
        json=sample_payload(),
    )

    assert response.status_code == 201
    assert response.json()["status"] == "completed"
