import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

import httpx


DEFAULT_GATEWAY_URL = "http://localhost:8000"
DEFAULT_AUTH_URL = "http://localhost:8001"
DEFAULT_GOLD_PATH = "eval/gold_questions.json"


async def login(client: httpx.AsyncClient, auth_url: str, identifier: str, password: str) -> str:
    response = await client.post(f"{auth_url.rstrip('/')}/api/auth/login", json={"identifier": identifier, "password": password})
    response.raise_for_status()
    return str(response.json()["access_token"])


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


async def run_eval(args: argparse.Namespace) -> dict[str, Any]:
    questions = load_official_questions(args.gold)
    results = []
    async with httpx.AsyncClient(timeout=180.0) as client:
        token = await login(client, args.auth_url, args.username, args.password)
        headers = {"Authorization": f"Bearer {token}"}
        for question in questions:
            response = await client.post(
                f"{args.gateway_url.rstrip('/')}/api/query",
                json={"query": question["text"], "limit": 10},
                headers=headers,
            )
            payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            warnings = " ".join(str(item).lower() for item in payload.get("warnings", []))
            evidence = payload.get("evidence_bundle", {}).get("evidence_items", [])
            degraded = "fallback" in warnings
            results.append(
                {
                    "question_id": question["id"],
                    "status_code": response.status_code,
                    "has_evidence": bool(evidence),
                    "degraded": degraded,
                    "sources_count": payload.get("answer", {}).get("sources_count", 0),
                }
            )
    failures = [
        item for item in results
        if item["status_code"] != 200 or not item["has_evidence"] or item["degraded"]
    ]
    report = {"results": results, "failures": failures}
    if failures:
        raise SystemExit(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gateway-url", default=DEFAULT_GATEWAY_URL)
    parser.add_argument("--auth-url", default=DEFAULT_AUTH_URL)
    parser.add_argument("--gold", default=DEFAULT_GOLD_PATH)
    parser.add_argument("--username", default="researcher")
    parser.add_argument("--password", default="researcher123")
    return parser.parse_args()


def main() -> None:
    result = asyncio.run(run_eval(parse_args()))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
