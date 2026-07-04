import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

SERVICE_DIR = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = SERVICE_DIR.parents[1]
for import_root in (SERVICE_DIR, REPOSITORY_ROOT):
    import_root_text = str(import_root)
    if import_root_text not in sys.path:
        sys.path.insert(0, import_root_text)

from app.core.config import Settings
from app.core.dependencies import get_chat_service
from app.main import create_app

from shared.contracts import UserRole
from shared.security import AuthenticatedPrincipal


@pytest.fixture
def principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(user_id=uuid4(), role=UserRole.ADMIN, token_id=uuid4())


@pytest.fixture
def client(principal: AuthenticatedPrincipal) -> TestClient:
    app = create_app(Settings(rate_limit_enabled=False))
    app.state.jwt_validator = AsyncMock()
    app.state.jwt_validator.validate = AsyncMock(return_value=principal)

    mock_chat_service = MagicMock()
    mock_chat_service.send_message = AsyncMock(
        return_value={
            "id": str(uuid4()),
            "role": "assistant",
            "content": "ok",
        }
    )
    app.dependency_overrides[get_chat_service] = lambda: mock_chat_service
    return TestClient(app)


def test_send_message_with_json_body_is_not_validation_error(client: TestClient) -> None:
    session_id = uuid4()
    response = client.post(
        f"/chat/sessions/{session_id}/messages",
        headers={"Authorization": "Bearer test-token"},
        json={"content": "nickel"},
    )
    assert response.status_code != 422
    assert response.status_code == 200
    assert response.json()["role"] == "assistant"


def test_send_message_forwards_authorization(client: TestClient) -> None:
    session_id = uuid4()
    client.post(
        f"/chat/sessions/{session_id}/messages",
        headers={"Authorization": "Bearer forwarded-token"},
        json={"content": "nickel"},
    )
    mock_chat_service = client.app.dependency_overrides[get_chat_service]()
    mock_chat_service.send_message.assert_awaited_once()
    call = mock_chat_service.send_message.await_args
    assert call.args[3] == "Bearer forwarded-token"
