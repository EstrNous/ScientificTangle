from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from scripts.ensure_cloud_corpus import indexing_complete, pending_paths
from scripts.seed_corpus_batches import save_state

ROOT = Path(__file__).resolve().parents[2]


def _env_without_pythonpath() -> dict[str, str]:
    return {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}


def test_ensure_cloud_corpus_help_without_pythonpath() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/ensure_cloud_corpus.py", "--help"],
        cwd=ROOT,
        env=_env_without_pythonpath(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_seed_corpus_batches_help_without_pythonpath() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/seed_corpus_batches.py", "--help"],
        cwd=ROOT,
        env=_env_without_pythonpath(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_seed_demo_help_without_pythonpath() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/seed_demo.py", "--help"],
        cwd=ROOT,
        env=_env_without_pythonpath(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


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
