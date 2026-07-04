from adapters.dto import SourceSpanDTO
from adapters.operations import source_span_write_params


def test_source_span_write_params_fills_highlight_and_row_id() -> None:
    span = SourceSpanDTO(
        source_span_id="span-1",
        document_id="doc-1",
        page_number=3,
        raw_text="nickel flow",
        char_start=10,
        char_end=25,
        source_type="table",
        table_block_id="tbl-1:row:0",
    )
    params = source_span_write_params(span)
    assert params["highlight_start"] == 10
    assert params["highlight_end"] == 25
    assert params["table_row_id"] == "tbl-1:row:0"


def test_list_review_candidates_query_exists() -> None:
    from adapters import queries

    assert "CandidateEntity" in queries.LIST_REVIEW_CANDIDATES
    assert "CandidateRelation" in queries.LIST_REVIEW_CANDIDATES
    assert "CandidateClass" in queries.LIST_REVIEW_CANDIDATES
