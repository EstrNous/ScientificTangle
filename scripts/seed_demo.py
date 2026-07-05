from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx

from scripts._seed_common import (
    DEFAULT_API_URL,
    DEFAULT_CORPUS_DIR,
    DEFAULT_DICTIONARY_VERSION,
    edge_tls_verify,
    ensure_dictionary,
    login,
)
from scripts.seed_corpus_batches import (
    DEFAULT_MAX_BATCH_BYTES,
    DEFAULT_MAX_FILE_BYTES,
    DEFAULT_POLL_TIMEOUT_SECONDS,
    DEFAULT_STATE_FILE,
    run_batches,
)

DEFAULT_DEMO_STATE_FILE = ".seed_demo_state.json"


async def run_demo(args: argparse.Namespace) -> dict[str, Any]:
    corpus_root = Path(args.corpus_dir)
    state_file = Path(args.state_file)
    verify_tls = edge_tls_verify()
    async with httpx.AsyncClient(timeout=300.0, verify=verify_tls) as client:
        headers = await login(client, args.api_url, args.username, args.password)
        dictionary_result = None
        if not args.skip_dictionary:
            dictionary_result = await ensure_dictionary(
                client,
                args.api_url,
                headers,
                args.dictionary_version,
            )
        batch_args = argparse.Namespace(
            api_url=args.api_url,
            corpus_dir=str(corpus_root),
            dictionary_version=args.dictionary_version,
            username=args.username,
            password=args.password,
            max_batch_bytes=args.max_batch_bytes,
            max_file_bytes=args.max_file_bytes,
            state_file=str(state_file),
            resume=args.resume,
            skip_dictionary=True,
            poll_timeout_seconds=args.poll_timeout_seconds,
            stop_on_failure=True,
        )
        batch_summary = await run_batches(batch_args)
        if batch_summary.get("batches_failed", 0) > 0:
            raise SystemExit(1)
        result: dict[str, Any] = {
            "corpus_dir": str(corpus_root),
            "batch_summary": batch_summary,
        }
        if dictionary_result is not None:
            result["dictionary"] = dictionary_result["dictionary"]
            result["dictionary_task"] = dictionary_result["dictionary_task"]
        return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--corpus-dir", default=DEFAULT_CORPUS_DIR)
    parser.add_argument("--dictionary-version", default=DEFAULT_DICTIONARY_VERSION)
    parser.add_argument("--username", default=os.getenv("DEMO_ADMIN_USERNAME", "admin"))
    parser.add_argument("--password", default=os.getenv("DEMO_ADMIN_PASSWORD", "admin123"))
    parser.add_argument("--state-file", default=DEFAULT_DEMO_STATE_FILE)
    parser.add_argument("--max-batch-bytes", type=int, default=DEFAULT_MAX_BATCH_BYTES)
    parser.add_argument("--max-file-bytes", type=int, default=DEFAULT_MAX_FILE_BYTES)
    parser.add_argument("--poll-timeout-seconds", type=int, default=DEFAULT_POLL_TIMEOUT_SECONDS)
    parser.add_argument("--resume", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--skip-dictionary", action="store_true")
    return parser.parse_args()


def main() -> None:
    print(json.dumps(asyncio.run(run_demo(parse_args())), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
