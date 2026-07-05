from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx  # noqa: E402

from scripts._seed_common import (  # noqa: E402
    DEFAULT_API_URL,
    DEFAULT_DICTIONARY_VERSION,
    edge_tls_verify,
    ensure_dictionary,
    login,
)


async def run_seed(args: argparse.Namespace) -> dict:
    verify_tls = edge_tls_verify()
    async with httpx.AsyncClient(timeout=300.0, verify=verify_tls) as client:
        headers = await login(client, args.api_url, args.username, args.password)
        return await ensure_dictionary(
            client,
            args.api_url,
            headers,
            args.dictionary_version,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default=os.getenv("DEMO_API_URL", DEFAULT_API_URL))
    parser.add_argument("--dictionary-version", default=DEFAULT_DICTIONARY_VERSION)
    parser.add_argument("--username", default=os.getenv("AUTH_SEED_ADMIN_USERNAME", os.getenv("DEMO_ADMIN_USERNAME", "admin")))
    parser.add_argument("--password", default=os.getenv("AUTH_SEED_ADMIN_PASSWORD", os.getenv("DEMO_ADMIN_PASSWORD", "admin")))
    return parser.parse_args()


def main() -> None:
    print(json.dumps(asyncio.run(run_seed(parse_args())), ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
