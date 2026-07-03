from app.api.query import collect_evidence_items
from shared.contracts import AccessPolicy, NormalizedDocument, QueryIR, SourceSpan


def test_collect_evidence_items_respects_access_policy_and_constraints() -> None:
    allowed_span = SourceSpan(
        document_id="allowed",
        page=1,
        start_offset=0,
        end_offset=52,
        text="В России извлекаемость никеля составила 82 %.",
        source_type="text",
    )
    denied_span = SourceSpan(
        document_id="denied",
        page=1,
        start_offset=0,
        end_offset=47,
        text="Закрытый источник сообщает никель 99 %.",
        source_type="text",
    )
    allowed_document = NormalizedDocument(
        id="allowed",
        source_type="article",
        title="Allowed",
        content=allowed_span.text,
        source_spans=[allowed_span],
        access_policy=AccessPolicy(level="internal", allowed_roles=["researcher"]),
    )
    denied_document = NormalizedDocument(
        id="denied",
        source_type="report",
        title="Denied",
        content=denied_span.text,
        source_spans=[denied_span],
        access_policy=AccessPolicy(level="restricted", allowed_roles=["admin"]),
    )
    query_ir = QueryIR(
        raw_query="никель Россия 82 %",
        filters={"numeric_constraints": [{"value": 82, "unit": "%"}], "geo_constraints": ["Россия"]},
    )

    items = collect_evidence_items(query_ir, [allowed_document, denied_document], ["researcher"])

    assert len(items) == 1
    assert items[0].source_span.document_id == "allowed"
    assert items[0].relevance_score > 0
