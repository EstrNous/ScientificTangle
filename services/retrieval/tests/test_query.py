import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest
from app.api.query import (
    RetrievalQueryRequest,
    RetrievalSearchRequest,
    SourceResolveRequest,
    build_points,
    collect_evidence_items,
    fuse_channels,
    resolve_source,
    run_query,
    search,
    source_span_id,
)
from app.storage import access_allowed, payload_access_allowed

from shared.contracts import (
    AccessPolicy,
    NormalizedDocument,
    QueryIR,
    SearchResult,
    SearchResultPayload,
    SourcePayload,
    SourceSpan,
    TableBlock,
)
from shared.web import ServiceError


def source(document_id: str, policy: AccessPolicy, text: str) -> SourcePayload:
    return SourcePayload(
        source_span=SourceSpan(
            document_id=document_id,
            page=1,
            start_offset=0,
            end_offset=len(text),
            text=text,
            source_type="text",
        ),
        document_title=f"{document_id}.pdf",
        source_type="pdf",
        access_policy=policy,
    )


def test_fusion_deduplicates_source_spans_and_merges_links() -> None:
    policy = AccessPolicy(level="internal", allowed_roles=["researcher"])
    dense = SearchResult(source=source("doc-1", policy, "nickel"), relevance_score=0.9, claim_ids=["c1"])
    lexical = SearchResult(
        source=dense.source,
        relevance_score=0.8,
        claim_ids=["c2"],
        entity_ids=["e1"],
    )
    fused = fuse_channels({"dense": [dense], "lexical": [lexical]}, 10)
    assert len(fused) == 1
    assert fused[0].claim_ids == ["c1", "c2"]
    assert fused[0].entity_ids == ["e1"]


class FakeStorageAdapter:
    is_ready = True

    async def search(self, question, filters, access_roles, limit):
        items = [
            SearchResult(
                source=source(
                    "allowed",
                    AccessPolicy(level="internal"),
                    "Никель 82 %",
                ),
                relevance_score=0.9,
            ),
            SearchResult(
                source=source(
                    "denied",
                    AccessPolicy(level="restricted", allowed_roles=["admin"]),
                    "Закрытый никель 99 %",
                ),
                relevance_score=1.0,
            ),
        ]
        filtered = [
            item
            for item in items
            if access_allowed(item.source.access_policy, access_roles)
        ]
        return SearchResultPayload(items=filtered)

    async def get_source(self, source_span_id, access_roles):
        return source(
            "allowed",
            AccessPolicy(level="internal"),
            "Никель 82 %",
        )


def test_access_policy_is_fail_closed() -> None:
    assert access_allowed(AccessPolicy(level="public"), ["external_partner"])
    assert access_allowed(AccessPolicy(level="internal"), ["researcher"])
    assert not access_allowed(AccessPolicy(level="internal"), ["external_partner"])
    assert not access_allowed(AccessPolicy(level="restricted"), ["researcher"])
    assert access_allowed(AccessPolicy(level="restricted"), ["admin"])


def test_denied_evidence_is_not_sent_to_reranking() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/query-ir"):
            return httpx.Response(
                200,
                json={
                    "query_ir": {"raw_query": "никель", "filters": {}},
                    "warnings": [],
                },
            )
        if request.url.path.endswith("/graph/evidence"):
            return httpx.Response(200, json=[])
        payload = json.loads(request.content)
        assert len(payload["evidence_items"]) == 1
        assert payload["evidence_items"][0]["source_span"]["document_id"] == "allowed"
        return httpx.Response(
            200,
            json={
                "scored_items": [
                    {"evidence_item": payload["evidence_items"][0], "score": 0.9}
                ]
            },
        )

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            request = SimpleNamespace(
                app=SimpleNamespace(
                    state=SimpleNamespace(
                        http_client=client,
                        storage_adapter=FakeStorageAdapter(),
                    )
                )
            )
            return await run_query(
                RetrievalQueryRequest(
                    question="никель",
                    access_roles=["researcher"],
                ),
                request,
            )

    result = asyncio.run(execute())

    assert result.evidence_bundle.total_found == 1
    assert result.retrieval_trace["accessible"] == 1


class HybridStorageAdapter:
    is_ready = True

    def __init__(self) -> None:
        policy = AccessPolicy(level="internal", allowed_roles=["researcher"])
        self.dense = source("dense-doc", policy, "dense nickel")
        self.lexical = source("lexical-doc", policy, "lexical nickel")
        self.table = source("table-doc", policy, "table nickel").model_copy(
            update={
                "source_span": source("table-doc", policy, "table nickel").source_span.model_copy(
                    update={"source_type": "table"}
                )
            }
        )
        self.graph = source("graph-doc", policy, "graph nickel")
        self.sources = {
            item.source_span.id: item
            for item in [self.dense, self.lexical, self.table, self.graph]
        }

    async def search(self, question, filters, access_roles, limit):
        return SearchResultPayload(
            items=[SearchResult(source=self.dense, relevance_score=0.9)]
        )

    async def search_lexical(self, tokens, filters, access_roles, limit, table_only=False):
        selected = self.table if table_only else self.lexical
        return SearchResultPayload(
            items=[SearchResult(source=selected, relevance_score=0.8)]
        )

    async def get_source(self, source_span_id, access_roles):
        return self.sources.get(source_span_id)


def test_run_query_traces_dense_lexical_table_and_graph_channels() -> None:
    adapter = HybridStorageAdapter()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/query-ir"):
            return httpx.Response(
                200,
                json={
                    "query_ir": {"raw_query": "nickel", "filters": {}},
                    "warnings": [],
                },
            )
        if request.url.path.endswith("/graph/evidence"):
            return httpx.Response(
                200,
                json=[
                    {
                        "source_span": {"source_span_id": adapter.graph.source_span.id},
                        "claim_id": "graph-claim",
                        "confidence": 0.7,
                    }
                ],
            )
        payload = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "scored_items": [
                    {"evidence_item": item, "score": 1.0}
                    for item in payload["evidence_items"]
                ]
            },
        )

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            request = SimpleNamespace(
                app=SimpleNamespace(
                    state=SimpleNamespace(
                        http_client=client,
                        storage_adapter=adapter,
                    )
                )
            )
            return await run_query(
                RetrievalQueryRequest(
                    question="nickel",
                    access_roles=["researcher"],
                    limit=10,
                ),
                request,
            )

    result = asyncio.run(execute())

    assert result.retrieval_trace["storage"] == "hybrid"
    assert result.retrieval_trace["channels"] == {
        "dense": 1,
        "lexical": 1,
        "table": 1,
        "graph": 1,
    }
    assert result.retrieval_trace["fused"] == 4
    assert result.retrieval_trace["reranked"] == 4
    assert {item.extraction_method for item in result.evidence_bundle.evidence_items} == {
        "semantic",
        "table",
    }


def test_source_and_search_repeat_access_filtering() -> None:
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(storage_adapter=FakeStorageAdapter()))
    )

    async def execute():
        source_result = await resolve_source(
            "span-1",
            SourceResolveRequest(access_roles=["researcher"]),
            request,
        )
        search_result = await search(
            RetrievalSearchRequest(
                question="никель",
                access_roles=["researcher"],
            ),
            request,
        )
        return source_result, search_result

    source_result, search_result = asyncio.run(execute())

    assert source_result.source_span.document_id == "allowed"
    assert [item.source.source_span.document_id for item in search_result.items] == [
        "allowed"
    ]


def test_resolve_source_returns_access_denied_for_existing_restricted_source() -> None:
    class RestrictedStorageAdapter(FakeStorageAdapter):
        async def get_source(self, source_span_id, access_roles):
            return source(
                source_span_id,
                AccessPolicy(level="restricted", allowed_roles=["admin"]),
                "Закрытый никель 99 %",
            )

    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(storage_adapter=RestrictedStorageAdapter()))
    )

    async def execute():
        return await resolve_source(
            "restricted-span",
            SourceResolveRequest(access_roles=["external_partner"]),
            request,
        )

    with pytest.raises(ServiceError) as error:
        asyncio.run(execute())

    assert error.value.status_code == 403
    assert error.value.code == "access_denied"


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
        filters={
            "numeric_constraints": [{"value": 82, "unit": "%"}],
            "geo_constraints": ["Россия"],
        },
    )

    items = collect_evidence_items(
        query_ir,
        [allowed_document, denied_document],
        ["researcher"],
    )

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
    assert payloads[0]["table_row_id"] == "table-1:row:0"
    assert payloads[0]["highlight_start"] == payloads[0]["start_offset"]
    assert payloads[0]["highlight_end"] == payloads[0]["end_offset"]
    assert payloads[0]["units"] == ["m/s"]
    assert payloads[1]["units"] == ["%"]


def test_payload_indexes_include_source_lookup_fields() -> None:
    from app.api.query import payload_indexes

    indexes = payload_indexes()
    assert indexes["table_row_id"] == "keyword"
    assert indexes["page"] == "integer"
    assert indexes["highlight_start"] == "integer"
    assert indexes["highlight_end"] == "integer"


def test_payload_allowed_respects_roles_and_admin_bypass() -> None:
    payload = {"access_level": "internal", "allowed_roles": ["researcher"]}

    assert payload_access_allowed(payload, ["researcher"])
    assert payload_access_allowed(payload, ["admin"])
    assert not payload_access_allowed(payload, ["external_partner"])
