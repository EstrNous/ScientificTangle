import argparse
import asyncio
import json
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

DEFAULT_GATEWAY_URL = "http://localhost:8000"
DEFAULT_AUTH_URL = "http://localhost:8001"
DEFAULT_GOLD_PATH = "eval/gold_questions.json"
DEFAULT_OUTPUT = "eval/reports/perf_latest.json"


async def login(client: httpx.AsyncClient, auth_url: str, identifier: str, password: str) -> str:
    response = await client.post(f"{auth_url.rstrip('/')}/api/auth/login", json={"identifier": identifier, "password": password})
    response.raise_for_status()
    return str(response.json()["access_token"])


async def run_queries(client: httpx.AsyncClient, gateway_url: str, token: str, questions: list[dict[str, Any]], repeat: int) -> list[dict[str, Any]]:
    results = []
    headers = {"Authorization": f"Bearer {token}"}
    for _ in range(repeat):
        for question in questions:
            started_at = time.perf_counter()
            response = await client.post(f"{gateway_url.rstrip('/')}/api/query", json={"question": question["text"], "limit": 10}, headers=headers)
            latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
            results.append(
                {
                    "question_id": question["id"],
                    "status_code": response.status_code,
                    "latency_ms": latency_ms,
                    "has_evidence": bool(response.json().get("evidence_bundle", {}).get("evidence_items", [])) if response.headers.get("content-type", "").startswith("application/json") else False,
                }
            )
    return results


def load_official_questions(path: str) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    questions = [item for item in payload.get("questions", []) if item.get("id", "").startswith("official-")]
    for question in questions:
        question["text"] = repair_mojibake(str(question["text"]))
    return questions


def repair_mojibake(text: str) -> str:
    if "Р" not in text and "С" not in text:
        return text
    try:
        return text.encode("cp1251").decode("utf-8")
    except UnicodeError:
        return text


def build_report(results: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = sorted(item["latency_ms"] for item in results)
    p50 = statistics.median(latencies) if latencies else None
    p95 = latencies[min(len(latencies) - 1, round((len(latencies) - 1) * 0.95))] if latencies else None
    return {
        "schema_version": "ml_perf_report.v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "total": len(results),
        "ok": sum(1 for item in results if item["status_code"] == 200),
        "with_evidence": sum(1 for item in results if item["has_evidence"]),
        "latency_ms_p50": p50,
        "latency_ms_p95": p95,
        "results": results,
    }


async def run_perf(args: argparse.Namespace) -> dict[str, Any]:
    questions = load_official_questions(args.gold)
    async with httpx.AsyncClient(timeout=180.0) as client:
        token = await login(client, args.auth_url, args.username, args.password)
        results = await run_queries(client, args.gateway_url, token, questions, args.repeat)
    return build_report(results)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gateway-url", default=DEFAULT_GATEWAY_URL)
    parser.add_argument("--auth-url", default=DEFAULT_AUTH_URL)
    parser.add_argument("--gold", default=DEFAULT_GOLD_PATH)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--username", default="researcher")
    parser.add_argument("--password", default="researcher")
    parser.add_argument("--repeat", type=int, default=2)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = asyncio.run(run_perf(args))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if output.name == "perf_latest.json":
        versioned = output.with_name(f"perf_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json")
        versioned.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
