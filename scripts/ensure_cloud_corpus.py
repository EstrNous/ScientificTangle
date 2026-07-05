from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.seed_corpus_batches import (  # noqa: E402
    DEFAULT_CORPUS_DIR,
    DEFAULT_MAX_FILE_BYTES,
    DEFAULT_STATE_FILE,
    collect_corpus_files,
    completed_paths,
    load_state,
    scan_manifest,
)

DEFAULT_MIN_INDEXED = 50


def ingestible_paths(corpus_root: Path, max_file_bytes: int) -> set[str]:
    return {
        item.relative_path
        for item in collect_corpus_files(corpus_root)
        if item.size_bytes <= max_file_bytes
    }


def corpus_has_local_files(corpus_root: Path) -> bool:
    if not corpus_root.is_dir():
        return False
    try:
        return bool(ingestible_paths(corpus_root, DEFAULT_MAX_FILE_BYTES))
    except SystemExit:
        return False


def pending_paths(corpus_root: Path, state_file: Path, max_file_bytes: int) -> set[str]:
    try:
        all_paths = ingestible_paths(corpus_root, max_file_bytes)
    except SystemExit:
        return set()
    if not all_paths:
        return set()
    done = completed_paths(load_state(state_file))
    return all_paths - done


def indexing_complete(
    corpus_root: Path,
    state_file: Path,
    indexed_count: int,
    min_indexed: int,
    max_file_bytes: int,
) -> bool:
    if indexed_count < min_indexed:
        return False
    if not corpus_has_local_files(corpus_root):
        return False
    return len(pending_paths(corpus_root, state_file, max_file_bytes)) == 0


def download_corpus(corpus_root: Path) -> None:
    subprocess.run(
        [sys.executable, "eval/yandex_disk_corpus.py", "--output-dir", str(corpus_root)],
        check=True,
        cwd=ROOT,
    )


def run_batch_seed(
    api_url: str,
    corpus_dir: Path,
    state_file: Path,
    username: str,
    password: str,
    skip_dictionary: bool,
) -> None:
    command = [
        sys.executable,
        "scripts/seed_corpus_batches.py",
        "--api-url",
        api_url,
        "--corpus-dir",
        str(corpus_dir),
        "--state-file",
        str(state_file),
        "--username",
        username,
        "--password",
        password,
        "--resume",
        "--stop-on-failure",
    ]
    if skip_dictionary:
        command.append("--skip-dictionary")
    result = subprocess.run(command, check=False, cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-dir", default=DEFAULT_CORPUS_DIR)
    parser.add_argument("--state-file", default=DEFAULT_STATE_FILE)
    parser.add_argument("--api-url", default="http://127.0.0.1/api")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="admin")
    parser.add_argument("--indexed-count", type=int, default=0)
    parser.add_argument("--min-indexed", type=int, default=DEFAULT_MIN_INDEXED)
    parser.add_argument("--max-file-bytes", type=int, default=DEFAULT_MAX_FILE_BYTES)
    parser.add_argument("--skip-dictionary", action="store_true")
    parser.add_argument("--skip-download", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    corpus_root = Path(args.corpus_dir)
    state_file = Path(args.state_file)
    manifest = scan_manifest(corpus_root) if corpus_root.is_dir() else {"manifest_exists": False}

    if indexing_complete(
        corpus_root,
        state_file,
        args.indexed_count,
        args.min_indexed,
        args.max_file_bytes,
    ):
        print(
            json.dumps(
                {
                    "action": "skip",
                    "reason": "corpus_already_indexed",
                    "indexed_count": args.indexed_count,
                    "corpus_dir": str(corpus_root),
                    "manifest": manifest,
                },
                ensure_ascii=False,
            )
        )
        return 0

    if not args.skip_download and not corpus_has_local_files(corpus_root):
        print(json.dumps({"action": "download", "corpus_dir": str(corpus_root)}, ensure_ascii=False))
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "httpx"],
            check=True,
            cwd=ROOT,
        )
        download_corpus(corpus_root)
    elif corpus_has_local_files(corpus_root):
        print(
            json.dumps(
                {
                    "action": "reuse_local_corpus",
                    "corpus_dir": str(corpus_root),
                    "pending_files": len(pending_paths(corpus_root, state_file, args.max_file_bytes)),
                    "manifest": manifest,
                },
                ensure_ascii=False,
            )
        )

    print(json.dumps({"action": "batch_index", "corpus_dir": str(corpus_root)}, ensure_ascii=False))
    run_batch_seed(
        args.api_url,
        corpus_root,
        state_file,
        args.username,
        args.password,
        args.skip_dictionary,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
