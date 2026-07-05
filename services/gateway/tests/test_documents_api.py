from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.core.config import Settings
from app.core.dependencies import get_gateway_service
from app.main import create_app
from fastapi.testclient import TestClient

from shared.contracts import UserRole
from shared.security import AuthenticatedPrincipal


@pytest.fixture
def client() -> TestClient:
    principal = AuthenticatedPrincipal(user_id=uuid4(), role=UserRole.RESEARCHER, token_id=uuid4())
    app = create_app(Settings(rate_limit_enabled=False))
    app.state.jwt_validator = AsyncMock()
    app.state.jwt_validator.validate = AsyncMock(return_value=principal)

    mock_service = AsyncMock()
    now = datetime.now(UTC).isoformat()
    task_id = uuid4()
    mock_service.upload_documents = AsyncMock(
        return_value={
            "id": str(task_id),
            "status": "pending",
            "report": None,
            "error_message": None,
            "created_at": now,
            "updated_at": now,
        }
    )
    app.dependency_overrides[get_gateway_service] = lambda: mock_service
    return TestClient(app)


def test_upload_documents_accepts_multipart(client: TestClient) -> None:
    response = client.post(
        "/documents/upload",
        headers={"Authorization": "Bearer test-token"},
        files=[("files", ("sample.txt", b"data", "text/plain"))],
    )
    assert response.status_code == 202
    assert response.json()["status"] == "pending"


def test_delete_reserved_upload_segment_returns_not_found(client: TestClient) -> None:
    response = client.delete(
        "/documents/upload",
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 404
    assert response.json()["code"] == "document_not_found"


def test_post_on_delete_document_route_returns_method_not_allowed(client: TestClient) -> None:
    response = client.post(
        "/documents/doc-1",
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 405
    assert response.json()["code"] == "method_not_allowed"


def test_get_document_returns_catalog_item(client: TestClient) -> None:
    mock_service = client.app.dependency_overrides[get_gateway_service]()
    mock_service.get_document = AsyncMock(
        return_value={
            "document_id": "doc-1",
            "title": "sample.pdf",
            "source_path": "sample.pdf",
            "source_type": "pdf",
            "status": "completed",
            "access_level": "internal",
            "source_spans_count": 1,
            "indexed_points_count": 1,
            "created_at": datetime.now(UTC).isoformat(),
            "warnings": [],
        }
    )
    response = client.get(
        "/documents/doc-1",
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 200
    assert response.json()["document_id"] == "doc-1"
