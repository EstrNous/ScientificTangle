from pathlib import Path

from scripts.seed_corpus_batches import (
    CorpusFile,
    batch_already_done,
    build_batches,
    collect_corpus_files,
    completed_paths,
    should_include_file,
)


def test_should_include_file_filters_service_files(tmp_path: Path) -> None:
    included = tmp_path / "report.pdf"
    manifest = tmp_path / "manifest.json"
    hidden = tmp_path / ".hidden.pdf"
    temp = tmp_path / "draft.tmp"
    included.write_bytes(b"x")
    manifest.write_bytes(b"{}")
    hidden.write_bytes(b"x")
    temp.write_bytes(b"x")
    assert should_include_file(included)
    assert not should_include_file(manifest)
    assert not should_include_file(hidden)
    assert not should_include_file(temp)


def test_collect_corpus_files_skips_manifest(tmp_path: Path) -> None:
    nested = tmp_path / "docs"
    nested.mkdir()
    (nested / "a.pdf").write_bytes(b"abc")
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    files = collect_corpus_files(tmp_path)
    assert len(files) == 1
    assert files[0].relative_path == "docs/a.pdf"
    assert files[0].size_bytes == 3


def test_build_batches_groups_by_bytes() -> None:
    files = [
        CorpusFile(path=Path("a"), relative_path="a", size_bytes=50),
        CorpusFile(path=Path("b"), relative_path="b", size_bytes=40),
        CorpusFile(path=Path("c"), relative_path="c", size_bytes=30),
    ]
    batches = build_batches(files, max_batch_bytes=80)
    assert len(batches) == 2
    assert [item.relative_path for item in batches[0]] == ["a"]
    assert [item.relative_path for item in batches[1]] == ["b", "c"]


def test_build_batches_single_large_file_gets_own_batch() -> None:
    files = [CorpusFile(path=Path("big"), relative_path="big", size_bytes=150)]
    batches = build_batches(files, max_batch_bytes=80)
    assert len(batches) == 1
    assert batches[0][0].relative_path == "big"


def test_completed_paths_from_state() -> None:
    state = {
        "completed_file_paths": ["a.pdf"],
        "batches": [
            {"status": "completed", "files": ["b.pdf"]},
            {"status": "failed", "files": ["c.pdf"]},
        ],
    }
    assert completed_paths(state) == {"a.pdf", "b.pdf"}


def test_batch_already_done_on_resume() -> None:
    state = {
        "batches": [
            {"status": "completed", "files": ["a.pdf", "b.pdf"]},
        ],
    }
    assert batch_already_done(state, ["a.pdf", "b.pdf"], resume=True)
    assert not batch_already_done(state, ["a.pdf"], resume=True)
    assert not batch_already_done(state, ["a.pdf", "b.pdf"], resume=False)
