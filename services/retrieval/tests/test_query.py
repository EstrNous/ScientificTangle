from app.api.query import build_points, collect_evidence_items, payload_allowed, source_span_id
from shared.contracts import AccessPolicy, NormalizedDocument, QueryIR, SourceSpan, TableBlock


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


def test_build_points_preserves_source_span_id_access_and_numeric_payload() -> None:
    span = SourceSpan(
        document_id="doc",
        page=2,
        start_offset=10,
        end_offset=41,
        text="Россия: скорость потока 0,4-0,6 м/с.",
        source_type="text",
    )
    document = NormalizedDocument(
        id="doc",
        source_type="report",
        title="Doc",
        content=span.text,
        source_spans=[span],
        access_policy=AccessPolicy(level="internal", allowed_roles=["researcher"]),
    )

    span_id = source_span_id(span)
    points = build_points([document], {span_id: ["claim-1"]}, {span_id: ["entity-1"]})

    assert len(points) == 1
    payload = points[0]["payload"]
    assert payload["source_span_id"] == source_span_id(span)
    assert payload["access_level"] == "internal"
    assert payload["allowed_roles"] == ["researcher"]
    assert payload["units"] == ["m/s"]
    assert payload["geo_bucket"] == "domestic"
    assert payload["claim_ids"] == ["claim-1"]


def test_build_points_indexes_table_rows_as_evidence() -> None:
    table = TableBlock(
        id="table-1",
        document_id="doc-table",
        page=3,
        headers=["parameter", "value"],
        rows=[["flow", "0,4 м/с"], ["recovery", "82 %"]],
        caption="Test conditions",
    )
    document = NormalizedDocument(
        id="doc-table",
        source_type="docx",
        title="Table Doc",
        content="",
        table_blocks=[table],
        access_policy=AccessPolicy(level="internal", allowed_roles=["researcher"]),
    )

    points = build_points([document], {}, {})

    assert len(points) == 2
    payloads = [point["payload"] for point in points]
    assert all(payload["item_type"] == "table_row" for payload in payloads)
    assert payloads[0]["table_block_id"] == "table-1:row:0"
    assert payloads[0]["units"] == ["m/s"]
    assert payloads[1]["units"] == ["%"]


def test_payload_allowed_respects_roles_and_admin_bypass() -> None:
    payload = {"access_level": "internal", "allowed_roles": ["researcher"]}

    assert payload_allowed(payload, ["researcher"])
    assert payload_allowed(payload, ["admin"])
    assert not payload_allowed(payload, ["external_partner"])
