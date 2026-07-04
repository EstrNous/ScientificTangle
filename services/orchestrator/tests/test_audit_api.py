import asyncio
from uuid import uuid4

import pytest
from app.api.audit import list_audit_events, require_admin

from shared.contracts import AuditEvent, UserRole
from shared.security import AuthenticatedPrincipal
from shared.web import ServiceError


def test_require_admin_rejects_non_admin() -> None:
    principal = AuthenticatedPrincipal(user_id=uuid4(), role=UserRole.RESEARCHER, token_id=uuid4())
    with pytest.raises(ServiceError) as exc:
        require_admin(principal)
    assert exc.value.status_code == 403


def test_require_admin_allows_admin() -> None:
    principal = AuthenticatedPrincipal(user_id=uuid4(), role=UserRole.ADMIN, token_id=uuid4())
    assert require_admin(principal) is principal


class FakeAuditService:
    def __init__(self) -> None:
        self.last_kwargs: dict | None = None

    async def list_audit_events(self, **kwargs):
        self.last_kwargs = kwargs
        return [
            AuditEvent(
                id="event-1",
                user_id=str(uuid4()),
                user=str(uuid4()),
                action="source_viewed",
                resource_type="source_span",
                resource_id="span-1",
                details={},
                request_id="req-1",
                timestamp="2026-07-04T00:00:00Z",
            )
        ]


def test_list_audit_events_delegates_to_service() -> None:
    service = FakeAuditService()
    admin_id = uuid4()
    principal = AuthenticatedPrincipal(user_id=admin_id, role=UserRole.ADMIN, token_id=uuid4())

    events = asyncio.run(
        list_audit_events(
            principal=principal,
            service=service,
            action="source_viewed",
            user_id=admin_id,
            limit=50,
            offset=5,
        )
    )

    assert service.last_kwargs == {
        "limit": 50,
        "offset": 5,
        "action": "source_viewed",
        "user_id": admin_id,
    }
    assert events[0].action == "source_viewed"


def test_audit_routes_are_in_openapi() -> None:
    from app.main import app

    paths = app.openapi()["paths"]
    assert "/audit/events" in paths
    assert paths["/audit/events"]["get"]["responses"]["200"]