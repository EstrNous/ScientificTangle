import asyncio
import json

import httpx

from eval.run_eval import build_report, compare_reports, load_eval_documents, select_questions


def test_build_report_contains_dashboard_data() -> None:
    report = build_report(
        [
            {
                "question_id": "official-001",
                "status_code": 200,
                "latency_ms": 120,
                "citation_coverage": 1.0,
                "numeric_correctness": 1.0,
                "query_ir_constraint_recall": 1.0,
                "evidence_recall_at_k": None,
                "unsupported_claim_rate": 0.0,
                "entity_linking_f1": 1.0,
                "candidate_quality_review_rate": None,
                "answer_completeness": 0.8,
                "geo_correctness": None,
                "conflict_detection_accuracy": None,
                "gap_precision": None,
                "access_leak_rate": 0.0,
                "jsonld_provenance_coverage": 1.0,
                "query_trace_completeness": 1.0,
                "has_evidence": True,
                "error": None,
                "input_documents_count": 1,
            }
        ]
    )

    assert report["dashboard_data"]["official_questions_total"] == 1
    assert report["dashboard_data"]["official_questions_with_evidence"] == 1
    assert report["dashboard_data"]["metric_status"]["numeric_correctness"] == "pass"
    assert report["schema_version"] == "ml_eval_report.v1"
    assert report["metrics"]["access_leak_rate"] == 0.0
    assert report["metrics"]["jsonld_provenance_coverage"] == 1.0
    assert report["dashboard_data"]["metric_status"]["access_leak_rate"] == "pass"


def test_select_questions_uses_named_suite(tmp_path) -> None:
    suites_path = tmp_path / "suites.json"
    suites_path.write_text(
        json.dumps(
            {
                "suites": {
                    "official_questions": {
                        "question_ids": ["official-001", "official-002"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    selected = select_questions(
        [
            {"id": "official-001"},
            {"id": "official-002"},
            {"id": "corpus-001"},
        ],
        "official_questions",
        str(suites_path),
    )

    assert [item["id"] for item in selected] == ["official-001", "official-002"]


def test_compare_reports_marks_new_blockers_as_regression() -> None:
    baseline_result = {
        "question_id": "official-001",
        "status_code": 200,
        "latency_ms": 120,
        "citation_coverage": 1.0,
        "numeric_correctness": 1.0,
        "query_ir_constraint_recall": 1.0,
        "evidence_recall_at_k": None,
        "unsupported_claim_rate": 0.0,
        "entity_linking_f1": 1.0,
        "candidate_quality_review_rate": None,
        "answer_completeness": 1.0,
        "geo_correctness": None,
        "conflict_detection_accuracy": None,
        "gap_precision": None,
        "access_leak_rate": 0.0,
        "jsonld_provenance_coverage": 1.0,
        "query_trace_completeness": 1.0,
        "has_evidence": True,
        "error": None,
    }
    current_blocker = {
        **baseline_result,
        "question_id": "official-002",
        "citation_coverage": 0.0,
        "numeric_correctness": None,
        "query_ir_constraint_recall": None,
        "entity_linking_f1": None,
        "answer_completeness": 0.0,
        "access_leak_rate": None,
        "jsonld_provenance_coverage": None,
        "has_evidence": False,
    }

    comparison = compare_reports(build_report([baseline_result]), build_report([baseline_result, current_blocker]))

    assert comparison["regression"] is True
    assert comparison["new_blocker_question_ids"] == ["official-002"]


def test_load_eval_documents_uses_ingestion_normalize(tmp_path) -> None:
    documents_path = tmp_path / "docs.json"
    documents_path.write_text(
        json.dumps({"documents": [{"title": "Doc", "content": "Никель 82 %", "source_type": "article"}]}, ensure_ascii=False),
        encoding="utf-8",
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "document": {
                    "id": "doc",
                    "source_type": payload["source_type"],
                    "title": payload["title"],
                    "content": payload["content"],
                    "source_spans": [
                        {
                            "document_id": "doc",
                            "page": 1,
                            "start_offset": 0,
                            "end_offset": 11,
                            "text": payload["content"],
                            "source_type": "text",
                        }
                    ],
                },
                "warnings": [],
            },
        )

    async def run() -> list[dict]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await load_eval_documents(client, str(documents_path), "http://ingestion/v1/documents/normalize")

    documents = asyncio.run(run())

    assert documents[0]["source_spans"][0]["text"] == "Никель 82 %"
