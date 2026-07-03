import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture(autouse=True)
def mock_neo4j_driver(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    driver = MagicMock()
    driver.close = AsyncMock()
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    session.run = AsyncMock()
    session.execute_write = AsyncMock(return_value=1)
    driver.session.return_value = session
    monkeypatch.setattr("adapters.driver.create_driver", lambda *args, **kwargs: driver)
    monkeypatch.setattr("adapters.driver.verify_connectivity", AsyncMock(return_value=True))
    monkeypatch.setattr("adapters.schema.seed_schema_registry", AsyncMock(return_value=MagicMock()))
    return driver
