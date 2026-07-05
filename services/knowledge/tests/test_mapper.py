from adapters.mapper import artifacts_to_bundle, entity_id_for_name

from shared.contracts import NormalizedDocument, SourceSpan


def test_entity_id_for_name_stable() -> None:
    assert entity_id_for_name("Nickel", "Material") == entity_id_for_name("Nickel", "Material")


def test_artifacts_to_bundle_creates_claim_for_confirmed_measurement() -> None:
    document = NormalizedDocument(
        id="doc-1",
        source_type="article",
        title="Demo",
        content="Ni recovery 92%",
        source_spans=[
            SourceSpan(
                document_id="doc-1",
                page=1,
                start_offset=0,
                end_offset=16,
                text="Ni recovery 92%",
                source_type="text",
            )
        ],
    )
    span_id = document.source_spans[0]
    from shared.utils.source_span import compute_source_span_id

    extraction = {
        "confirmed": [
            {
                "id": "m1",
                "kind": "measurement",
                "value": "92 %",
                "confidence": 0.9,
                "status": "confirmed",
                "source_span_ids": [compute_source_span_id(span_id)],
            }
        ],
        "candidates": [],
    }
    bundle = artifacts_to_bundle(document, extraction)
    assert bundle.documents
    assert bundle.spans
    assert bundle.measurements
    assert bundle.claims
    assert bundle.claims[0].source_span_ids
