from __future__ import annotations

import uuid
from typing import Any

from neo4j import AsyncDriver

from shared.contracts import QueryIR

from . import queries
from .dto import (
    ClaimDTO,
    ClaimsBundleDTO,
    ConflictDTO,
    EntityID,
    EvidenceRecordDTO,
    FactVersionDTO,
    FactVersionHistoryDTO,
    GapDTO,
    GraphNeighborhood,
    GraphSubgraphDTO,
    GroupComparisonDTO,
    MeasurementAggregateDTO,
    NeighborhoodFallbackResultDTO,
    RankedClaimDTO,
    SourceSpanDTO,
)
from .operations import (
    claim_record_to_evidence,
    neighbor_query_for_depth,
    path_records_to_neighborhood,
    rank_claim_records,
    records_to_subgraph,
    subgraph_dto_to_contract,
    write_bundle_tx,
)
from .query_compiler import compile_query_ir


class Neo4jKnowledgeAdapter:
    def __init__(self, driver: AsyncDriver) -> None:
        self._driver = driver

    async def ping(self, request_id: str | None = None) -> bool:
        async with self._driver.session() as session:
            result = await session.run(queries.PING)
            record = await result.single()
            return bool(record and record.get("ok") == 1)

    async def write_claims_bundle(
        self,
        claims: list[ClaimDTO],
        spans: list[SourceSpanDTO],
        bundle: ClaimsBundleDTO | None = None,
        request_id: str | None = None,
    ) -> bool:
        payload = bundle or ClaimsBundleDTO(claims=claims, spans=spans)
        if claims and not payload.claims:
            payload.claims = claims
        if spans and not payload.spans:
            payload.spans = spans
        async def _write(tx: Any) -> int:
            return await write_bundle_tx(tx, payload)

        async with self._driver.session() as session:
            written = await session.execute_write(_write)
            return written > 0

    async def write_bundle(self, bundle: ClaimsBundleDTO, request_id: str | None = None) -> bool:
        return await self.write_claims_bundle(bundle.claims, bundle.spans, bundle=bundle, request_id=request_id)

    async def resolve_aliases(self, mention: str, request_id: str | None = None, limit: int = 10) -> list[EntityID]:
        normalized = mention.strip()
        if not normalized:
            return []
        async with self._driver.session() as session:
            try:
                result = await session.run(
                    queries.RESOLVE_ALIAS_FULLTEXT,
                    mention=normalized,
                    limit=limit,
                )
            except Exception:
                result = await session.run(
                    queries.RESOLVE_ALIAS_CONTAINS,
                    mention=normalized,
                    limit=limit,
                )
            records = [record async for record in result]
        entity_ids = [str(record["entity_id"]) for record in records if record.get("entity_id")]
        return list(dict.fromkeys(entity_ids))

    async def find_conflicts(self, entity_id: str, request_id: str | None = None) -> list[ConflictDTO]:
        async with self._driver.session() as session:
            result = await session.run(queries.FIND_CONFLICTS, entity_id=entity_id)
            records = [record async for record in result]
        conflicts: list[ConflictDTO] = []
        for record in records:
            conflicts.append(
                ConflictDTO(
                    conflict_id=uuid.uuid4().hex[:16],
                    entity_id=entity_id,
                    claim_ids=[str(record["claim_id_a"]), str(record["claim_id_b"])],
                    measurement_ids=[str(item) for item in record.get("measurement_ids", []) if item],
                    reason=str(record.get("reason", "conflict")),
                    confidence=0.8,
                )
            )
        return conflicts

    async def find_missing_edges(self, domain_profile: str, request_id: str | None = None) -> list[GapDTO]:
        async with self._driver.session() as session:
            result = await session.run(queries.FIND_MISSING_EDGES)
            records = [record async for record in result]
        gaps: list[GapDTO] = []
        for record in records:
            gaps.append(
                GapDTO(
                    gap_id=uuid.uuid4().hex[:16],
                    domain_profile=domain_profile,
                    description="Отсутствует измерение выхода для связки процесс-материал",
                    expected_relation="PRODUCES_OUTPUT",
                    entity_ids=[str(record.get("process_id", "")), str(record.get("material_id", ""))],
                    priority="medium",
                )
            )
        return gaps

    async def build_subgraph(
        self,
        query_ir: QueryIR,
        access_levels: list[str] | None = None,
        request_id: str | None = None,
    ) -> GraphSubgraphDTO:
        plan = compile_query_ir(query_ir, access_levels=access_levels)
        entity_ids = await self.resolve_aliases(" ".join(plan.entity_hints), request_id=request_id) if plan.entity_hints else []
        async with self._driver.session() as session:
            result = await session.run(
                queries.BUILD_SUBGRAPH,
                entity_ids=entity_ids,
                entity_hints=plan.entity_hints,
                access_levels=plan.access_levels,
                limit=plan.limit,
            )
            records = [record async for record in result]
        return records_to_subgraph(records)

    async def build_subgraph_by_evidence(
        self,
        claim_ids: list[str],
        entity_ids: list[str],
        source_span_ids: list[str],
        request_id: str | None = None,
    ) -> GraphSubgraphDTO:
        if not claim_ids and not entity_ids and not source_span_ids:
            return GraphSubgraphDTO()
        async with self._driver.session() as session:
            result = await session.run(
                queries.BUILD_SUBGRAPH_BY_EVIDENCE,
                claim_ids=claim_ids,
                entity_ids=entity_ids,
                source_span_ids=source_span_ids,
            )
            records = [record async for record in result]
        return records_to_subgraph(records)

    async def expand_neighbors(
        self,
        entity_id: str,
        depth: int = 1,
        request_id: str | None = None,
        limit: int = 80,
    ) -> GraphNeighborhood:
        query = neighbor_query_for_depth(depth)
        async with self._driver.session() as session:
            result = await session.run(query, entity_id=entity_id, limit=limit)
            records = [record async for record in result]
        return path_records_to_neighborhood(entity_id, depth, records)

    async def find_entities(
        self,
        name: str | None = None,
        domain_type: str | None = None,
        limit: int = 50,
        request_id: str | None = None,
    ) -> list[EntityID]:
        async with self._driver.session() as session:
            result = await session.run(
                queries.FIND_ENTITIES,
                name=name,
                domain_type=domain_type,
                limit=limit,
            )
            records = [record async for record in result]
        return [str(dict(record["e"]).get("entity_id")) for record in records if record.get("e")]

    async def filter_by_constraints(
        self,
        query_ir: QueryIR,
        access_levels: list[str] | None = None,
        request_id: str | None = None,
    ) -> GraphSubgraphDTO:
        plan = compile_query_ir(query_ir, access_levels=access_levels)
        numeric = query_ir.numeric_filter
        time_constraints = query_ir.filters.get("time_constraints", {}) if isinstance(query_ir.filters, dict) else {}
        async with self._driver.session() as session:
            result = await session.run(
                queries.FILTER_BY_CONSTRAINTS,
                access_levels=plan.access_levels,
                min_confidence=query_ir.filters.get("min_confidence") if isinstance(query_ir.filters, dict) else None,
                status=query_ir.filters.get("status") if isinstance(query_ir.filters, dict) else None,
                geo_name=query_ir.geo_filter.location_name if query_ir.geo_filter else None,
                numeric_min=numeric.range_min if numeric else None,
                numeric_max=numeric.range_max if numeric else None,
                published_after=time_constraints.get("from") if isinstance(time_constraints, dict) else None,
                published_before=time_constraints.get("to") if isinstance(time_constraints, dict) else None,
                limit=plan.limit,
            )
            records = [record async for record in result]
        return records_to_subgraph(records)

    async def aggregate_measurements(
        self,
        entity_id: str | None = None,
        request_id: str | None = None,
    ) -> list[MeasurementAggregateDTO]:
        async with self._driver.session() as session:
            result = await session.run(queries.AGGREGATE_MEASUREMENTS, entity_id=entity_id)
            records = [record async for record in result]
        aggregates: list[MeasurementAggregateDTO] = []
        for record in records:
            aggregates.append(
                MeasurementAggregateDTO(
                    group_key=str(record.get("group_key") or "default"),
                    count=int(record.get("count") or 0),
                    avg_value=float(record["avg_value"]) if record.get("avg_value") is not None else None,
                    min_value=float(record["min_value"]) if record.get("min_value") is not None else None,
                    max_value=float(record["max_value"]) if record.get("max_value") is not None else None,
                    unit=str(record.get("unit") or ""),
                )
            )
        return aggregates

    async def compare_groups(
        self,
        group_a_key: str,
        group_b_key: str,
        request_id: str | None = None,
    ) -> GroupComparisonDTO:
        async with self._driver.session() as session:
            result = await session.run(
                queries.COMPARE_GROUPS,
                group_a_key=group_a_key,
                group_b_key=group_b_key,
            )
            records = [record async for record in result]
        values: dict[str, tuple[float | None, str]] = {}
        for record in records:
            key = str(record.get("group_key"))
            values[key] = (
                float(record["avg_value"]) if record.get("avg_value") is not None else None,
                str(record.get("unit") or ""),
            )
        a_avg, unit = values.get(group_a_key, (None, ""))
        b_avg, unit_b = values.get(group_b_key, (unit, ""))
        delta = None
        if a_avg is not None and b_avg is not None:
            delta = a_avg - b_avg
        return GroupComparisonDTO(
            group_a_key=group_a_key,
            group_b_key=group_b_key,
            group_a_avg=a_avg,
            group_b_avg=b_avg,
            delta=delta,
            unit=unit or unit_b,
        )

    async def retrieve_evidence(
        self,
        query_ir: QueryIR,
        access_levels: list[str] | None = None,
        request_id: str | None = None,
    ) -> list[EvidenceRecordDTO]:
        plan = compile_query_ir(query_ir, access_levels=access_levels)
        numeric = query_ir.numeric_filter
        time_constraints = query_ir.filters.get("time_constraints", {}) if isinstance(query_ir.filters, dict) else {}
        async with self._driver.session() as session:
            result = await session.run(
                queries.RETRIEVE_EVIDENCE,
                access_levels=plan.access_levels,
                entity_hints=plan.entity_hints,
                geo_name=query_ir.geo_filter.location_name if query_ir.geo_filter else None,
                numeric_min=numeric.range_min if numeric else None,
                numeric_max=numeric.range_max if numeric else None,
                published_after=time_constraints.get("from") if isinstance(time_constraints, dict) else None,
                published_before=time_constraints.get("to") if isinstance(time_constraints, dict) else None,
                limit=plan.limit,
            )
            records = [record async for record in result]
        return [claim_record_to_evidence(record) for record in records]

    async def neighborhood_fallback(
        self,
        query_ir: QueryIR,
        access_levels: list[str] | None = None,
        request_id: str | None = None,
    ) -> NeighborhoodFallbackResultDTO:
        evidence = await self.retrieve_evidence(query_ir, access_levels=access_levels, request_id=request_id)
        if evidence:
            return NeighborhoodFallbackResultDTO(evidence=evidence, used_fallback=False)
        expanded_entity_ids: list[str] = []
        seed_entity_ids: list[str] = []
        for hint in query_ir.entities:
            seed_entity_ids.extend(await self.resolve_aliases(hint, request_id=request_id))
        for entity_id in list(dict.fromkeys(seed_entity_ids))[:3]:
            neighborhood = await self.expand_neighbors(entity_id, depth=1, request_id=request_id)
            neighbor_entities = [
                node.id for node in neighborhood.nodes if node.node_type == "Entity" and node.id != entity_id
            ]
            expanded_entity_ids.extend(neighbor_entities)
        expanded_entity_ids = list(dict.fromkeys(expanded_entity_ids))[:10]
        if not expanded_entity_ids:
            return NeighborhoodFallbackResultDTO(evidence=[], used_fallback=True)
        expanded_ir = query_ir.model_copy(
            update={"entities": list(dict.fromkeys([*query_ir.entities, *expanded_entity_ids]))}
        )
        fallback_evidence = await self.retrieve_evidence(
            expanded_ir,
            access_levels=access_levels,
            request_id=request_id,
        )
        return NeighborhoodFallbackResultDTO(
            evidence=fallback_evidence,
            used_fallback=True,
            expanded_entity_ids=expanded_entity_ids,
        )

    async def get_fact_versions(
        self,
        claim_id: str,
        request_id: str | None = None,
    ) -> FactVersionHistoryDTO:
        async with self._driver.session() as session:
            result = await session.run(queries.GET_FACT_VERSIONS, claim_id=claim_id)
            record = await result.single()
        if record is None:
            return FactVersionHistoryDTO(claim_id=claim_id, claim_version=0, status="unknown")
        versions: list[FactVersionDTO] = []
        for node in record.get("versions", []):
            if node is None:
                continue
            props = dict(node)
            versions.append(
                FactVersionDTO(
                    fact_version_id=str(props.get("fact_version_id", "")),
                    claim_id=str(props.get("claim_id", claim_id)),
                    version=int(props.get("version") or 0),
                    status=str(props.get("status", "")),
                    recorded_at=str(props.get("recorded_at")) if props.get("recorded_at") is not None else None,
                )
            )
        superseded = [str(item) for item in record.get("superseded_claim_ids", []) if item]
        return FactVersionHistoryDTO(
            claim_id=str(record.get("claim_id", claim_id)),
            claim_version=int(record.get("claim_version") or 0),
            status=str(record.get("status", "")),
            versions=versions,
            superseded_claim_ids=superseded,
        )

    async def rank_claims(
        self,
        claim_ids: list[str],
        query_ir: QueryIR | None = None,
        request_id: str | None = None,
        limit: int = 20,
    ) -> list[RankedClaimDTO]:
        async with self._driver.session() as session:
            result = await session.run(queries.RANK_CLAIMS, claim_ids=claim_ids)
            records = [record async for record in result]
        effective_limit = query_ir.limit if query_ir else limit
        return rank_claim_records(records, effective_limit)
