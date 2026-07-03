from app.api.documents import NormalizeDocumentRequest, build_normalized_document


def test_build_normalized_document_text_fallback() -> None:
    request = NormalizeDocumentRequest(
        title="Sample",
        content="Nickel 82 % in Russia.",
        source_type="article",
    )
    document = build_normalized_document(request)
    assert document.title == "Sample"
    assert len(document.source_spans) == 1
    assert "Nickel" in document.source_spans[0].text
