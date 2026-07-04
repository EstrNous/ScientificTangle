#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import httpx


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round((len(ordered) - 1) * ratio))))
    return ordered[index]


def timed_request(client: httpx.Client, method: str, url: str, **kwargs) -> float:
    started = time.perf_counter()
    response = client.request(method, url, **kwargs)
    response.raise_for_status()
    return (time.perf_counter() - started) * 1000


def main() -> int:
    parser = argparse.ArgumentParser(description="Neo4j graph ops latency smoke via Knowledge API")
    parser.add_argument("--base-url", default=os.getenv("KNOWLEDGE_URL", "http://localhost:8004"))
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--p95-ms", type=float, default=float(os.getenv("NEO4J_PERF_P95_MS", "1500")))
    parser.add_argument("--p50-ms", type=float, default=float(os.getenv("NEO4J_PERF_P50_MS", "800")))
    args = parser.parse_args()

    latencies: dict[str, list[float]] = {
        "health": [],
        "resolve_alias": [],
        "find_entities": [],
        "subgraph": [],
    }

    with httpx.Client(timeout=30.0) as client:
        for _ in range(args.iterations):
            latencies["health"].append(timed_request(client, "GET", f"{args.base_url}/health"))
            latencies["resolve_alias"].append(
                timed_request(
                    client,
                    "POST",
                    f"{args.base_url}/v1/graph/resolve-alias",
                    json={"mention": "никель"},
                )
            )
            latencies["find_entities"].append(
                timed_request(
                    client,
                    "POST",
                    f"{args.base_url}/v1/graph/entities",
                    json={"name": "nickel", "limit": 10},
                )
            )
            latencies["subgraph"].append(
                timed_request(
                    client,
                    "POST",
                    f"{args.base_url}/v1/graph/subgraph",
                    json={"claim_ids": [], "entity_ids": [], "source_span_ids": []},
                )
            )

    report: dict[str, dict[str, float]] = {}
    failed = False
    for name, samples in latencies.items():
        p50 = percentile(samples, 0.5)
        p95 = percentile(samples, 0.95)
        report[name] = {"p50_ms": round(p50, 2), "p95_ms": round(p95, 2)}
        if p50 > args.p50_ms or p95 > args.p95_ms:
            failed = True

    print(json.dumps({"report": report, "thresholds": {"p50_ms": args.p50_ms, "p95_ms": args.p95_ms}}, ensure_ascii=False))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
