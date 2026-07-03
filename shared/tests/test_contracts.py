import pytest
from pydantic import ValidationError

from shared.contracts import NormalizedDocument, QueryIR, SourceSpan


def test_source_span_rejects_invalid_source_type() -> None:
    with pytest.raises(ValidationError):
        SourceSpan(
            document_id="d1",
            page=1,
            start_offset=0,
            end_offset=1,
            text="x",
            source_type="invalid",
        )


def test_normalized_document_accepts_valid_span() -> None:
    span = SourceSpan(
        document_id="d1",
        page=1,
        start_offset=0,
        end_offset=5,
        text="hello",
        source_type="text",
    )
    doc = NormalizedDocument(
        id="d1",
        source_type="article",
        title="T",
        content="hello",
        source_spans=[span],
    )
    assert doc.source_spans[0].text == "hello"


def test_query_ir_minimal() -> None:
    query = QueryIR(
        raw_query="test",
        filters={},
        entities=[],
        intent="fact_lookup",
    )
    assert query.raw_query == "test"
