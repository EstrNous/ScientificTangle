import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from shared.contracts import NormalizedDocument, SourceSpan


pytestmark = pytest.mark.skipif(
    not settings.yandex_enabled,
    reason="Yandex API credentials are not configured",
)

client = TestClient(app)


def test_yandex_live_smoke_structured_query_and_answer() -> None:
    span = SourceSpan(
        document_id="live-smoke-doc",
        page=1,
        start_offset=0,
        end_offset=76,
        text="Флотация никеля в России показала извлекаемость 82 % в опубликованном источнике.",
        source_type="text",
    )
    document = NormalizedDocument(
        id="live-smoke-doc",
        source_type="article",
        title="Live smoke",
        content=span.text,
        source_spans=[span],
    )

    extraction = client.post("/v1/extraction/structured", json={"document": document.model_dump(mode="json")})
    query_ir = client.post("/v1/query-ir", json={"raw_query": "флотация никеля в России 82 %"})

    assert extraction.status_code == 200
    assert query_ir.status_code == 200
    assert extraction.json()["mode"] == "llm"
    assert query_ir.json()["mode"] == "llm"
    assert extraction.json()["confirmed"]
    assert query_ir.json()["query_ir"]["filters"]["numeric_constraints"]
