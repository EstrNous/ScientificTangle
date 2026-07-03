from eval.run_eval import build_report


def test_build_report_has_core_metrics() -> None:
    report = build_report(
        [
            {
                "citation_coverage": 1.0,
                "numeric_correctness": 1.0,
                "query_ir_constraint_recall": 1.0,
                "evidence_recall_at_k": 1.0,
                "unsupported_claim_rate": 0.0,
                "entity_linking_f1": 1.0,
                "candidate_quality_review_rate": 0.0,
                "answer_completeness": 1.0,
                "geo_correctness": 1.0,
            }
        ]
    )
    assert "citation_coverage" in report
    assert "numeric_correctness" in report
