from eval.run_eval import access_leak_rate, collect_source_span_ids


def test_access_leak_rate_is_none_without_forbidden_ids() -> None:
    question = {"expected_forbidden_source_span_ids": []}
    evidence = [{"source_span": {"id": "span-1"}}]
    assert access_leak_rate(question, evidence) is None


def test_access_leak_rate_is_zero_when_forbidden_absent() -> None:
    question = {"expected_forbidden_source_span_ids": ["forbidden-1"]}
    evidence = [{"source_span": {"id": "allowed-1"}}]
    assert access_leak_rate(question, evidence) == 0.0


def test_access_leak_rate_detects_leaked_span() -> None:
    question = {"expected_forbidden_source_span_ids": ["leaked-1", "leaked-2"]}
    evidence = [
        {"source_span": {"id": "allowed-1"}},
        {"source_span": {"id": "leaked-1"}},
    ]
    assert access_leak_rate(question, evidence) == 0.5


def test_collect_source_span_ids_reads_id_and_metadata() -> None:
    items = [
        {"source_span": {"id": "direct-id"}},
        {"source_span": {"metadata": {"source_span_id": "meta-id"}}},
        {
            "source_span": {
                "document_id": "doc-1",
                "page": 1,
                "start_offset": 0,
                "end_offset": 10,
            }
        },
    ]
    ids = collect_source_span_ids(items)
    assert "direct-id" in ids
    assert "meta-id" in ids
    assert any(value.startswith("doc-1") or len(value) > 8 for value in ids)
