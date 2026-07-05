import importlib.util
from pathlib import Path


def load_migration():
    path = Path(__file__).parents[1] / "storage" / "versions" / "0006_reconcile_runtime_schema.py"
    spec = importlib.util.spec_from_file_location("query_migration_0006", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OperationRecorder:
    def __init__(self) -> None:
        self.added = []
        self.altered = []
        self.dropped = []
        self.executed = []
        self.created_tables = []
        self.created_indexes = []

    def add_column(self, table, column):
        self.added.append((table, column.name))

    def alter_column(self, table, column, **values):
        self.altered.append((table, column, values))

    def drop_column(self, table, column):
        self.dropped.append((table, column))

    def execute(self, statement):
        self.executed.append(statement)

    def create_table(self, table, *columns, **kwargs):
        self.created_tables.append(table)

    def create_index(self, name, table_name, columns):
        self.created_indexes.append((name, table_name, tuple(columns)))


def test_query_migration_reconciles_canonical_runtime_schema(monkeypatch) -> None:
    migration = load_migration()
    recorder = OperationRecorder()
    monkeypatch.setattr(migration, "op", recorder)
    monkeypatch.setattr(
        migration,
        "table_names",
        lambda: {"query_runs", "export_jobs", "roles", "permissions", "role_permissions", "audit_events", "indexed_documents"},
    )
    monkeypatch.setattr(
        migration,
        "column_names",
        lambda table_name: {
            "query_runs": {
                "id",
                "user_id",
                "status",
                "raw_query",
                "query_ir",
                "retrieval_trace",
                "latency_ms",
                "created_at",
                "evidence_bundle",
                "graph_subgraph",
                "warnings",
                "error_code",
                "request_id",
                "answer_payload",
            },
            "export_jobs": {"id", "user_id", "status", "format", "file_url", "created_at", "updated_at"},
        }.get(table_name, set()),
    )
    monkeypatch.setattr(
        migration,
        "index_names",
        lambda table_name: set(),
    )

    migration.upgrade()

    assert ("query_runs", "raw_question") in recorder.added
    assert ("query_runs", "answer") in recorder.added
    assert ("query_runs", "updated_at") in recorder.added
    assert ("export_jobs", "query_run_id") in recorder.added
    assert ("export_jobs", "payload") in recorder.added
    assert len(recorder.altered) == 2
    assert any("raw_question = COALESCE(raw_question, raw_query" in statement for statement in recorder.executed)
    assert any("answer = COALESCE(answer, answer_payload)" in statement for statement in recorder.executed)


def test_query_migration_reconciles_legacy_close_query_schema(monkeypatch) -> None:
    migration = load_migration()
    recorder = OperationRecorder()
    monkeypatch.setattr(migration, "op", recorder)
    monkeypatch.setattr(
        migration,
        "table_names",
        lambda: {"query_runs", "export_jobs"},
    )
    monkeypatch.setattr(
        migration,
        "column_names",
        lambda table_name: {
            "query_runs": {
                "id",
                "user_id",
                "status",
                "raw_question",
                "query_ir",
                "retrieval_trace",
                "latency_ms",
                "created_at",
                "evidence_bundle",
                "answer",
                "graph_subgraph",
                "warnings",
                "error_code",
                "error_message",
                "request_id",
                "updated_at",
            },
            "export_jobs": {"id", "user_id", "status", "format", "file_url", "created_at", "updated_at"},
        }.get(table_name, set()),
    )
    monkeypatch.setattr(
        migration,
        "index_names",
        lambda table_name: set(),
    )

    migration.upgrade()

    assert "roles" in recorder.created_tables
    assert "permissions" in recorder.created_tables
    assert "role_permissions" in recorder.created_tables
    assert "audit_events" in recorder.created_tables
    assert "indexed_documents" in recorder.created_tables
    assert ("export_jobs", "query_run_id") in recorder.added
    assert ("ix_export_jobs_query_run_id", "export_jobs", ("query_run_id",)) in recorder.created_indexes
