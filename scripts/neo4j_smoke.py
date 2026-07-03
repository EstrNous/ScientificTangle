import argparse
import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_ROOT = ROOT / "services" / "knowledge"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(KNOWLEDGE_ROOT) not in sys.path:
    sys.path.insert(0, str(KNOWLEDGE_ROOT))

from adapters.driver import create_driver
from adapters.dto import ClaimDTO, ClaimsBundleDTO, DocumentDTO, EntityDTO, SourceSpanDTO
from adapters.neo4j_adapter import Neo4jKnowledgeAdapter
from adapters.schema import reset_database, seed_schema_registry


async def run_smoke(reset: bool) -> dict:
    uri = os.getenv("NEO4J_URL", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "neo4j_pass")
    driver = create_driver(uri, user, password)
    adapter = Neo4jKnowledgeAdapter(driver)
    if reset:
        await reset_database(driver, request_id="neo4j-smoke-reset")
    bootstrap = await seed_schema_registry(driver, request_id="neo4j-smoke-bootstrap")
    document_id = f"doc-{uuid.uuid4().hex[:8]}"
    span_id = f"span-{uuid.uuid4().hex[:8]}"
    entity_id = f"ent-{uuid.uuid4().hex[:8]}"
    claim_id = f"claim-{uuid.uuid4().hex[:8]}"
    bundle = ClaimsBundleDTO(
        documents=[DocumentDTO(document_id=document_id, title="Smoke", source_type="article")],
        spans=[
            SourceSpanDTO(
                source_span_id=span_id,
                document_id=document_id,
                page_number=1,
                raw_text="Ni 92 %",
                char_start=0,
                char_end=7,
            )
        ],
        entities=[EntityDTO(entity_id=entity_id, canonical_name="nickel", domain_type="Material")],
        claims=[
            ClaimDTO(
                claim_id=claim_id,
                status="verified",
                confidence=0.9,
                statement="Ni 92 %",
                source_span_ids=[span_id],
                entity_ids=[entity_id],
            )
        ],
    )
    written = await adapter.write_bundle(bundle, request_id="neo4j-smoke-write")
    aliases = await adapter.resolve_aliases("nickel", request_id="neo4j-smoke-alias")
    ready = await adapter.ping(request_id="neo4j-smoke-ping")
    await driver.close()
    return {
        "bootstrap": bootstrap.model_dump(mode="json"),
        "written": written,
        "resolve_aliases": aliases,
        "ping": ready,
        "claim_id": claim_id,
        "source_span_id": span_id,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--output", default="tmp/neo4j_smoke.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = asyncio.run(run_smoke(args.reset))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
