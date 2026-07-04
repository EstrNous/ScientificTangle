import httpx
from adapters.mapper import artifacts_to_bundle
from adapters.neo4j_adapter import Neo4jKnowledgeAdapter
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from shared.contracts import (
    KnowledgeIngestionRequest,
    KnowledgeIngestionResponse,
    StorageWriteResult,
)
from shared.utils.request_id import generate_request_id

from ..core.config import settings
from .dictionaries import _load_version

router = APIRouter(prefix="/v1/documents", tags=["knowledge"])


class DocumentGraphDeleteResponse(BaseModel):
    document_id: str
    deleted: bool
    deleted_nodes: int = 0
    warnings: list[str] = Field(default_factory=list)


@router.post("/extract", response_model=KnowledgeIngestionResponse)
async def extract_document(
    request: KnowledgeIngestionRequest,
    app_request: Request,
) -> KnowledgeIngestionResponse:
    request_id = getattr(app_request.state, "request_id", None) or generate_request_id()
    client: httpx.AsyncClient = app_request.app.state.http_client
    response = await client.post(
        f"{settings.model_url.rstrip('/')}/v1/extraction/structured",
        json={"document": request.document.model_dump(mode="json")},
    )
    response.raise_for_status()
    extraction = response.json()
    if request.dictionary_version_id is not None:
        dictionary = await _load_version(app_request, request.dictionary_version_id)
        canonical_by_alias = {}
        for file in dictionary.files:
            if file.kind not in {"aliases", "entities", "units", "geographies"}:
                continue
            for entry in file.entries:
                canonical = str(entry.get("canonical") or entry.get("name") or "").strip()
                for value in [canonical, *entry.get("aliases", [])]:
                    if value:
                        canonical_by_alias[str(value).casefold()] = canonical or str(value)
        for layer in ("confirmed", "candidates"):
            for artifact in extraction.get(layer, []):
                if not isinstance(artifact, dict):
                    continue
                value = str(artifact.get("value", ""))
                if value.casefold() in canonical_by_alias:
                    artifact["value"] = canonical_by_alias[value.casefold()]
                metadata = artifact.setdefault("metadata", {})
                if isinstance(metadata, dict):
                    metadata["dictionary_version_id"] = str(dictionary.id)
    confirmed = extraction.get("confirmed", [])
    candidates = extraction.get("candidates", [])
    records_count = len(confirmed) + len(candidates)
    confirmed_count = len(confirmed)
    warnings: list[str] = []
    adapter: Neo4jKnowledgeAdapter | None = getattr(app_request.app.state, "neo4j_adapter", None)
    mode: str = "adapter_pending"
    claim_ids: list[str] = []
    graph_entity_ids: list[str] = []
    if adapter is not None:
        bundle = artifacts_to_bundle(request.document, extraction)
        claim_ids = [claim.claim_id for claim in bundle.claims]
        graph_entity_ids = [entity.entity_id for entity in bundle.entities]
        try:
            written = await adapter.write_bundle(bundle, request_id=request_id)
            if written:
                mode = "live"
            else:
                warnings.append("neo4j_write_empty")
        except Exception as exc:
            warnings.append(f"neo4j_write_failed:{exc}")
    else:
        warnings.append("neo4j_adapter_pending")
    return KnowledgeIngestionResponse(
        document_id=request.document.id,
        extraction=extraction,
        graph_write=StorageWriteResult(
            backend="neo4j",
            mode=mode,  # type: ignore[arg-type]
            document_ids=[request.document.id],
            records_count=records_count,
            confirmed_count=confirmed_count,
            claim_ids=claim_ids,
            graph_entity_ids=graph_entity_ids,
            warnings=warnings,
        ),
        warnings=warnings,
    )


@router.delete("/{document_id}/graph", response_model=DocumentGraphDeleteResponse)
async def delete_document_graph(
    document_id: str,
    app_request: Request,
) -> DocumentGraphDeleteResponse:
    adapter: Neo4jKnowledgeAdapter | None = getattr(app_request.app.state, "neo4j_adapter", None)
    if adapter is None:
        return DocumentGraphDeleteResponse(
            document_id=document_id,
            deleted=False,
            warnings=["neo4j_adapter_pending"],
        )
    async with adapter._driver.session() as session:
        result = await session.run(
            """
            MATCH (d:Document {document_id: $document_id})
            OPTIONAL MATCH (d)<-[:PART_OF]-(s:SourceSpan)
            OPTIONAL MATCH (s)<-[:DESCRIBED_IN]-(n)
            WITH d, collect(DISTINCT s) AS spans, collect(DISTINCT n) AS linked
            WITH [d] + spans + linked AS nodes
            FOREACH (node IN nodes | DETACH DELETE node)
            RETURN size(nodes) AS deleted_nodes
            """,
            document_id=document_id,
        )
        record = await result.single()
    deleted_nodes = int(record["deleted_nodes"]) if record and record.get("deleted_nodes") else 0
    return DocumentGraphDeleteResponse(
        document_id=document_id,
        deleted=deleted_nodes > 0,
        deleted_nodes=deleted_nodes,
    )
