import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.contracts import ExtractionArtifact
from app.main import app
from shared.contracts import EvidenceBundle, EvidenceItem, NormalizedDocument, QueryIR, SourceSpan, TableBlock


client = TestClient(app)


def test_confirmed_artifact_requires_source_span() -> None:
    with pytest.raises(ValidationError):
        ExtractionArtifact(
            kind="claim",
            value="Nickel recovery is 82 %",
            confidence=0.91,
            status="confirmed",
        )


def test_structured_extraction_confirms_only_sourced_measurements() -> None:
    span = SourceSpan(
        document_id="doc-1",
        page=1,
        start_offset=0,
        end_offset=72,
        text="The flotation test achieved nickel recovery 82 % at flow 1.5 m/s.",
        source_type="text",
    )
    document = NormalizedDocument(
        id="doc-1",
        source_type="article",
        title="Nickel flotation test",
        content=span.text,
        source_spans=[span],
    )

    response = client.post("/v1/extraction/structured", json={"document": document.model_dump(mode="json")})

    assert response.status_code == 200
    payload = response.json()
    confirmed = payload["confirmed"]
    assert any(item["kind"] == "measurement" and item["status"] == "confirmed" for item in confirmed)
    assert all(item["source_span_ids"] for item in confirmed)
    assert all(item["source_spans"] for item in confirmed)


def test_structured_extraction_covers_domain_artifact_types() -> None:
    span = SourceSpan(
        document_id="doc-domain",
        page=1,
        start_offset=0,
        end_offset=180,
        text="Ni, никель и халькопирит обрабатываются флотацией в колонной флотации. Скорость потока 1.2 м/с. Иванов И. И. показал вывод для России в 2024.",
        source_type="text",
    )
    document = NormalizedDocument(
        id="doc-domain",
        source_type="article",
        title="Domain extraction",
        content=span.text,
        source_spans=[span],
    )

    response = client.post("/v1/extraction/structured", json={"document": document.model_dump(mode="json")})

    assert response.status_code == 200
    kinds = {item["kind"] for item in response.json()["confirmed"]}
    assert {"material", "substance", "process", "equipment", "property", "date", "geography", "expert", "conclusion"} <= kinds


def test_structured_extraction_moves_unsourced_claims_to_candidates() -> None:
    document = NormalizedDocument(
        id="doc-2",
        source_type="report",
        title="Unsourced report",
        content="The report claims recovery 82 % but has no span evidence.",
    )

    response = client.post("/v1/extraction/structured", json={"document": document.model_dump(mode="json")})

    assert response.status_code == 200
    payload = response.json()
    assert payload["confirmed"] == []
    assert payload["candidates"]
    assert any("missing_source_span" in item["reason_codes"] for item in payload["candidates"])
    assert payload["unsupported_warnings"]


def test_structured_extraction_demotes_low_confidence_confirmed_layer() -> None:
    span = SourceSpan(
        document_id="doc-threshold",
        page=1,
        start_offset=0,
        end_offset=45,
        text="Flotation relates Ni and Cu in this source.",
        source_type="text",
    )
    document = NormalizedDocument(
        id="doc-threshold",
        source_type="article",
        title="Threshold check",
        content=span.text,
        source_spans=[span],
    )

    response = client.post(
        "/v1/extraction/structured",
        json={"document": document.model_dump(mode="json"), "confirmed_confidence_threshold": 0.8},
    )

    assert response.status_code == 200
    payload = response.json()
    assert any(item["kind"] == "entity" and "low_confidence" in item["reason_codes"] for item in payload["candidates"])


def test_table_without_source_span_is_schema_candidate() -> None:
    table = TableBlock(
        id="table-1",
        document_id="doc-3",
        page=2,
        headers=["parameter", "value"],
        rows=[["flow", "1.2 m/s"]],
    )
    document = NormalizedDocument(
        id="doc-3",
        source_type="report",
        title="Table only",
        content="",
        table_blocks=[table],
    )

    response = client.post("/v1/extraction/structured", json={"document": document.model_dump(mode="json")})

    assert response.status_code == 200
    payload = response.json()
    assert payload["confirmed"] == []
    assert any({"missing_source_span", "schema_candidate"}.issubset(set(item["reason_codes"])) for item in payload["candidates"])


def test_query_ir_keeps_numeric_geo_time_and_source_constraints() -> None:
    question = (
        "Методы обессоливания воды в России: сульфаты, хлориды, Ca, Mg, Na по 200-300 мг/л, "
        "сухой остаток не более 1000 мг/дм3 за последние 5 лет по публикациям"
    )

    response = client.post("/v1/query-ir", json={"raw_query": question})

    assert response.status_code == 200
    payload = response.json()
    constraints = payload["constraints"]
    assert payload["query_ir"]["intent"] == "find_methods"
    assert len(constraints["numeric_constraints"]) >= 2
    assert constraints["numeric_constraints"][0]["operator"] == "range"
    assert constraints["numeric_constraints"][0]["range_min"] == 200
    assert constraints["numeric_constraints"][0]["range_max"] == 300
    assert constraints["numeric_constraints"][1]["operator"] == "le"
    assert constraints["numeric_constraints"][1]["unit"] == "mg/dm3"
    assert constraints["time_constraints"]["relative_years"] == 5
    assert "Россия" in constraints["geo_constraints"]
    assert "publication" in constraints["source_type_constraints"]


def test_answer_synthesis_does_not_present_candidates_as_facts() -> None:
    query_ir = QueryIR(raw_query="What is supported?")
    evidence_bundle = EvidenceBundle(query_ir=query_ir)
    candidate = ExtractionArtifact(
        kind="claim",
        value="Candidate unsupported fact",
        confidence=0.4,
        status="candidate",
        reason_codes=["missing_source_span"],
    )

    response = client.post(
        "/v1/answers/synthesize",
        json={
            "query_ir": query_ir.model_dump(mode="json"),
            "evidence_bundle": evidence_bundle.model_dump(mode="json"),
            "candidate_items": [candidate.model_dump(mode="json")],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "Candidate unsupported fact" not in payload["answer"]["answer_text"]
    assert payload["candidate_count"] == 1
    assert payload["unsupported_warnings"][0]["statement"] == "Candidate unsupported fact"
    assert payload["answer"]["sources_count"] == 0


def test_rerank_scores_source_span_matches() -> None:
    query_ir = QueryIR(raw_query="nickel recovery 82 %", filters={"numeric_constraints": [{"value": 82, "unit": "%"}]})
    span = SourceSpan(
        document_id="doc-4",
        page=1,
        start_offset=0,
        end_offset=32,
        text="Nickel recovery reached 82 %.",
        source_type="text",
    )
    evidence_item = EvidenceItem(source_span=span, relevance_score=0.2, extraction_method="numeric")

    response = client.post(
        "/v1/rerank",
        json={
            "query_ir": query_ir.model_dump(mode="json"),
            "evidence_items": [evidence_item.model_dump(mode="json")],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["scored_items"][0]["score"] > 0.2
    assert "source_span_present" in payload["scored_items"][0]["reasons"]


def test_schema_and_prompt_registry_are_versioned() -> None:
    schemas = client.get("/v1/schemas")
    prompts = client.get("/v1/prompts")

    assert schemas.status_code == 200
    assert prompts.status_code == 200
    assert {entry["version"] for entry in schemas.json()["schemas"]} >= {"structured_extraction.v1", "query_ir.v1"}
    assert {entry["version"] for entry in prompts.json()["prompts"]} >= {"structured_extraction.v1", "query_ir.v1"}


def test_model_status_reports_provider_configuration() -> None:
    response = client.get("/v1/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "yandex"
    assert isinstance(payload["yandex_configured"], bool)
    assert payload["mode"] in {"llm", "deterministic_degraded"}
    if payload["yandex_configured"]:
        assert payload["mode"] == "llm"
    else:
        assert payload["mode"] == "deterministic_degraded"


def test_conflicts_gaps_interests_notifications_and_jsonld() -> None:
    query_ir = QueryIR(raw_query="Россия никель скорость 1.2 м/с", filters={"numeric_constraints": [{"value": 1.2, "unit": "m/s"}], "geo_constraints": ["Россия"]})
    span = SourceSpan(
        document_id="doc-top",
        page=1,
        start_offset=0,
        end_offset=70,
        text="В России скорость потока католита составила 1.2 м/с.",
        source_type="text",
    )
    evidence_item = EvidenceItem(source_span=span, relevance_score=0.9, extraction_method="numeric")
    evidence_bundle = EvidenceBundle(query_ir=query_ir, evidence_items=[evidence_item], total_found=1)
    first = ExtractionArtifact(kind="measurement", value="1.2 m/s", confidence=0.9, status="confirmed", source_span_ids=["s1"], source_spans=[span])
    second = ExtractionArtifact(kind="measurement", value="2.4 m/s", confidence=0.9, status="confirmed", source_span_ids=["s1"], source_spans=[span])

    conflicts = client.post("/v1/conflicts/detect", json={"artifacts": [first.model_dump(mode="json"), second.model_dump(mode="json")]})
    gaps = client.post(
        "/v1/gaps/suggest",
        json={"query_ir": query_ir.model_dump(mode="json"), "evidence_bundle": evidence_bundle.model_dump(mode="json"), "candidates": []},
    )
    interests = client.post("/v1/interests/extract", json={"text": "Интересуют никель, флотация, колонная флотация и Россия"})
    notification = client.post(
        "/v1/notifications/match",
        json={"interests": interests.json()["interests"], "artifacts": [first.model_dump(mode="json")]},
    )
    answer_response = client.post(
        "/v1/answers/synthesize",
        json={"query_ir": query_ir.model_dump(mode="json"), "evidence_bundle": evidence_bundle.model_dump(mode="json")},
    )
    jsonld = client.post("/v1/jsonld/enrich", json={"answer": answer_response.json()["answer"]})

    assert conflicts.status_code == 200
    assert conflicts.json()["conflicts"]
    assert gaps.status_code == 200
    assert interests.status_code == 200
    assert interests.json()["interests"]
    assert notification.status_code == 200
    assert jsonld.status_code == 200
    assert jsonld.json()["jsonld"]["@type"] == "st:Answer"
