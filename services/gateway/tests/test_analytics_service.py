import asyncio
import json
from pathlib import Path
from uuid import uuid4

import httpx
from app.service.analytics_service import AdminService, AnalyticsService, GraphService


def test_graph_service_builds_payload_from_knowledge_entities() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/v1/graph/entities"):
            return httpx.Response(200, json={"entity_ids": ["Ni", "Cu", "Co"]})
        return httpx.Response(404)

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            payload = await GraphService(client).get_graph()
            assert len(payload.knowledge_graph.nodes) == 3
            assert payload.entities[0].status == "verified"
            assert len(payload.candidates) <= 10

    asyncio.run(run())


def test_graph_service_catalog_maps_retrieval_items() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/v1/search"):
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "source": {
                                "document_title": "Doc",
                                "source_span": {"id": "span-1", "document_id": "doc-1"},
                                "metadata": {"material": "Ni", "process": "flotation", "year": 2024, "geo": "RU"},
                            }
                        }
                    ]
                },
            )
        return httpx.Response(404)

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            catalog = await GraphService(client).get_catalog()
            assert catalog.items[0].title == "Doc"
            assert catalog.items[0].material == "Ni"
            assert catalog.items[0].year == 2024

    asyncio.run(run())


def test_analytics_service_reads_eval_report_when_present(tmp_path: Path, monkeypatch) -> None:
    report_path = tmp_path / "latest.json"
    report_path.write_text(
        json.dumps(
            {
                "citation_coverage": 0.9,
                "numeric_correctness": 0.8,
                "avg_latency_ms": 150,
                "unsupported_claim_rate": 0.1,
                "entity_linking_f1": 0.7,
                "evidence_recall_at_k": 0.6,
                "results": [
                    {
                        "question_id": "official-001",
                        "question": "test",
                        "citation_coverage": 0.9,
                        "numeric_correctness": 0.8,
                        "latency_ms": 150,
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    (tmp_path / "eval" / "reports").mkdir(parents=True)
    (tmp_path / "eval" / "reports" / "latest.json").write_text(report_path.read_text(encoding="utf-8"), encoding="utf-8")

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(404))) as client:
            payload = await AnalyticsService(client).get_strategic_evaluation()
            assert payload.summary.avg_citation_coverage == 0.9
            assert payload.questions[0].id == "official-001"
            assert payload.questions[0].status == "pass"

    asyncio.run(run())


def test_analytics_service_falls_back_to_gold_questions(monkeypatch, tmp_path: Path) -> None:
    gold = {
        "questions": [
            {"id": "official-001", "text": "Q1", "split": "mvp"},
            {"id": "other-001", "text": "Q2", "split": "train"},
        ]
    }
    monkeypatch.chdir(tmp_path)
    eval_dir = tmp_path / "eval"
    eval_dir.mkdir()
    (eval_dir / "gold_questions.json").write_text(json.dumps(gold, ensure_ascii=False), encoding="utf-8")

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(404))) as client:
            payload = await AnalyticsService(client).get_strategic_evaluation()
            assert len(payload.questions) == 1
            assert payload.questions[0].id == "official-001"
            assert payload.questions[0].status == "warn"

    asyncio.run(run())


def test_analytics_service_returns_empty_when_eval_files_missing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(404))) as client:
            payload = await AnalyticsService(client).get_strategic_evaluation()
            assert payload.questions == []
            assert payload.summary.avg_citation_coverage == 0.0

    asyncio.run(run())


def test_get_eval_report_summary_blocked_when_missing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(404))) as client:
            payload = await AnalyticsService(client).get_eval_report_summary()
            assert payload.status == "blocked_by_data"
            assert "eval/reports/latest.json is not available" in payload.warnings

    asyncio.run(run())


def test_analytics_service_builds_strategic_metrics_from_knowledge() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/v1/graph/gaps"):
            return httpx.Response(200, json=["gap-a", "gap-b"])
        if request.url.path.endswith("/v1/graph/entities"):
            return httpx.Response(200, json={"entity_ids": ["Ni", "Cu", "Co", "Fe"]})
        return httpx.Response(404)

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            payload = await AnalyticsService(client).get_strategic_metrics()
            assert payload.totals["documents"] == 4
            assert payload.totals["gaps"] == 2
            assert len(payload.directions) == 2
            assert payload.low_coverage_topics == ["gap-a", "gap-b"]

    asyncio.run(run())


def test_analytics_service_builds_lab_coverage_from_gaps() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/v1/graph/gaps"):
            return httpx.Response(200, json=["Ni flotation gap", "Cu leaching gap"])
        return httpx.Response(404)

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            payload = await AnalyticsService(client).get_lab_coverage()
            assert payload.summary["gap_count"] == 2
            assert payload.gaps[0].title.startswith("Ni")

    asyncio.run(run())


def test_admin_service_get_admin_stats_counts_restricted_documents() -> None:
    user_id = uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/api/auth/users"):
            return httpx.Response(
                200,
                json={"items": [{"id": str(user_id), "email": "a@b.c", "username": "Admin", "role": "admin"}]},
            )
        if request.url.path.endswith("/documents"):
            return httpx.Response(
                200,
                json={
                    "items": [
                        {"document_id": "doc-1", "title": "Public", "access_level": "internal"},
                        {"document_id": "doc-2", "title": "Secret", "access_level": "restricted"},
                    ]
                },
            )
        if request.url.path.endswith("/audit/events"):
            return httpx.Response(200, json=[])
        return httpx.Response(404)

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            stats = await AdminService(client).get_admin_stats("Bearer token")
            assert stats["summary"]["users_count"] == 1
            assert stats["summary"]["restricted_documents"] == 1
            assert len(stats["access_policies"]) == 2

    asyncio.run(run())


def test_admin_service_get_admin_stats_aggregates_audit_events() -> None:
    user_id = uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/api/auth/users"):
            return httpx.Response(
                200,
                json={"items": [{"id": str(user_id), "email": "a@b.c", "username": "Admin", "role": "admin"}]},
            )
        if request.url.path.endswith("/audit/events"):
            return httpx.Response(
                200,
                json=[
                    {"action": "source_viewed"},
                    {"action": "access_denied"},
                ],
            )
        return httpx.Response(404)

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            stats = await AdminService(client).get_admin_stats("Bearer token")
            assert stats["summary"]["users_count"] == 1
            assert stats["summary"]["audit_events_24h"] == 2
            assert stats["summary"]["access_denied_24h"] == 1

    asyncio.run(run())
