import os

import pytest


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if os.getenv("RUN_MODEL_TESTS") == "1":
        return
    skip = pytest.mark.skip(reason="Model tests are opt-in: set RUN_MODEL_TESTS=1")
    for item in items:
        item.add_marker(skip)
