from __future__ import annotations

import json
from pathlib import Path

from scripts.ensure_cloud_corpus import indexing_complete, pending_paths
from scripts.seed_corpus_batches import save_state


def test_indexing_complete_when_state_matches(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    sample = corpus_root / "a.txt"
    sample.write_text("hello", encoding="utf-8")
    state_file = tmp_path / "state.json"
    save_state(
        state_file,
        {
            "batches": [{"status": "completed", "files": ["a.txt"]}],
            "completed_file_paths": ["a.txt"],
            "skipped_oversized": [],
        },
    )
    assert indexing_complete(corpus_root, state_file, indexed_count=100, min_indexed=50, max_file_bytes=10_000_000)
    assert pending_paths(corpus_root, state_file, 10_000_000) == set()


def test_indexing_not_complete_when_pending_files(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    (corpus_root / "a.txt").write_text("hello", encoding="utf-8")
    (corpus_root / "b.txt").write_text("world", encoding="utf-8")
    state_file = tmp_path / "state.json"
    save_state(
        state_file,
        {
            "batches": [{"status": "completed", "files": ["a.txt"]}],
            "completed_file_paths": ["a.txt"],
            "skipped_oversized": [],
        },
    )
    assert not indexing_complete(corpus_root, state_file, indexed_count=100, min_indexed=50, max_file_bytes=10_000_000)
    assert pending_paths(corpus_root, state_file, 10_000_000) == {"b.txt"}
