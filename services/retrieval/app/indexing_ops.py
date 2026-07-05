import httpx

from shared.contracts import RetrievalIndexRequest, StorageWriteResult

from .api.query import (
    COLLECTION_NAME,
    build_embeddings,
    build_index_links_by_span,
    build_points,
    collect_index_links,
    ensure_collection,
    qdrant_url,
)


async def write_index(
    client: httpx.AsyncClient,
    request: RetrievalIndexRequest,
) -> StorageWriteResult:
    bootstrap = await ensure_collection(client)
    claim_ids, graph_entity_ids = collect_index_links(request)
    claim_ids_by_span, graph_entity_ids_by_span = build_index_links_by_span(request)
    points = build_points(request.documents, claim_ids_by_span, graph_entity_ids_by_span)
    document_ids = [document.id for document in request.documents]
    if not points:
        return StorageWriteResult(
            backend="qdrant",
            mode="live",
            document_ids=document_ids,
            records_count=0,
            claim_ids=claim_ids,
            graph_entity_ids=graph_entity_ids,
            warnings=[*bootstrap.warnings],
        )
    vectors_response = await build_embeddings(
        client,
        [point["payload"]["text"] for point in points],
        "document",
    )
    for point, vector in zip(points, vectors_response["vectors"], strict=True):
        point["vector"] = vector
    response = await client.put(
        qdrant_url(f"/collections/{COLLECTION_NAME}/points"),
        params={"wait": "true"},
        json={"points": points},
    )
    response.raise_for_status()
    return StorageWriteResult(
        backend="qdrant",
        mode="live",
        document_ids=document_ids,
        records_count=len(points),
        claim_ids=claim_ids,
        graph_entity_ids=graph_entity_ids,
        warnings=[*bootstrap.warnings, *vectors_response["warnings"]],
    )
