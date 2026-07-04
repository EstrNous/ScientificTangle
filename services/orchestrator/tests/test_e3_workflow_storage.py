import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from infra.postgres.common.cursor import CursorPage, decode_cursor, encode_cursor
from infra.postgres.orchestrator_db.models import (
    AuditEvent,
    CascadeStatus,
    DocumentDeletionStatus,
    ReviewDecisionStatus,
)
from infra.postgres.orchestrator_db.workflow_storage import WorkflowStorageRepository


class FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False
        self.added: list[object] = []
        self.begin_count = 0

    def add(self, item: object) -> None:
        self.added.append(item)

    async def begin(self):
        self.begin_count += 1
        return _FakeTransaction(self)

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def flush(self) -> None:
        return None

    async def refresh(self, item: object) -> None:
        return None


class _FakeTransaction:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc_type is not None:
            await self._session.rollback()
        else:
            await self._session.commit()
        return False


def test_workflow_repository_records_audit_without_auto_commit() -> None:
    session = FakeSession()
    repo = WorkflowStorageRepository(session)
    event = asyncio.run(
        repo.record_audit_event(
            user_id=uuid4(),
            action="review_decision",
            resource_type="review_candidate",
            resource_id="cand-1",
            details={"status": "approved"},
            request_id="req-1",
            commit=False,
        )
    )
    assert isinstance(event, AuditEvent)
    assert session.committed is False
    assert session.added


def test_cursor_page_truncates_with_next_cursor() -> None:
    created_at = datetime.now(UTC)
    rows = [
        AuditEvent(
            id=uuid4(),
            user_id=uuid4(),
            action="review_decision",
            resource_type="review_candidate",
            resource_id="cand-1",
            details={},
            request_id="req-1",
            created_at=created_at,
        )
        for _ in range(3)
    ]
    page = CursorPage(items=rows[:2], next_cursor=encode_cursor(rows[1].created_at, rows[1].id))
    assert len(page.items) == 2
    assert page.next_cursor is not None
    decoded_created_at, decoded_id = decode_cursor(page.next_cursor)
    assert decoded_id == rows[1].id
    assert decoded_created_at == rows[1].created_at


def test_cascade_and_deletion_status_enums_align() -> None:
    assert DocumentDeletionStatus.PENDING.value == "pending"
    assert CascadeStatus.FAILED.value == "failed"
    assert ReviewDecisionStatus.DEFERRED.value == "deferred"
