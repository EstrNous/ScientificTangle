from pathlib import Path

from eval.offline_quality_gate import evaluate_offline_quality
from eval.run_eval import build_report


def base_gold() -> dict:
    return {
        "questions": [
            {
                "id": "official-001",
                "split": "mvp",
                "expected_entities": ["Ni"],
                "expected_source_span_ids": ["span-1"],
                "expected_source_span_review": {"status": "reviewed"},
            }
        ],
        "corpus_regression_questions": [
            {
                "id": "corpus-001",
                "expected_forbidden_source_span_ids": ["forbidden-1"],
            }
        ],
    }


def base_fixtures() -> dict:
    return {
        "review_policy": {"live_model_calls": "blocked_by_policy"},
        "external_dataset": {
            "normalized_source_spans_status": "blocked_by_data",
            "reason_codes": ["raw_corpus_not_normalized"],
        },
        "official_questions": [
            {
                "question_id": "official-001",
                "expected_source_span_ids": ["span-1"],
            }
        ],
    }


def base_suites() -> dict:
    return {
        "suites": {
            "official_questions": {"question_ids": ["official-001"]},
            "hybrid_retrieval": {"question_ids": ["corpus-001"]},
            "access_filtering": {"question_ids": ["corpus-001"]},
            "unsupported_claims": {"question_ids": ["official-001"]},
            "answer_completeness": {"question_ids": ["official-001"]},
        }
    }


def test_offline_quality_gate_marks_policy_and_data_blocks() -> None:
    result = evaluate_offline_quality(base_gold(), base_fixtures(), {"inputs": []}, base_suites(), Path.cwd())

    statuses = {item["id"]: item["status"] for item in result["checks"]}

    assert result["overall_status"] == "warn"
    assert statuses["live_answer_quality"] == "blocked_by_policy"
    assert statuses["live_latency_p95"] == "blocked_by_policy"
    assert statuses["full_corpus_reviewed_source_expectations"] == "blocked_by_data"
    assert statuses["official_expected_source_spans"] == "pass"
    assert statuses["access_filtering_fixture"] == "pass"


def test_offline_quality_gate_fails_missing_source_span_expectation() -> None:
    gold = base_gold()
    gold["questions"][0]["expected_source_span_ids"] = []

    result = evaluate_offline_quality(gold, base_fixtures(), {"inputs": []}, base_suites(), Path.cwd())

    statuses = {item["id"]: item["status"] for item in result["checks"]}
    assert result["overall_status"] == "fail"
    assert statuses["official_expected_source_spans"] == "fail"


def test_offline_quality_gate_accepts_optional_offline_report_without_live_latency_claim() -> None:
    report = build_report(
        [
            {
                "question_id": "official-001",
                "status_code": 200,
                "latency_ms": 120,
                "citation_coverage": 1.0,
                "numeric_correctness": None,
                "query_ir_constraint_recall": 1.0,
                "evidence_recall_at_k": 1.0,
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

    result = evaluate_offline_quality(base_gold(), base_fixtures(), {"inputs": []}, base_suites(), Path.cwd(), report)
    latency = [item for item in result["checks"] if item["id"] == "latency_ms_p95"]

    assert latency
    assert all(item["status"] == "blocked_by_policy" for item in latency)
