import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from infra.postgres.orchestrator_db.models import ExportArtifact, ExportJob, ExportJobStatus
from infra.postgres.orchestrator_db.product_events_storage import (
    ExportArtifactInput,
    ProductEventsStorageRepository,
)
from infra.postgres.orchestrator_db.repository import QueryRunRepository
from shared.contracts import ExportPayload, QueryRunStatus


class FakeSession:
    def __init__(self) -> None:
        self.begin_count = 0
        self.committed = False
        self.added: list[object] = []
        self._objects: dict[object, object] = {}

    def add(self, item: object) -> None:
        self.added.append(item)
        if hasattr(item, "id"):
            self._objects[item.id] = item

    async def begin(self):
        self.begin_count += 1
        return _FakeTransaction(self)

    async def commit(self) -> None:
        self.committed = True

    async def refresh(self, item: object) -> None:
        return None

    async def get(self, model: type, key: object) -> object | None:
        return self._objects.get(key)


class _FakeTransaction:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc_type is not None:
            return False
        await self._session.commit()
        return False


def test_attach_export_artifacts_does_not_begin_nested_transaction() -> None:
    session = FakeSession()
    job_id = uuid4()
    job = ExportJob(
        id=job_id,
        user_id=uuid4(),
        query_run_id=uuid4(),
        format="markdown",
        status=ExportJobStatus.PROCESSING.value,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session._objects[job_id] = job
    repo = ProductEventsStorageRepository(session)

    rows = asyncio.run(
        repo.attach_export_artifacts(
            job_id,
            [
                ExportArtifactInput(
                    artifact_kind="report",
                    storage_key="exports/demo/report.md",
                    content_type="text/markdown",
                    file_url="/api/export/jobs/demo/artifact",
                )
            ],
            mark_completed=False,
        )
    )

    assert session.begin_count == 0
    assert len(rows) == 1
    assert isinstance(rows[0], ExportArtifact)
    assert session.committed is False


def test_attach_export_artifacts_commits_when_mark_completed() -> None:
    session = FakeSession()
    job_id = uuid4()
    job = ExportJob(
        id=job_id,
        user_id=uuid4(),
        query_run_id=uuid4(),
        format="markdown",
        status=ExportJobStatus.PROCESSING.value,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session._objects[job_id] = job
    repo = ProductEventsStorageRepository(session)

    asyncio.run(
        repo.attach_export_artifacts(
            job_id,
            [
                ExportArtifactInput(
                    artifact_kind="report",
                    storage_key="exports/demo/report.md",
                    content_type="text/markdown",
                    file_url="/api/export/jobs/demo/artifact",
                )
            ],
            mark_completed=True,
        )
    )

    assert session.begin_count == 0
    assert session.committed is True
    assert job.status == ExportJobStatus.COMPLETED.value


def test_complete_export_with_artifacts_without_nested_transaction() -> None:
    session = FakeSession()
    job_id = uuid4()
    job = ExportJob(
        id=job_id,
        user_id=uuid4(),
        query_run_id=uuid4(),
        format="json",
        status=ExportJobStatus.PROCESSING.value,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session._objects[job_id] = job
    repository = QueryRunRepository(session)
    payload = ExportPayload(
        export_job_id=job_id,
        query_run_id=job.query_run_id,
        format="json",
        status=QueryRunStatus.COMPLETED,
        content_type="application/json",
        content={},
        file_url="/api/export/jobs/demo/artifact",
        warnings=[],
        format_status=[],
        generated_at=datetime.now(UTC),
    )
    artifacts = [
        ExportArtifactInput(
            artifact_kind="report",
            storage_key="exports/demo/report.json",
            content_type="application/json",
            file_url="/api/export/jobs/demo/artifact",
        )
    ]

    result = asyncio.run(repository.complete_export_with_artifacts(job, payload, artifacts))

    assert session.begin_count == 0
    assert session.committed is True
    assert result.status == ExportJobStatus.COMPLETED.value
    assert any(isinstance(item, ExportArtifact) for item in session.added)
