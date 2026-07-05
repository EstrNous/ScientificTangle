import os
import uuid

import pytest
import pytest_asyncio
from adapters.driver import create_driver
from adapters.dto import ClaimDTO, ClaimsBundleDTO, DocumentDTO, EntityDTO, SourceSpanDTO
from adapters.neo4j_adapter import Neo4jKnowledgeAdapter
from adapters.schema import reset_database, seed_schema_registry

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_NEO4J_INTEGRATION") != "1",
    reason="Set RUN_NEO4J_INTEGRATION=1 with running Neo4j",
)


@pytest_asyncio.fixture
async def neo4j_adapter():
    uri = os.getenv("NEO4J_URL", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "neo4j_pass")
    driver = create_driver(uri, user, password)
    adapter = Neo4jKnowledgeAdapter(driver)
    await reset_database(driver, request_id="integration-reset")
    await seed_schema_registry(driver, request_id="integration-seed")
    yield adapter
    await driver.close()


@pytest.mark.asyncio
async def test_neo4j_bootstrap_has_constraints(neo4j_adapter: Neo4jKnowledgeAdapter) -> None:
    async with neo4j_adapter._driver.session() as session:
        result = await session.run("SHOW CONSTRAINTS YIELD name RETURN count(name) AS total")
        record = await result.single()
    assert record is not None
    assert int(record["total"]) >= 4


@pytest.mark.asyncio
async def test_neo4j_write_read_roundtrip(neo4j_adapter: Neo4jKnowledgeAdapter) -> None:
    document_id = f"doc-{uuid.uuid4().hex[:8]}"
    span_id = f"span-{uuid.uuid4().hex[:8]}"
    entity_id = f"ent-{uuid.uuid4().hex[:8]}"
    claim_id = f"claim-{uuid.uuid4().hex[:8]}"
    bundle = ClaimsBundleDTO(
        documents=[
            DocumentDTO(
                document_id=document_id,
                title="Integration doc",
                source_type="article",
                access_level="internal",
            )
        ],
        spans=[
            SourceSpanDTO(
                source_span_id=span_id,
                document_id=document_id,
                page_number=1,
                raw_text="Ni recovery 92 %",
                char_start=0,
                char_end=16,
            )
        ],
        entities=[
            EntityDTO(
                entity_id=entity_id,
                canonical_name="nickel",
                domain_type="Material",
                created_at="2026-01-01T00:00:00+00:00",
            )
        ],
        claims=[
            ClaimDTO(
                claim_id=claim_id,
                status="verified",
                confidence=0.92,
                statement="Ni recovery 92 %",
                claim_extracted_at="2026-01-01T00:00:00+00:00",
                claim_last_updated_at="2026-01-01T00:00:00+00:00",
                source_span_ids=[span_id],
                entity_ids=[entity_id],
                semantic_relations=[{"type": "USES_MATERIAL", "target_id": entity_id}],
            )
        ],
    )
    assert await neo4j_adapter.write_bundle(bundle, request_id="integration-write")

    seeded = await neo4j_adapter.resolve_aliases("nickel", request_id="integration-resolve")
    assert seeded

    neighborhood = await neo4j_adapter.expand_neighbors(entity_id, depth=1, request_id="integration-neighbors")
    assert neighborhood.center_entity_id == entity_id
    assert any(node.id == claim_id for node in neighborhood.nodes)

    async with neo4j_adapter._driver.session() as session:
        result = await session.run(
            """
            MATCH (c:Claim {claim_id: $claim_id})-[:DESCRIBED_IN]->(s:SourceSpan {source_span_id: $span_id})
            RETURN count(c) AS total
            """,
            claim_id=claim_id,
            span_id=span_id,
        )
        record = await result.single()
    assert record is not None
    assert int(record["total"]) == 1


@pytest.mark.asyncio
async def test_neo4j_subgraph_by_evidence_ids(neo4j_adapter: Neo4jKnowledgeAdapter) -> None:
    document_id = f"doc-{uuid.uuid4().hex[:8]}"
    span_id = f"span-{uuid.uuid4().hex[:8]}"
    entity_id = f"ent-{uuid.uuid4().hex[:8]}"
    claim_id = f"claim-{uuid.uuid4().hex[:8]}"
    bundle = ClaimsBundleDTO(
        documents=[
            DocumentDTO(
                document_id=document_id,
                title="Subgraph doc",
                source_type="article",
                access_level="internal",
            )
        ],
        spans=[
            SourceSpanDTO(
                source_span_id=span_id,
                document_id=document_id,
                page_number=1,
                raw_text="Cu grade 1.5 %",
                char_start=0,
                char_end=14,
            )
        ],
        entities=[
            EntityDTO(
                entity_id=entity_id,
                canonical_name="copper",
                domain_type="Material",
                created_at="2026-01-01T00:00:00+00:00",
            )
        ],
        claims=[
            ClaimDTO(
                claim_id=claim_id,
                status="verified",
                confidence=0.88,
                statement="Cu grade 1.5 %",
                claim_extracted_at="2026-01-01T00:00:00+00:00",
                claim_last_updated_at="2026-01-01T00:00:00+00:00",
                source_span_ids=[span_id],
                entity_ids=[entity_id],
            )
        ],
    )
    assert await neo4j_adapter.write_bundle(bundle, request_id="integration-subgraph-write")
    subgraph = await neo4j_adapter.build_subgraph_by_evidence(
        [claim_id], [entity_id], [span_id], ["public", "internal"]
    )
    assert claim_id in subgraph.claim_ids
    assert span_id in subgraph.source_span_ids
    assert any(node.id == entity_id for node in subgraph.nodes)

    versions = await neo4j_adapter.get_fact_versions(claim_id, request_id="integration-versions")
    assert versions.claim_id == claim_id
    assert versions.versions


@pytest.mark.asyncio
async def test_neo4j_filter_and_rank_claims(neo4j_adapter: Neo4jKnowledgeAdapter) -> None:
    from shared.contracts import QueryIR

    query_ir = QueryIR(raw_query="nickel", entities=["nickel"], limit=5)
    filtered = await neo4j_adapter.filter_by_constraints(query_ir, access_levels=["public", "internal"])
    assert isinstance(filtered.nodes, list)
    ranked = await neo4j_adapter.rank_claims([], query_ir=query_ir, limit=5)
    assert ranked == []


@pytest.mark.asyncio
async def test_neo4j_ping(neo4j_adapter: Neo4jKnowledgeAdapter) -> None:
    assert await neo4j_adapter.ping(request_id="integration-ping")
