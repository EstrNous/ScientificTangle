import pytest

from app.service.storage import ArtifactStorage


@pytest.fixture(autouse=True)
def stub_artifact_storage_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    async def ensure_bucket(self) -> None:
        return None

    monkeypatch.setattr(ArtifactStorage, "ensure_bucket", ensure_bucket)
