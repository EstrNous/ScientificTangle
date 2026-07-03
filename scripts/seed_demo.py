import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

import httpx

DEFAULT_RETRIEVAL_URL = "http://localhost:8005"
DEFAULT_SEED_PATH = "demo/seed_data/mvp_normalized_documents.json"


async def seed_demo(retrieval_url: str, seed_path: str, reset: bool, fail_on_degraded: bool) -> dict[str, Any]:
    payload = json.loads(Path(seed_path).read_text(encoding="utf-8"))
    documents = payload.get("normalized_documents", [])
    if not documents:
        raise SystemExit(f"No normalized_documents in {seed_path}")
    async with httpx.AsyncClient(timeout=120.0) as client:
        if reset:
            reset_response = await client.post(f"{retrieval_url.rstrip('/')}/v1/index/reset")
            reset_response.raise_for_status()
        else:
            bootstrap_response = await client.post(f"{retrieval_url.rstrip('/')}/v1/index/bootstrap")
            bootstrap_response.raise_for_status()
        index_response = await client.post(
            f"{retrieval_url.rstrip('/')}/v1/documents/index",
            json={"documents": documents},
        )
        index_response.raise_for_status()
        result = index_response.json()
        indexed_count = result.get("vector_write", {}).get("records_count", 0)
        warnings = " ".join(str(item).lower() for item in result.get("warnings", []))
        if fail_on_degraded and ("fallback" in warnings or "degraded" in warnings):
            raise SystemExit(json.dumps(result, ensure_ascii=False, indent=2))
        result["indexed_points_count"] = indexed_count
        return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--retrieval-url", default=DEFAULT_RETRIEVAL_URL)
    parser.add_argument("--seed-path", default=DEFAULT_SEED_PATH)
    parser.add_argument("--no-reset", action="store_true")
    parser.add_argument("--fail-on-degraded", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = asyncio.run(seed_demo(args.retrieval_url, args.seed_path, not args.no_reset, args.fail_on_degraded))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
