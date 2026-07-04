from app.service.scientific_query import (
    merge_graph_exact_evidence,
    partition_verified_evidence,
    planner_selects_graph,
    scientific_query_enabled,
)

from shared.contracts import EvidenceBundle, EvidenceItem, QueryIR, SourceSpan


def test_scientific_query_enabled_respects_filter_override() -> None:
    assert scientific_query_enabled(False, {"top1_scientific_query": True}) is True
    assert scientific_query_enabled(True, {"top1_scientific_query": False}) is False
    assert scientific_query_enabled(True, {}) is True
    assert scientific_query_enabled(False, {}) is False


def test_planner_selects_graph_reads_trace() -> None:
    trace = {
        "planner": {
            "trace": [
                {"profile": "semantic", "selected": True},
                {"profile": "graph", "selected": True, "reason": "graph_candidate_channel"},
            ]
        }
    }
    assert planner_selects_graph(trace) is True
    assert planner_selects_graph({"planner": {"trace": []}}) is False


def test_merge_graph_exact_evidence_adds_graph_items_and_conflicts() -> None:
    query_ir = QueryIR(raw_query="nickel")
    bundle = EvidenceBundle(query_ir=query_ir, evidence_items=[], total_found=0)
    graph_result = {
        "fallback_state": "partial",
        "conflicts": ["unit mismatch"],
        "gaps": ["missing measurement"],
        "evidence": [
            {
                "claim_id": "claim-graph-1",
                "statement": "Nickel 82 %",
                "confidence": 0.8,
                "status": "confirmed",
                "source_span": {
                    "source_span_id": "span-graph-1",
                    "document_id": "doc-1",
                    "page_number": 2,
                    "raw_text": "Nickel 82 %",
                    "char_start": 0,
                    "char_end": 11,
                    "source_type": "text",
                },
            }
        ],
    }

    updated, graph_trace = merge_graph_exact_evidence(bundle, graph_result)

    assert updated.total_found == 1
    assert updated.evidence_items[0].extraction_method == "exact"
    assert updated.has_conflicts is True
    assert "unit mismatch" in updated.conflicts
    assert graph_trace["added_evidence_items"] == 1


def test_partition_verified_evidence_demotes_failed_items() -> None:
    span = SourceSpan(
        id="span-1",
        document_id="doc-1",
        page=1,
        start_offset=0,
        end_offset=10,
        text="unsupported text",
        source_type="text",
    )
    bundle = EvidenceBundle(
        query_ir=QueryIR(raw_query="test"),
        evidence_items=[EvidenceItem(source_span=span, relevance_score=0.9)],
        total_found=1,
    )
    artifacts = [
        {
            "id": "span-1",
            "kind": "claim",
            "value": span.text,
            "confidence": 0.9,
            "status": "candidate",
            "source_span_ids": ["span-1"],
            "reason_codes": ["geo_mismatch"],
        }
    ]

    updated, candidates = partition_verified_evidence(bundle, artifacts)

    assert updated.evidence_items == []
    assert candidates[0]["reason_codes"] == ["geo_mismatch"]