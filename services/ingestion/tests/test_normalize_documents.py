from app.api.documents import NormalizeDocumentRequest, build_normalized_document


def test_build_normalized_document_creates_text_and_table_source_spans() -> None:
    request = NormalizeDocumentRequest(
        title="Demo",
        content="Никель показал извлекаемость 82 %.\n\nФлотация применялась в России.",
        table_headers=["parameter", "value"],
        table_rows=[["recovery", "82 %"]],
    )

    document = build_normalized_document(request)

    assert document.title == "Demo"
    assert len(document.source_spans) == 3
    assert document.table_blocks
    assert any(span.source_type == "table" and span.table_block_id for span in document.source_spans)
