import asyncio
import json
from types import SimpleNamespace

import httpx

from app.api.query import (
    RetrievalQueryRequest,
    RetrievalSearchRequest,
    SourceResolveRequest,
    resolve_source,
    run_query,
    search,
)
from app.storage import access_allowed
from shared.contracts import (
    AccessPolicy,
    SearchResult,
    SearchResultPayload,
    SourcePayload,
    SourceSpan,
)


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


class FakeStorageAdapter:
    is_ready = True

    async def search(self, question, filters, access_roles, limit):
        return SearchResultPayload(
            items=[
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
        )

    async def get_source(self, source_span_id, access_roles):
        return source(
            source_span_id,
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

    assert source_result.source_span.document_id == "span-1"
    assert [item.source.source_span.document_id for item in search_result.items] == [
        "allowed"
    ]
