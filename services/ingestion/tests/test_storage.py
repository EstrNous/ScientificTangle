import asyncio
from io import BytesIO
from uuid import uuid4

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.service.storage import InvalidUploadError, SourceStorage, StorageOperationError


class FakeMinio:
    def __init__(self, fail_on_put: int | None = None) -> None:
        self.objects: dict[str, bytes] = {}
        self.put_count = 0
        self.fail_on_put = fail_on_put

    def bucket_exists(self, bucket: str) -> bool:
        return True

    def make_bucket(self, bucket: str) -> None:
        return None

    def put_object(
        self,
        bucket: str,
        object_key: str,
        data: BytesIO,
        length: int,
        content_type: str,
    ) -> None:
        self.put_count += 1
        if self.fail_on_put == self.put_count:
            raise RuntimeError("storage failure")
        self.objects[object_key] = data.read(length)

    def remove_object(self, bucket: str, object_key: str) -> None:
        self.objects.pop(object_key, None)


def upload(filename: str, content: bytes, content_type: str = "text/plain") -> UploadFile:
    return UploadFile(
        file=BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


def test_store_records_checksum_and_sanitizes_object_key() -> None:
    client = FakeMinio()
    storage = SourceStorage(client, "source-files", 1024)
    user_id = uuid4()
    task_id = uuid4()

    sources = asyncio.run(
        storage.store(user_id, task_id, [upload("../../данные.csv", b"value", "text/csv")])
    )

    assert len(sources) == 1
    assert sources[0].original_filename == "данные.csv"
    assert sources[0].object_key.startswith(f"uploads/{user_id}/{task_id}/")
    assert ".." not in sources[0].object_key
    assert sources[0].size_bytes == 5
    assert len(sources[0].sha256) == 64
    assert client.objects[sources[0].object_key] == b"value"


def test_empty_and_oversized_uploads_are_rejected() -> None:
    storage = SourceStorage(FakeMinio(), "source-files", 3)

    with pytest.raises(InvalidUploadError) as empty_error:
        asyncio.run(storage.store(uuid4(), uuid4(), [upload("empty.txt", b"")]))
    assert empty_error.value.code == "empty_file"

    with pytest.raises(InvalidUploadError) as size_error:
        asyncio.run(storage.store(uuid4(), uuid4(), [upload("large.txt", b"1234")]))
    assert size_error.value.code == "upload_too_large"


def test_partial_failure_removes_previously_stored_objects() -> None:
    client = FakeMinio(fail_on_put=2)
    storage = SourceStorage(client, "source-files", 1024)

    with pytest.raises(StorageOperationError):
        asyncio.run(
            storage.store(
                uuid4(),
                uuid4(),
                [upload("one.txt", b"one"), upload("two.txt", b"two")],
            )
        )

    assert client.objects == {}
