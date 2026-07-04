from shared.contracts import SourceSpan
from shared.utils.source_span import compute_source_span_id, compute_source_span_id_from_parts


def test_compute_source_span_id_is_stable() -> None:
    span = SourceSpan(
        document_id="doc-1",
        page=1,
        start_offset=0,
        end_offset=10,
        text="nickel",
        source_type="text",
    )
    first = compute_source_span_id(span)
    second = compute_source_span_id(span.model_copy(update={"text": "changed"}))
    assert first == second
    assert len(first) == 16


def test_compute_source_span_id_from_parts_matches_span_helper() -> None:
    span = SourceSpan(
        document_id="doc-2",
        page=3,
        start_offset=4,
        end_offset=12,
        text="Cu",
        source_type="text",
        table_block_id="tbl-1",
    )
    assert compute_source_span_id(span) == compute_source_span_id_from_parts(
        "doc-2",
        3,
        4,
        12,
        "tbl-1",
    )
