import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

import httpx

DEFAULT_MODEL_URL = "http://localhost:8006"


def load_env_file(path: str) -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def require_model_tests_enabled() -> None:
    if os.getenv("RUN_MODEL_TESTS") != "1":
        raise SystemExit("Model scripts are opt-in: set RUN_MODEL_TESTS=1")


def require_yandex_env() -> None:
    missing = [key for key in ("YANDEX_API_KEY", "YANDEX_FOLDER_ID") if not os.getenv(key)]
    if missing:
        raise SystemExit(f"Missing required Yandex env vars: {', '.join(missing)}")


async def post_json(client: httpx.AsyncClient, url: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = await client.post(url, json=payload)
    response.raise_for_status()
    return response.json()


def assert_live_mode(name: str, payload: dict[str, Any]) -> None:
    mode = payload.get("mode")
    warnings = " ".join(str(item).lower() for item in payload.get("warnings", []))
    if mode == "deterministic_degraded" or "fallback" in warnings or "degraded" in warnings:
        raise SystemExit(f"{name} used degraded fallback: {json.dumps(payload, ensure_ascii=False)}")


async def run_smoke(model_url: str) -> dict[str, Any]:
    base = model_url.rstrip("/")
    document = {
        "id": "yandex-live-doc",
        "source_type": "technical_note",
        "title": "Yandex live smoke",
        "content": "При электроэкстракции никеля оптимальная скорость потока католита составляет 0,4-0,6 м/с.",
        "source_spans": [
            {
                "document_id": "yandex-live-doc",
                "page": 1,
                "start_offset": 0,
                "end_offset": 91,
                "text": "При электроэкстракции никеля оптимальная скорость потока католита составляет 0,4-0,6 м/с.",
                "source_type": "text",
            }
        ],
        "access_policy": {"level": "internal", "allowed_roles": ["researcher", "admin"]},
    }
    evidence_bundle = {
        "query_ir": {"raw_query": "скорость потока католита", "filters": {}, "limit": 5},
        "evidence_items": [
            {
                "source_span": document["source_spans"][0],
                "relevance_score": 0.9,
                "claim_ids": [],
                "extraction_method": "semantic",
            }
        ],
        "total_found": 1,
        "has_gaps": False,
        "has_conflicts": False,
        "gaps": [],
        "conflicts": [],
    }
    async with httpx.AsyncClient(timeout=180.0) as client:
        status = (await client.get(f"{base}/v1/status")).json()
        if not status.get("yandex_configured"):
            raise SystemExit(f"Model service reports Yandex not configured: {json.dumps(status, ensure_ascii=False)}")
        embeddings = await post_json(client, f"{base}/v1/embeddings", {"texts": ["никель католит"], "input_type": "query"})
        extraction = await post_json(client, f"{base}/v1/extraction/structured", {"document": document})
        query_ir = await post_json(client, f"{base}/v1/query-ir", {"raw_query": "Какая скорость потока католита?", "limit": 5})
        answer = await post_json(
            client,
            f"{base}/v1/answers/synthesize",
            {
                "query_ir": evidence_bundle["query_ir"],
                "evidence_bundle": evidence_bundle,
                "candidate_items": [],
            },
        )
    for name, payload in (("embeddings", embeddings), ("extraction", extraction), ("query_ir", query_ir), ("answer", answer)):
        assert_live_mode(name, payload)
    return {"status": status, "checks": ["embeddings", "extraction", "query_ir", "answer"]}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-url", default=DEFAULT_MODEL_URL)
    parser.add_argument("--env-file", default=".env")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    require_model_tests_enabled()
    load_env_file(args.env_file)
    require_yandex_env()
    result = asyncio.run(run_smoke(args.model_url))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
