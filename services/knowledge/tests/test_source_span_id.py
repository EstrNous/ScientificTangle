import pytest

from shared.contracts import SourceSpan
from shared.utils.source_span import compute_source_span_id, compute_source_span_id_from_parts


def test_compute_source_span_id_stable() -> None:
    span = SourceSpan(
        document_id="doc-1",
        page=2,
        start_offset=10,
        end_offset=25,
        text="sample text",
        source_type="text",
    )
    first = compute_source_span_id(span)
    second = compute_source_span_id(span)
    assert first == second
    assert len(first) == 16


def test_compute_source_span_id_from_parts_matches_span() -> None:
    span = SourceSpan(
        document_id="doc-1",
        page=2,
        start_offset=10,
        end_offset=25,
        text="sample text",
        table_block_id="tbl-1",
        source_type="table",
    )
    assert compute_source_span_id(span) == compute_source_span_id_from_parts(
        "doc-1",
        2,
        10,
        25,
        "tbl-1",
    )
