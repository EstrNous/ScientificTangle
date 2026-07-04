import asyncio
import hashlib
import os
from uuid import UUID

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_UPLOAD_INTEGRATION") != "1",
    reason="Authenticated upload stack is not enabled",
)


def test_authenticated_upload_is_stored_and_persisted() -> None:
    asyncpg = pytest.importorskip("asyncpg")
    minio_module = pytest.importorskip("minio")
    base_url = os.getenv("UPLOAD_BASE_URL", "http://localhost")
    content = b"scientific-tangle-upload"

    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        login = client.post(
            "/api/auth/login",
            json={
                "identifier": os.getenv("AUTH_SEED_RESEARCHER_USERNAME", "researcher"),
                "password": os.getenv("AUTH_SEED_RESEARCHER_PASSWORD", "researcher"),
            },
        )
        login.raise_for_status()
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}", "X-Request-ID": "integration-upload"}
        upload = client.post(
            "/api/documents/upload",
            files=[("files", ("sample.txt", content, "text/plain"))],
            headers=headers,
        )
        upload.raise_for_status()
        payload = upload.json()
        task_id = payload["id"]
        task = client.get(f"/api/tasks/{task_id}", headers=headers)
        task.raise_for_status()
        assert task.json()["status"] == "pending"
        source = task.json()["report"]["sources"][0]

    minio_client = minio_module.Minio(
        os.getenv("MINIO_TEST_ENDPOINT", "localhost:9000"),
        access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin123"),
        secure=False,
    )
    response = minio_client.get_object("source-files", source["object_key"])
    try:
        stored = response.read()
    finally:
        response.close()
        response.release_conn()
    assert stored == content
    assert source["sha256"] == hashlib.sha256(content).hexdigest()

    async def load_task() -> object:
        connection = await asyncpg.connect(
            os.getenv(
                "POSTGRES_TEST_DSN",
                "postgresql://st_user:st_pass@localhost:5432/scientific_tangle",
            )
        )
        try:
            return await connection.fetchrow(
                "SELECT status, report FROM ingestion_tasks WHERE id = $1",
                UUID(task_id),
            )
        finally:
            await connection.close()

    row = asyncio.run(load_task())
    assert row is not None
    assert row["status"] == "pending"
    assert row["report"]["sources"][0]["sha256"] == source["sha256"]
