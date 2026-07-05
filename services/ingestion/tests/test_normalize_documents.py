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


def test_build_normalized_document_enriches_fact_contexts_with_provenance() -> None:
    request = NormalizeDocumentRequest(
        title="Normalization",
        content="Platinum group metals (PGM) recovery reached 82 % in Russia during 2021-2024.",
        table_headers=["parameter", "value"],
        table_rows=[["flow", "1.5 m/s"]],
    )

    document = build_normalized_document(request)

    assert len(document.quantities) == 2
    assert {quantity.unit for quantity in document.quantities} == {"%", "m/s"}
    assert all(quantity.source_span_id for quantity in document.quantities)
    assert document.geo_contexts[0].location_name == "Россия"
    assert document.geo_contexts[0].source_span_id
    assert document.time_contexts[0].start_year == 2021
    assert document.time_contexts[0].end_year == 2024
    assert document.alias_refs[0].alias == "PGM"
    assert document.alias_refs[0].source_span_id
    assert document.metadata["normalization_coverage"]["measurements"] == 2
    assert document.metadata["normalization_coverage"]["tables"] == 1
