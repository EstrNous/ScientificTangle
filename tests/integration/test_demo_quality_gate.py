from pathlib import Path

from eval.demo_quality_gate import evaluate_demo_quality
from eval.run_eval import build_report


def test_demo_quality_gate_blocks_without_live_report() -> None:
    result = evaluate_demo_quality(
        None,
        {"inputs": []},
        {"suites": {"official_questions": {}, "hybrid_retrieval": {}, "access_filtering": {}, "unsupported_claims": {}, "answer_completeness": {}}},
        Path.cwd(),
    )

    assert result["overall_status"] == "blocked"
    assert any(item["id"] == "live_eval_report" and item["status"] == "blocked" for item in result["checks"])


def test_demo_quality_gate_passes_clean_report() -> None:
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
        ]
    )

    result = evaluate_demo_quality(
        report,
        {"inputs": []},
        {"suites": {"official_questions": {}, "hybrid_retrieval": {}, "access_filtering": {}, "unsupported_claims": {}, "answer_completeness": {}}},
        Path.cwd(),
    )

    assert result["overall_status"] == "pass"


def test_demo_quality_gate_fails_blockers() -> None:
    report = build_report(
        [
            {
                "question_id": "official-001",
                "status_code": 500,
                "latency_ms": 120,
                "citation_coverage": 0.0,
                "numeric_correctness": None,
                "query_ir_constraint_recall": None,
                "evidence_recall_at_k": None,
                "unsupported_claim_rate": 0.5,
                "entity_linking_f1": None,
                "candidate_quality_review_rate": None,
                "answer_completeness": 0.0,
                "geo_correctness": None,
                "conflict_detection_accuracy": None,
                "gap_precision": None,
                "access_leak_rate": 1.0,
                "jsonld_provenance_coverage": None,
                "query_trace_completeness": 0.0,
                "has_evidence": False,
                "error": "boom",
            }
        ]
    )

    result = evaluate_demo_quality(
        report,
        {"inputs": []},
        {"suites": {"official_questions": {}, "hybrid_retrieval": {}, "access_filtering": {}, "unsupported_claims": {}, "answer_completeness": {}}},
        Path.cwd(),
    )

    assert result["overall_status"] == "fail"
