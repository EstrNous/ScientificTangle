import argparse
import asyncio
import json
import os
from pathlib import Path

import httpx
import pytest

from scripts.seed_demo import run_demo

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_E2E") != "1",
    reason="Set RUN_E2E=1 with a clean docker compose stack",
)


def test_four_official_questions_use_real_gateway_evidence() -> None:
    corpus_dir = Path(os.getenv("DEMO_CORPUS_DIR", "demo/seed_data/yandex_disk_corpus"))
    if not any(path.is_file() and path.name != "manifest.json" for path in corpus_dir.rglob("*")):
        pytest.fail(f"Real MVP corpus is missing in {corpus_dir}")
    gold = json.loads(Path("eval/gold_questions.json").read_text(encoding="utf-8"))["questions"]
    official = [question for question in gold if question.get("split") == "mvp"]
    assert len(official) == 4
    assert all(question.get("expected_source_span_ids") for question in official)

    async def execute() -> None:
        api_url = os.getenv("DEMO_API_URL", "http://localhost/api")
        username = os.getenv("DEMO_ADMIN_USERNAME", "admin")
        password = os.getenv("DEMO_ADMIN_PASSWORD", "admin123")
        await run_demo(
            argparse.Namespace(
                api_url=api_url,
                corpus_dir=str(corpus_dir),
                dictionary_version="mvp.acceptance.v1",
                username=username,
                password=password,
            )
        )
        async with httpx.AsyncClient(timeout=180.0) as client:
            login = await client.post(
                f"{api_url}/auth/login",
                json={"identifier": username, "password": password},
            )
            login.raise_for_status()
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
            for question in official:
                response = await client.post(
                    f"{api_url}/query",
                    headers=headers,
                    json={"question": question["text"], "limit": 20},
                )
                response.raise_for_status()
                run = response.json()
                assert run["status"] == "completed"
                evidence = run["evidence_bundle"]["evidence_items"]
                actual_ids = {item["source_span"]["id"] for item in evidence}
                assert actual_ids & set(question["expected_source_span_ids"])
                assert run["answer"]["sources_count"] > 0
                source_id = evidence[0]["source_span"]["id"]
                source = await client.get(f"{api_url}/source/{source_id}", headers=headers)
                source.raise_for_status()
                graph = await client.get(
                    f"{api_url}/graph/subgraph",
                    params={"run_id": run["id"]},
                    headers=headers,
                )
                graph.raise_for_status()
                search = await client.get(
                    f"{api_url}/search",
                    params={"question": question["text"], "limit": 5},
                    headers=headers,
                )
                search.raise_for_status()
                assert search.json()["items"]
                for export_format in ("markdown", "json"):
                    exported = await client.post(
                        f"{api_url}/export",
                        headers=headers,
                        json={"query_run_id": run["id"], "format": export_format},
                    )
                    exported.raise_for_status()
            audit = await client.get(f"{api_url}/audit/events", headers=headers)
            audit.raise_for_status()
            actions = {event["action"] for event in audit.json()}
            assert {"dictionary_activated", "query_created", "source_viewed", "document_exported"} <= actions

    asyncio.run(execute())
