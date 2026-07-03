from __future__ import annotations

import uuid
from typing import Any

from neo4j import AsyncTransaction

from . import queries
from .dto import (
    ClaimsBundleDTO,
    EvidenceRecordDTO,
    GraphEdgeDTO,
    GraphNeighborhood,
    GraphNodeDTO,
    GraphSubgraphDTO,
    RankedClaimDTO,
    SourceSpanDTO,
)


def node_to_graph_node(node: Any, node_type: str) -> GraphNodeDTO:
    props = dict(node)
    node_id = (
        props.get("entity_id")
        or props.get("claim_id")
        or props.get("source_span_id")
        or props.get("document_id")
        or props.get("measurement_id")
        or props.get("alias_id")
        or str(node.element_id)
    )
    label = (
        props.get("canonical_name")
        or props.get("statement")
        or props.get("raw_text")
        or props.get("title")
        or props.get("name")
        or node_type
    )
    return GraphNodeDTO(id=str(node_id), label=str(label)[:200], node_type=node_type, properties=props)


async def write_bundle_tx(tx: AsyncTransaction, bundle: ClaimsBundleDTO) -> int:
    written = 0
    for document in bundle.documents:
        await tx.run(queries.WRITE_DOCUMENT, **document.model_dump())
        written += 1
    for span in bundle.spans:
        await tx.run(queries.WRITE_SOURCE_SPAN, **span.model_dump())
        written += 1
    for entity in bundle.entities:
        await tx.run(queries.WRITE_ENTITY, **entity.model_dump())
        written += 1
    for alias in bundle.aliases:
        await tx.run(queries.WRITE_ALIAS, **alias.model_dump())
        written += 1
    for measurement in bundle.measurements:
        await tx.run(queries.WRITE_MEASUREMENT, **measurement.model_dump())
        written += 1
    for geography in bundle.geographies:
        await tx.run(queries.WRITE_GEOGRAPHY, **geography.model_dump())
        written += 1
    for candidate in bundle.candidate_entities:
        await tx.run(queries.WRITE_CANDIDATE_ENTITY, **candidate)
        written += 1
    for claim in bundle.claims:
        await tx.run(queries.WRITE_CLAIM, **claim.model_dump())
        await tx.run(
            queries.WRITE_FACT_VERSION,
            fact_version_id=uuid.uuid4().hex[:16],
            claim_id=claim.claim_id,
            recorded_at=claim.claim_last_updated_at,
        )
        for relation in claim.semantic_relations:
            await tx.run(
                queries.WRITE_SEMANTIC_RELATION_SIMPLE,
                claim_id=claim.claim_id,
                target_id=relation["target_id"],
                rel_type=relation["type"],
            )
        written += 1
    return written


def records_to_subgraph(records: list[Any]) -> GraphSubgraphDTO:
    nodes: dict[str, GraphNodeDTO] = {}
    edges: list[GraphEdgeDTO] = []
    claim_ids: list[str] = []
    source_span_ids: list[str] = []
    for record in records:
        for key, node_type in (
            ("e", "Entity"),
            ("c", "Claim"),
            ("s", "SourceSpan"),
            ("d", "Document"),
            ("m", "Measurement"),
            ("g", "Geography"),
        ):
            value = record.get(key)
            if value is not None:
                graph_node = node_to_graph_node(value, node_type)
                nodes[graph_node.id] = graph_node
                if node_type == "Claim":
                    claim_ids.append(graph_node.id)
                if node_type == "SourceSpan":
                    source_span_ids.append(graph_node.id)
    node_list = list(nodes.values())
    for index, left in enumerate(node_list):
        for right in node_list[index + 1 :]:
            edges.append(
                GraphEdgeDTO(
                    id=f"{left.id}->{right.id}",
                    source=left.id,
                    target=right.id,
                    edge_type="CO_OCCURS",
                )
            )
    return GraphSubgraphDTO(
        nodes=node_list,
        edges=edges,
        claim_ids=list(dict.fromkeys(claim_ids)),
        source_span_ids=list(dict.fromkeys(source_span_ids)),
    )


def path_records_to_neighborhood(entity_id: str, depth: int, records: list[Any]) -> GraphNeighborhood:
    nodes: dict[str, GraphNodeDTO] = {}
    edges: list[GraphEdgeDTO] = []
    for record in records:
        path = record.get("path")
        if path is None:
            continue
        for node in path.nodes:
            labels = list(node.labels)
            node_type = labels[0] if labels else "Node"
            graph_node = node_to_graph_node(node, node_type)
            nodes[graph_node.id] = graph_node
        for rel in path.relationships:
            start = str(rel.start_node.get("entity_id") or rel.start_node.get("claim_id") or rel.start_node.element_id)
            end = str(rel.end_node.get("entity_id") or rel.end_node.get("claim_id") or rel.end_node.element_id)
            edges.append(
                GraphEdgeDTO(
                    id=str(rel.element_id),
                    source=start,
                    target=end,
                    edge_type=rel.type,
                )
            )
    return GraphNeighborhood(center_entity_id=entity_id, depth=depth, nodes=list(nodes.values()), edges=edges)


def status_score(status: str) -> float:
    return {
        "verified": 1.0,
        "auto_verified": 0.9,
        "extracted": 0.7,
        "candidate": 0.5,
        "conflicting": 0.3,
        "deprecated": 0.1,
        "rejected": 0.0,
    }.get(status, 0.4)


def rank_claim_records(records: list[Any], limit: int) -> list[RankedClaimDTO]:
    ranked: list[RankedClaimDTO] = []
    for record in records:
        claim_id = str(record["claim_id"])
        confidence = float(record.get("confidence") or 0.0)
        status = str(record.get("status") or "candidate")
        recency = str(record.get("latest_supporting_evidence_date") or record.get("claim_last_updated_at") or "")
        recency_bonus = 0.05 if recency else 0.0
        score = min(1.0, confidence * status_score(status) + recency_bonus)
        ranked.append(
            RankedClaimDTO(
                claim_id=claim_id,
                score=score,
                status=status,  # type: ignore[arg-type]
                confidence=confidence,
            )
        )
    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked[:limit]


def claim_record_to_evidence(record: Any) -> EvidenceRecordDTO:
    claim = record["c"]
    span = record.get("s")
    document = record.get("d")
    claim_props = dict(claim)
    span_dto = None
    if span is not None:
        span_props = dict(span)
        span_dto = SourceSpanDTO(
            source_span_id=str(span_props.get("source_span_id", "")),
            document_id=str(span_props.get("document_id", "")),
            page_number=int(span_props.get("page_number") or 1),
            raw_text=str(span_props.get("raw_text", "")),
            char_start=int(span_props.get("char_start") or 0),
            char_end=int(span_props.get("char_end") or 0),
            source_type=str(span_props.get("source_type") or "text"),
            table_block_id=span_props.get("table_block_id"),
        )
    return EvidenceRecordDTO(
        claim_id=str(claim_props.get("claim_id", "")),
        statement=str(claim_props.get("statement", "")),
        confidence=float(claim_props.get("confidence") or 0.0),
        status=str(claim_props.get("status") or "candidate"),  # type: ignore[arg-type]
        source_span=span_dto,
        document_id=str(dict(document).get("document_id")) if document is not None else None,
        access_level=str(dict(document).get("access_level")) if document is not None else None,
    )


def neighbor_query_for_depth(depth: int) -> str:
    hop = max(1, min(depth, 3))
    return f"""
MATCH (center:Entity {{entity_id: $entity_id}})
MATCH path = (center)-[*1..{hop}]-(neighbor)
WHERE neighbor:Entity OR neighbor:Claim OR neighbor:Measurement OR neighbor:SourceSpan OR neighbor:Document
RETURN path
LIMIT $limit
"""
