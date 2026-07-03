from unittest.mock import AsyncMock, MagicMock

import pytest

from adapters.dto import ClaimsBundleDTO, ClaimDTO, DocumentDTO, SourceSpanDTO
from adapters.neo4j_adapter import Neo4jKnowledgeAdapter


@pytest.fixture
def adapter() -> Neo4jKnowledgeAdapter:
    driver = MagicMock()
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    session.execute_write = AsyncMock(return_value=3)
    session.run = AsyncMock()
    driver.session.return_value = session
    return Neo4jKnowledgeAdapter(driver)


@pytest.mark.asyncio
async def test_write_bundle_uses_execute_write(adapter: Neo4jKnowledgeAdapter) -> None:
    bundle = ClaimsBundleDTO(
        documents=[DocumentDTO(document_id="d1", title="T", source_type="article")],
        spans=[
            SourceSpanDTO(
                source_span_id="span1",
                document_id="d1",
                page_number=1,
                raw_text="text",
                char_start=0,
                char_end=4,
            )
        ],
        claims=[
            ClaimDTO(
                claim_id="c1",
                statement="claim",
                confidence=0.9,
                status="verified",
                source_span_ids=["span1"],
            )
        ],
    )
    result = await adapter.write_bundle(bundle, request_id="req-1")
    assert result is True
    adapter._driver.session.assert_called()
    session = adapter._driver.session.return_value
    session.execute_write.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_aliases_empty_mention(adapter: Neo4jKnowledgeAdapter) -> None:
    assert await adapter.resolve_aliases("   ") == []
