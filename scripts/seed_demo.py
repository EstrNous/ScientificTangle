import argparse
import asyncio
import json
import os
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


async def run_demo(args: argparse.Namespace) -> dict[str, Any]:
    corpus_root = Path(args.corpus_dir)
    corpus_files = [path for path in corpus_root.rglob("*") if path.is_file() and path.name != "manifest.json"]
    if not corpus_files:
        raise SystemExit(f"Real demo corpus is missing in {corpus_root}")
    verify_tls = edge_tls_verify()
    async with httpx.AsyncClient(timeout=180.0, verify=verify_tls) as client:
        headers = await login(client, args.api_url, args.username, args.password)
        dictionary_result = await ensure_dictionary(
            client,
            args.api_url,
            headers,
            args.dictionary_version,
        )
        handles = [path.open("rb") for path in corpus_files]
        try:
            documents = await client.post(
                f"{args.api_url}/documents/upload",
                headers=headers,
                files=[
                    ("files", (path.name, handle, "application/octet-stream"))
                    for path, handle in zip(corpus_files, handles, strict=True)
                ],
            )
            documents.raise_for_status()
        finally:
            for handle in handles:
                handle.close()
        document_task = await wait_task(client, args.api_url, headers, documents.json()["id"])
        return {
            "dictionary": dictionary_result["dictionary"],
            "dictionary_task": dictionary_result["dictionary_task"],
            "document_task": document_task,
            "corpus_files": len(corpus_files),
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--corpus-dir", default=DEFAULT_CORPUS_DIR)
    parser.add_argument("--dictionary-version", default=DEFAULT_DICTIONARY_VERSION)
    parser.add_argument("--username", default=os.getenv("DEMO_ADMIN_USERNAME", "admin"))
    parser.add_argument("--password", default=os.getenv("DEMO_ADMIN_PASSWORD", "admin123"))
    return parser.parse_args()


def main() -> None:
    print(json.dumps(asyncio.run(run_demo(parse_args())), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
