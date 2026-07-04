from __future__ import annotations

import argparse
import asyncio
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from scripts._seed_common import (
    DEFAULT_API_URL,
    DEFAULT_CORPUS_DIR,
    DEFAULT_DICTIONARY_VERSION,
    edge_tls_verify,
    ensure_dictionary,
    login,
    wait_task,
)

DEFAULT_MAX_BATCH_BYTES = 80_000_000
DEFAULT_MAX_FILE_BYTES = 200 * 1024 * 1024
DEFAULT_STATE_FILE = ".seed_corpus_batches_state.json"
DEFAULT_POLL_TIMEOUT_SECONDS = 900
EXCLUDED_NAMES = {"manifest.json"}
EXCLUDED_SUFFIXES = {".tmp"}


@dataclass(frozen=True)
class CorpusFile:
    path: Path
    relative_path: str
    size_bytes: int


def should_include_file(path: Path) -> bool:
    if path.name in EXCLUDED_NAMES:
        return False
    if path.name.startswith("."):
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    return path.is_file()


def collect_corpus_files(corpus_root: Path) -> list[CorpusFile]:
    files = [
        CorpusFile(
            path=path,
            relative_path=path.relative_to(corpus_root).as_posix(),
            size_bytes=path.stat().st_size,
        )
        for path in sorted(corpus_root.rglob("*"))
        if should_include_file(path)
    ]
    if not files:
        raise SystemExit(f"Corpus files are missing in {corpus_root}")
    return files


def scan_manifest(corpus_root: Path) -> dict[str, Any]:
    manifest_path = corpus_root / "manifest.json"
    if not manifest_path.exists():
        return {"manifest_exists": False}
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_files = data.get("files", [])
    manifest_size = sum(int(item.get("size") or 0) for item in manifest_files)
    return {
        "manifest_exists": True,
        "manifest_files": len(manifest_files),
        "manifest_size_bytes": manifest_size,
        "source": data.get("source"),
    }


def build_batches(
    files: list[CorpusFile],
    max_batch_bytes: int,
) -> list[list[CorpusFile]]:
    batches: list[list[CorpusFile]] = []
    current: list[CorpusFile] = []
    current_bytes = 0
    for item in files:
        if current and current_bytes + item.size_bytes > max_batch_bytes:
            batches.append(current)
            current = []
            current_bytes = 0
        current.append(item)
        current_bytes += item.size_bytes
    if current:
        batches.append(current)
    return batches


def load_state(state_file: Path) -> dict[str, Any]:
    if not state_file.exists():
        return {"batches": [], "skipped_oversized": [], "completed_file_paths": []}
    return json.loads(state_file.read_text(encoding="utf-8"))


def save_state(state_file: Path, state: dict[str, Any]) -> None:
    state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def completed_paths(state: dict[str, Any]) -> set[str]:
    paths: set[str] = set(state.get("completed_file_paths", []))
    for batch in state.get("batches", []):
        if batch.get("status") == "completed":
            paths.update(batch.get("files", []))
    return paths


def batch_already_done(state: dict[str, Any], batch_files: list[str], resume: bool) -> bool:
    if not resume:
        return False
    for batch in state.get("batches", []):
        if batch.get("status") == "completed" and batch.get("files") == batch_files:
            return True
    return False


def extract_metrics(task_payload: dict[str, Any]) -> dict[str, Any]:
    report = task_payload.get("report") or {}
    return {
        "documents_count": report.get("documents_count", 0),
        "source_spans_count": report.get("source_spans_count", 0),
        "indexed_points_count": report.get("indexed_points_count", 0),
        "warnings": list(report.get("warnings") or []),
    }


def format_batch_log(
    batch_number: int,
    batch_files: list[CorpusFile],
    task_id: str | None,
    status: str,
    metrics: dict[str, Any],
    error_message: str | None = None,
) -> str:
    total_bytes = sum(item.size_bytes for item in batch_files)
    parts = [
        f"batch={batch_number}",
        f"files={len(batch_files)}",
        f"bytes={total_bytes}",
        f"task_id={task_id or '-'}",
        f"status={status}",
        f"documents_count={metrics.get('documents_count', 0)}",
        f"source_spans_count={metrics.get('source_spans_count', 0)}",
        f"indexed_points_count={metrics.get('indexed_points_count', 0)}",
        f"warnings={metrics.get('warnings', [])}",
    ]
    if error_message:
        parts.append(f"error_message={error_message}")
    return " ".join(parts)


async def upload_batch(
    client: httpx.AsyncClient,
    api_url: str,
    headers: dict[str, str],
    batch: list[CorpusFile],
    poll_timeout_seconds: int,
) -> dict[str, Any]:
    handles = [item.path.open("rb") for item in batch]
    try:
        response = await client.post(
            f"{api_url}/documents/upload",
            headers=headers,
            files=[
                ("files", (item.path.name, handle, "application/octet-stream"))
                for item, handle in zip(batch, handles, strict=True)
            ],
        )
        response.raise_for_status()
        task_id = response.json()["id"]
    finally:
        for handle in handles:
            handle.close()
    return await wait_task(
        client,
        api_url,
        headers,
        task_id,
        poll_timeout_seconds=poll_timeout_seconds,
        raise_on_failed=False,
    )


async def run_batches(args: argparse.Namespace) -> dict[str, Any]:
    corpus_root = Path(args.corpus_dir)
    state_file = Path(args.state_file)
    state = load_state(state_file)
    manifest_info = scan_manifest(corpus_root)
    all_files = collect_corpus_files(corpus_root)
    actual_size = sum(item.size_bytes for item in all_files)
    oversized = [item for item in all_files if item.size_bytes > args.max_file_bytes]
    ingestible = [item for item in all_files if item.size_bytes <= args.max_file_bytes]
    if oversized:
        existing_skipped = {
            entry.get("relative_path")
            for entry in state.get("skipped_oversized", [])
            if entry.get("relative_path")
        }
        for item in oversized:
            if item.relative_path in existing_skipped:
                continue
            state.setdefault("skipped_oversized", []).append(
                {
                    "relative_path": item.relative_path,
                    "size_bytes": item.size_bytes,
                    "reason": "oversized",
                }
            )
        save_state(state_file, state)
    if args.resume:
        done = completed_paths(state)
        ingestible = [item for item in ingestible if item.relative_path not in done]
    batches = build_batches(ingestible, args.max_batch_bytes)
    summary = {
        "corpus_dir": str(corpus_root),
        "actual_files": len(all_files),
        "actual_size_bytes": actual_size,
        "manifest": manifest_info,
        "skipped_oversized": len(oversized),
        "batches_total": len(batches),
        "batches_completed": 0,
        "batches_failed": 0,
        "batches_skipped": 0,
    }
    if not batches:
        return summary
    verify_tls = edge_tls_verify()
    async with httpx.AsyncClient(timeout=300.0, verify=verify_tls) as client:
        headers = await login(client, args.api_url, args.username, args.password)
        if not args.skip_dictionary:
            await ensure_dictionary(client, args.api_url, headers, args.dictionary_version)
        for batch_number, batch in enumerate(batches, start=1):
            batch_paths = [item.relative_path for item in batch]
            if batch_already_done(state, batch_paths, args.resume):
                summary["batches_skipped"] += 1
                print(format_batch_log(batch_number, batch, None, "skipped", {}))
                continue
            task_payload = await upload_batch(
                client,
                args.api_url,
                headers,
                batch,
                args.poll_timeout_seconds,
            )
            status = task_payload.get("status", "unknown")
            metrics = extract_metrics(task_payload)
            error_message = task_payload.get("error_message")
            print(
                format_batch_log(
                    batch_number,
                    batch,
                    task_payload.get("id"),
                    status,
                    metrics,
                    error_message,
                )
            )
            state.setdefault("batches", []).append(
                {
                    "batch_id": batch_number,
                    "files": batch_paths,
                    "task_id": task_payload.get("id"),
                    "status": status,
                    "metrics": metrics,
                    "error_message": error_message,
                }
            )
            if status == "completed":
                summary["batches_completed"] += 1
                completed = set(state.get("completed_file_paths", []))
                completed.update(batch_paths)
                state["completed_file_paths"] = sorted(completed)
            else:
                summary["batches_failed"] += 1
            save_state(state_file, state)
            if status != "completed" and args.stop_on_failure:
                break
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--corpus-dir", default=DEFAULT_CORPUS_DIR)
    parser.add_argument("--dictionary-version", default=DEFAULT_DICTIONARY_VERSION)
    parser.add_argument("--username", default=os.getenv("DEMO_ADMIN_USERNAME", "admin"))
    parser.add_argument("--password", default=os.getenv("DEMO_ADMIN_PASSWORD", "admin123"))
    parser.add_argument("--max-batch-bytes", type=int, default=DEFAULT_MAX_BATCH_BYTES)
    parser.add_argument("--max-file-bytes", type=int, default=DEFAULT_MAX_FILE_BYTES)
    parser.add_argument("--state-file", default=DEFAULT_STATE_FILE)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--skip-dictionary", action="store_true")
    parser.add_argument("--poll-timeout-seconds", type=int, default=DEFAULT_POLL_TIMEOUT_SECONDS)
    parser.add_argument("--stop-on-failure", action="store_true")
    return parser.parse_args()


def main() -> None:
    print(json.dumps(asyncio.run(run_batches(parse_args())), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
