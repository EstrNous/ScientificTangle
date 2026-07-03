import importlib.util
from pathlib import Path


def load_migration():
    path = Path(__file__).parents[1] / "storage" / "versions" / "0004_close_query_e2e.py"
    spec = importlib.util.spec_from_file_location("query_migration_0004", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OperationRecorder:
    def __init__(self) -> None:
        self.added = []
        self.altered = []
        self.dropped = []
        self.executed = []

    def add_column(self, table, column):
        self.added.append((table, column.name))

    def alter_column(self, table, column, **values):
        self.altered.append((table, column, values))

    def drop_column(self, table, column):
        self.dropped.append((table, column))

    def execute(self, statement):
        self.executed.append(statement)


def test_query_migration_upgrade_and_downgrade(monkeypatch) -> None:
    migration = load_migration()
    recorder = OperationRecorder()
    monkeypatch.setattr(migration, "op", recorder)

    migration.upgrade()

    assert ("query_runs", "raw_question") in recorder.added
    assert ("query_runs", "evidence_bundle") in recorder.added
    assert ("query_runs", "updated_at") in recorder.added
    assert len(recorder.altered) == 2

    migration.downgrade()

    assert ("query_runs", "raw_question") in recorder.dropped
    assert ("query_runs", "updated_at") in recorder.dropped
