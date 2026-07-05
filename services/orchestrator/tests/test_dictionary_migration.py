from pathlib import Path


def test_dictionary_migration_adds_pinning_columns() -> None:
    source = (
        Path(__file__).parents[1]
        / "storage"
        / "versions"
        / "0007_add_dictionary_pinning.py"
    ).read_text(encoding="utf-8")
    assert 'revision: str = "0007"' in source
    assert 'down_revision: str | None = "0006"' in source
    assert '"task_kind"' in source
    assert source.count('"dictionary_version_id"') >= 2
