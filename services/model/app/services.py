import hashlib
import json
import math
import re
import uuid
from difflib import SequenceMatcher
from typing import Any

try:
    from thefuzz import fuzz, process
except ImportError:
    fuzz = None
    process = None

from shared.contracts import AccessPolicy, AnswerPayload, EvidenceBundle, EvidenceItem, GeoContext, NormalizedDocument, Quantity, QueryIR, SourceSpan
from shared.utils.source_span import compute_source_span_id as source_span_id

from .contracts import (
    CONFIRMED_MIN_CONFIDENCE,
    AnswerSynthesisRequest,
    AnswerSynthesisResponse,
    ConflictDetectionRequest,
    ConflictDetectionResponse,
    ConflictSignal,
    DocumentProfileSuggestion,
    EmbeddingItem,
    EmbeddingRequest,
    EmbeddingResponse,
    ExtractionArtifact,
    GapSuggestion,
    GapSuggestionRequest,
    GapSuggestionResponse,
    JsonLdEnrichmentRequest,
    JsonLdEnrichmentResponse,
    ModelStatusResponse,
    NotificationMatch,
    NotificationMatchRequest,
    NotificationMatchResponse,
    QueryIRBuildRequest,
    QueryIRBuildResponse,
    RerankRequest,
    RerankResponse,
    ScoredEvidenceItem,
    StructuredExtractionRequest,
    StructuredExtractionResponse,
    UnsupportedWarning,
    UserInterest,
    UserInterestExtractionRequest,
    UserInterestExtractionResponse,
)
from .core.config import settings
from .yandex_client import YandexModelClient


DEGRADED_WARNING = "LLM API is not configured; deterministic degraded extraction is active"
NUMERIC_PATTERN = re.compile(
    r"(?P<operator><=|>=|≤|≥|<|>|до|не более|не менее|более|менее)?\s*"
    r"(?P<first>\d+(?:[,.]\d+)?)"
    r"(?:\s*[-–—]\s*(?P<second>\d+(?:[,.]\d+)?))?\s*"
    r"(?P<unit>%|мг/л|mg/l|мг/дм3|мг/дм³|г/л|g/l|м/с|m/s|л/с|l/s|°c|°C|кг/т|kg/t)",
    re.IGNORECASE,
)
CHEMICAL_PATTERN = re.compile(r"\b(?:Au|Ag|Mg|Ca|Na|Ni|Cu|Co|Fe|Zn|Pb|PGM|PGE|МПГ|ПГЭ)\b")
ALIAS_PATTERN = re.compile(r"(?P<long>[A-Za-zА-Яа-яЁё0-9][A-Za-zА-Яа-яЁё0-9\s-]{2,80}?)\s*\((?P<short>[A-Za-zА-Яа-яЁё0-9-]{2,16})\)")
SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?。])\s+|(?<=\.)\s+")
TOKEN_PATTERN = re.compile(r"[A-Za-zА-Яа-яЁё0-9%/.,-]+")

UNIT_ALIASES = {
    "мг/л": "mg/l",
    "mg/l": "mg/l",
    "мг/дм3": "mg/dm3",
    "мг/дм³": "mg/dm3",
    "г/л": "g/l",
    "g/l": "g/l",
    "м/с": "m/s",
    "m/s": "m/s",
    "л/с": "l/s",
    "l/s": "l/s",
    "%": "%",
    "°c": "C",
    "°C": "C",
    "кг/т": "kg/t",
    "kg/t": "kg/t",
}

GEO_TERMS = {
    "россия": "Россия",
    "россии": "Россия",
    "россий": "Россия",
    "за рубежом": "зарубежная практика",
    "зарубеж": "зарубежная практика",
    "норильск": "Норильский регион",
    "норильского": "Норильский регион",
    "кольский": "Кольский полуостров",
    "кольского": "Кольский полуостров",
}

SOURCE_TYPE_TERMS = {
    "публикац": "publication",
    "стать": "publication",
    "патент": "patent",
    "отчет": "technical_report",
    "отчёт": "technical_report",
    "норматив": "regulation",
}

CLAIM_TERMS = (
    "achieved",
    "shows",
    "reported",
    "recommended",
    "requires",
    "increases",
    "decreases",
    "составляет",
    "показал",
    "показано",
    "рекоменду",
    "требует",
    "влияет",
    "повышает",
    "снижает",
    "достигает",
)

PROCESS_TERMS = {
    "desalination": "process",
    "flotation": "process",
    "electroextraction": "process",
    "leaching": "process",
    "обессол": "process",
    "флотац": "process",
    "электроэкстракц": "process",
    "выщелач": "process",
    "закач": "process",
    "циркуляц": "process",
}
MATERIAL_TERMS = {
    "пентландит",
    "халькопирит",
    "пирротин",
    "миллерит",
    "лимонит",
    "гематит",
    "магнетит",
    "пиролюзит",
    "золото",
    "серебро",
    "платина",
    "палладий",
    "медь",
    "никель",
    "кобальт",
    "цинк",
    "сульфидн",
    "оксидн",
    "штейн",
    "шлак",
    "руда",
    "ферроникель",
}
EQUIPMENT_TERMS = {
    "дробилка",
    "мельница",
    "флотационная машина",
    "колонная флотация",
    "колонн",
    "электропечь",
    "дуговая печь",
    "конвертер",
    "электролизная ванна",
    "реактор",
    "насос",
    "скважина",
}
PROPERTY_TERMS = {
    "извлекаемость",
    "содержание",
    "скорость",
    "температура",
    "давление",
    "производительность",
    "стоимость",
    "сухой остаток",
    "качество",
    "концентрация",
}
EXPERT_PATTERN = re.compile(r"\b[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ]\.){1,2}|\b[A-Z][a-z]+(?:\s+[A-Z]\.){1,2}")
DATE_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b|\b\d{1,2}[./-]\d{1,2}[./-](?:19|20)?\d{2}\b")
MODEL_CACHE: dict[str, dict[str, Any]] = {}
FUZZY_ALIAS_THRESHOLD = 88

SEED_ALIASES = {
    "мпг": "металлы платиновой группы",
    "пгэ": "платиноидные элементы",
    "pgm": "металлы платиновой группы",
    "pge": "платиноидные элементы",
    "fe-ni": "ферроникель",
    "feni": "ферроникель",
    "cu-ni": "медно-никелевые руды",
    "ni": "никель",
    "cu": "медь",
    "co": "кобальт",
    "au": "золото",
    "ag": "серебро",
}

RU_EN_ALIASES = {
    "nickel": "никель",
    "copper": "медь",
    "cobalt": "кобальт",
    "gold": "золото",
    "silver": "серебро",
    "slag": "шлак",
    "matte": "штейн",
    "flotation": "флотация",
    "leaching": "выщелачивание",
    "desalination": "обессоливание",
    "electroextraction": "электроэкстракция",
}


def cache_key(operation: str, version: str, model_name: str, payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"{operation}:{version}:{model_name}:{digest}"


def cached_response(model_cls: type[Any], key: str) -> Any | None:
    cached = MODEL_CACHE.get(key)
    if cached is None:
        return None
    return model_cls.model_validate(cached)


def store_cache(key: str, response: Any) -> Any:
    MODEL_CACHE[key] = response.model_dump(mode="json")
    return response


def build_embeddings(request: EmbeddingRequest) -> EmbeddingResponse:
    client = YandexModelClient(settings)
    selected_model = select_embedding_model(request)
    key = cache_key("embeddings", "embeddings.v1", selected_model, request.model_dump(mode="json"))
    cached = cached_response(EmbeddingResponse, key)
    if cached:
        return cached
    warnings = []
    mode = "deterministic_degraded"
    embeddings = []
    if client.is_configured:
        try:
            embeddings = [
                EmbeddingItem(index=index, text=text, vector=client.embedding(text, selected_model, request.dimensions))
                for index, text in enumerate(request.texts)
            ]
            mode = "llm"
        except Exception as exc:
            warnings.append(f"Yandex embeddings failed, deterministic fallback used: {exc}")
    if not embeddings:
        embeddings = [
            EmbeddingItem(index=index, text=text, vector=hash_embedding(text, request.dimensions))
            for index, text in enumerate(request.texts)
        ]
        warnings.append(DEGRADED_WARNING)
    response = EmbeddingResponse(
        mode=mode,
        model_name=selected_model if mode == "llm" else request.model_name,
        dimensions=request.dimensions,
        embeddings=embeddings,
        warnings=warnings,
    )
    return store_cache(key, EmbeddingResponse.model_validate(response.model_dump()))


def select_embedding_model(request: EmbeddingRequest) -> str:
    if request.model_name != "deterministic-hash-v1":
        return request.model_name
    if settings.yandex_use_tuned_embeddings and settings.yandex_tuned_embedding_model_uri:
        return settings.yandex_tuned_embedding_model_uri
    if request.input_type == "query":
        return settings.yandex_embedding_query_model
    return settings.yandex_embedding_doc_model


def hash_embedding(text: str, dimensions: int) -> list[float]:
    values = []
    counter = 0
    while len(values) < dimensions:
        digest = hashlib.sha256(f"{counter}:{text}".encode("utf-8")).digest()
        values.extend((byte / 127.5) - 1.0 for byte in digest)
        counter += 1
    vector = values[:dimensions]
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [round(value / norm, 6) for value in vector]


def build_structured_extraction(request: StructuredExtractionRequest) -> StructuredExtractionResponse:
    document = request.document
    selected_model = settings.yandex_long_context_model
    key = cache_key("structured_extraction", "structured_extraction.v1", selected_model, request.model_dump(mode="json"))
    cached = cached_response(StructuredExtractionResponse, key)
    if cached:
        return cached
    span_index = {source_span_id(span): span for span in document.source_spans}
    confirmed: list[ExtractionArtifact] = []
    candidates: list[ExtractionArtifact] = []
    warnings: list[UnsupportedWarning] = []
    seen: set[tuple[str, str, str]] = set()
    llm_warnings: list[str] = []
    mode = "deterministic_degraded"

    client = YandexModelClient(settings)
    if client.is_configured:
        try:
            llm_response = build_llm_structured_extraction(client, request, span_index)
            for item in llm_response.confirmed:
                add_artifact(item, confirmed, candidates, seen)
            for item in llm_response.candidates:
                add_artifact(item, confirmed, candidates, seen)
            warnings.extend(llm_response.unsupported_warnings)
            llm_warnings.extend(llm_response.warnings)
            mode = "llm"
        except Exception as exc:
            llm_warnings.append(f"Yandex structured extraction failed, deterministic fallback used: {exc}")

    for span_id, span in span_index.items():
        add_span_artifacts(span_id, span, confirmed, candidates, warnings, seen)

    add_table_artifacts(document, span_index, confirmed, candidates, warnings, seen)

    if not document.source_spans:
        add_unsourced_content_candidates(document, candidates, warnings, seen)

    confirmed, demoted_candidates = apply_confirmed_threshold(confirmed, request.confirmed_confidence_threshold)
    candidates = [*demoted_candidates, *candidates]
    warnings.extend(
        UnsupportedWarning(statement=item.value, reason_codes=item.reason_codes, source_span_ids=item.source_span_ids)
        for item in demoted_candidates
    )
    confirmed = confirmed[: request.max_artifacts]
    candidates = candidates[: request.max_artifacts]
    profile = suggest_document_profile(document)
    response_warnings = llm_warnings
    if mode == "deterministic_degraded":
        response_warnings = [*response_warnings, DEGRADED_WARNING]
    response = StructuredExtractionResponse(
        mode=mode,
        document_id=document.id,
        profile=profile,
        confirmed=confirmed,
        candidates=candidates,
        unsupported_warnings=warnings,
        warnings=response_warnings,
    )
    return store_cache(key, StructuredExtractionResponse.model_validate(response.model_dump()))


def build_llm_structured_extraction(
    client: YandexModelClient,
    request: StructuredExtractionRequest,
    span_index: dict[str, SourceSpan],
) -> StructuredExtractionResponse:
    document = request.document
    payload = {
        "document": document.model_dump(mode="json"),
        "source_span_ids": list(span_index),
        "max_artifacts": request.max_artifacts,
        "confirmed_confidence_threshold": request.confirmed_confidence_threshold,
    }
    data = complete_json_with_fallback(
        client,
        "Extract structured evidence-first artifacts. Return confirmed items only when source_span_ids point to provided source spans. Put weak or unsourced findings into candidates with reason_codes.",
        json_dumps(payload),
        StructuredExtractionResponse.model_json_schema(),
        settings.yandex_long_context_model,
        [settings.yandex_chat_model, settings.yandex_fast_model],
    )
    data.setdefault("profile", suggest_document_profile(document).model_dump(mode="json"))
    confirmed: list[ExtractionArtifact] = []
    candidates: list[ExtractionArtifact] = []
    warnings = [
        UnsupportedWarning.model_validate(item)
        for item in data.get("unsupported_warnings", [])
        if isinstance(item, dict) and item.get("statement")
    ]
    seen: set[tuple[str, str, str]] = set()
    for item in [*data.get("confirmed", []), *data.get("candidates", [])]:
        if not isinstance(item, dict):
            continue
        try:
            normalized = normalize_llm_artifact(item, span_index)
        except (TypeError, ValueError):
            continue
        add_artifact(normalized, confirmed, candidates, seen)
        if normalized.status != "confirmed":
            warnings.append(UnsupportedWarning(statement=normalized.value, reason_codes=normalized.reason_codes, source_span_ids=normalized.source_span_ids))
    return StructuredExtractionResponse(
        mode="llm",
        document_id=document.id,
        profile=DocumentProfileSuggestion.model_validate(data["profile"]),
        confirmed=confirmed,
        candidates=candidates,
        unsupported_warnings=warnings,
        warnings=[str(item) for item in data.get("warnings", [])],
    )


def normalize_llm_artifact(raw_artifact: dict[str, Any], span_index: dict[str, SourceSpan]) -> ExtractionArtifact:
    source_span_ids_raw = raw_artifact.get("source_span_ids", [])
    source_span_ids = [str(span_id) for span_id in source_span_ids_raw if str(span_id) in span_index]
    source_spans = [span_index[span_id] for span_id in source_span_ids]
    confidence = float(raw_artifact.get("confidence", 0.0))
    reason_codes = [str(code) for code in raw_artifact.get("reason_codes", [])]
    status = raw_artifact.get("status", "candidate")
    base = {
        "id": raw_artifact.get("id") or uuid.uuid4().hex,
        "kind": raw_artifact.get("kind", "claim"),
        "value": str(raw_artifact.get("value", "")).strip(),
        "metadata": raw_artifact.get("metadata", {}) if isinstance(raw_artifact.get("metadata", {}), dict) else {},
    }
    if status == "confirmed" and source_span_ids and confidence >= CONFIRMED_MIN_CONFIDENCE and not reason_codes:
        return ExtractionArtifact(
            id=base["id"],
            kind=base["kind"],
            value=base["value"],
            confidence=confidence,
            status="confirmed",
            source_span_ids=source_span_ids,
            source_spans=source_spans,
            metadata={**base["metadata"], "source": "llm_schema"},
        )
    if not source_span_ids:
        reason_codes.append("missing_source_span")
    if confidence < CONFIRMED_MIN_CONFIDENCE:
        reason_codes.append("low_confidence")
    return ExtractionArtifact(
        id=base["id"],
        kind=base["kind"],
        value=base["value"],
        confidence=min(confidence, 0.68),
        status="candidate",
        source_span_ids=[],
        source_spans=[],
        reason_codes=stable_unique(reason_codes) or ["schema_candidate"],
        metadata={**base["metadata"], "source": "llm_schema"},
    )


def apply_confirmed_threshold(
    confirmed: list[ExtractionArtifact],
    threshold: float,
) -> tuple[list[ExtractionArtifact], list[ExtractionArtifact]]:
    effective_threshold = max(CONFIRMED_MIN_CONFIDENCE, threshold)
    kept = []
    demoted = []
    for item in confirmed:
        if item.confidence >= effective_threshold:
            kept.append(item)
            continue
        demoted.append(
            ExtractionArtifact(
                id=item.id,
                kind=item.kind,
                value=item.value,
                confidence=item.confidence,
                status="candidate",
                source_span_ids=item.source_span_ids,
                source_spans=item.source_spans,
                reason_codes=["low_confidence"],
                metadata=item.metadata,
            )
        )
    return kept, demoted


def add_span_artifacts(
    span_id: str,
    span: SourceSpan,
    confirmed: list[ExtractionArtifact],
    candidates: list[ExtractionArtifact],
    warnings: list[UnsupportedWarning],
    seen: set[tuple[str, str, str]],
) -> None:
    for entity in extract_entities(span.text)[:8]:
        add_artifact(
            ExtractionArtifact(
                kind="entity",
                value=entity,
                confidence=0.78,
                status="confirmed",
                source_span_ids=[span_id],
                source_spans=[span],
                metadata={"source": "span_text"},
            ),
            confirmed,
            candidates,
            seen,
        )

    add_domain_artifacts(span_id, span, confirmed, candidates, seen)

    for alias_value, reason_codes, confidence in extract_aliases(span.text):
        status = "candidate" if reason_codes else "confirmed"
        artifact = ExtractionArtifact(
            kind="alias",
            value=alias_value,
            confidence=confidence,
            status=status,
            source_span_ids=[span_id] if status == "confirmed" else [],
            source_spans=[span] if status == "confirmed" else [],
            reason_codes=reason_codes,
            metadata={"source": "parenthetical_alias"},
        )
        add_artifact(artifact, confirmed, candidates, seen)
        if status != "confirmed":
            warnings.append(UnsupportedWarning(statement=alias_value, reason_codes=reason_codes))

    for quantity in extract_numeric_constraints(span.text):
        value = format_quantity_value(quantity)
        add_artifact(
            ExtractionArtifact(
                kind="measurement",
                value=value,
                confidence=0.88,
                status="confirmed",
                source_span_ids=[span_id],
                source_spans=[span],
                metadata={"quantity": quantity.model_dump()},
            ),
            confirmed,
            candidates,
            seen,
        )

    for sentence in extract_sentences(span.text):
        sentence_has_signal = any(term in sentence.lower() for term in CLAIM_TERMS) or bool(extract_numeric_constraints(sentence))
        if not sentence_has_signal:
            continue
        reason_codes = ["conflicting_values"] if has_conflict_signal(sentence) else []
        status = "candidate" if reason_codes else "confirmed"
        artifact = ExtractionArtifact(
            kind="claim",
            value=sentence,
            confidence=0.82 if status == "confirmed" else 0.64,
            status=status,
            source_span_ids=[span_id] if status == "confirmed" else [],
            source_spans=[span] if status == "confirmed" else [],
            reason_codes=reason_codes,
            metadata={"claim_type": "measurement_or_recommendation"},
        )
        add_artifact(artifact, confirmed, candidates, seen)
        if status != "confirmed":
            warnings.append(UnsupportedWarning(statement=sentence, reason_codes=reason_codes))

        if any(term in sentence.lower() for term in ("recommend", "рекоменду")):
            add_artifact(
                ExtractionArtifact(
                    kind="recommendation",
                    value=sentence,
                    confidence=0.8,
                    status="confirmed",
                    source_span_ids=[span_id],
                    source_spans=[span],
                    metadata={"source": "recommendation_sentence"},
                ),
                confirmed,
                candidates,
                seen,
            )

    relation = extract_relation(span.text)
    if relation:
        add_artifact(
            ExtractionArtifact(
                kind="relation",
                value=relation,
                confidence=0.74,
                status="confirmed",
                source_span_ids=[span_id],
                source_spans=[span],
                metadata={"source": "cooccurrence"},
            ),
            confirmed,
            candidates,
            seen,
        )


def add_domain_artifacts(
    span_id: str,
    span: SourceSpan,
    confirmed: list[ExtractionArtifact],
    candidates: list[ExtractionArtifact],
    seen: set[tuple[str, str, str]],
) -> None:
    for kind, values in extract_domain_values(span.text).items():
        for value in values[:10]:
            add_artifact(
                ExtractionArtifact(
                    kind=kind,
                    value=value,
                    confidence=0.79,
                    status="confirmed",
                    source_span_ids=[span_id],
                    source_spans=[span],
                    metadata={"source": "domain_rule"},
                ),
                confirmed,
                candidates,
                seen,
            )


def add_table_artifacts(
    document: NormalizedDocument,
    span_index: dict[str, SourceSpan],
    confirmed: list[ExtractionArtifact],
    candidates: list[ExtractionArtifact],
    warnings: list[UnsupportedWarning],
    seen: set[tuple[str, str, str]],
) -> None:
    table_spans = {span.table_block_id: (span_id, span) for span_id, span in span_index.items() if span.table_block_id}
    for table in document.table_blocks:
        source = table_spans.get(table.id)
        for row in table.rows[:20]:
            row_pairs = [f"{header}: {cell}" for header, cell in zip(table.headers, row)]
            row_text = " | ".join(row_pairs)
            quantities = extract_numeric_constraints(row_text)
            if not quantities:
                continue
            if source:
                span_id, span = source
                artifact = ExtractionArtifact(
                    kind="measurement",
                    value=row_text,
                    confidence=0.82,
                    status="confirmed",
                    source_span_ids=[span_id],
                    source_spans=[span],
                    metadata={"table_block_id": table.id, "quantities": [q.model_dump() for q in quantities]},
                )
                add_artifact(artifact, confirmed, candidates, seen)
            else:
                reason_codes = ["missing_source_span", "schema_candidate"]
                if needs_unit_check(row_text):
                    reason_codes.append("needs_unit_check")
                artifact = ExtractionArtifact(
                    kind="measurement",
                    value=row_text,
                    confidence=0.5,
                    status="candidate",
                    reason_codes=reason_codes,
                    metadata={"table_block_id": table.id, "quantities": [q.model_dump() for q in quantities]},
                )
                add_artifact(artifact, confirmed, candidates, seen)
                warnings.append(UnsupportedWarning(statement=row_text, reason_codes=reason_codes))


def add_unsourced_content_candidates(
    document: NormalizedDocument,
    candidates: list[ExtractionArtifact],
    warnings: list[UnsupportedWarning],
    seen: set[tuple[str, str, str]],
) -> None:
    for sentence in extract_sentences(document.content)[:30]:
        has_signal = bool(extract_numeric_constraints(sentence)) or any(term in sentence.lower() for term in CLAIM_TERMS)
        if not has_signal:
            continue
        reason_codes = ["missing_source_span", "low_confidence"]
        artifact = ExtractionArtifact(
            kind="claim",
            value=sentence,
            confidence=0.42,
            status="candidate",
            reason_codes=reason_codes,
            metadata={"source": "document_content_without_span"},
        )
        add_artifact(artifact, [], candidates, seen)
        warnings.append(UnsupportedWarning(statement=sentence, reason_codes=reason_codes))


def add_artifact(
    artifact: ExtractionArtifact,
    confirmed: list[ExtractionArtifact],
    candidates: list[ExtractionArtifact],
    seen: set[tuple[str, str, str]],
) -> None:
    key = (artifact.kind, artifact.value.lower(), artifact.status)
    if key in seen:
        return
    seen.add(key)
    if artifact.status == "confirmed":
        confirmed.append(artifact)
    else:
        candidates.append(artifact)


def extract_numeric_constraints(text: str) -> list[Quantity]:
    quantities = []
    for match in NUMERIC_PATTERN.finditer(text):
        first = parse_float(match.group("first"))
        second_text = match.group("second")
        unit = normalize_unit(match.group("unit"))
        operator_text = (match.group("operator") or "").lower()
        if second_text is not None:
            second = parse_float(second_text)
            quantities.append(Quantity(value=first, unit=unit, operator="range", range_min=min(first, second), range_max=max(first, second)))
            continue
        operator = normalize_operator(operator_text)
        quantities.append(Quantity(value=first, unit=unit, operator=operator))
    return quantities


def parse_float(value: str) -> float:
    return float(value.replace(",", "."))


def normalize_unit(unit: str) -> str:
    return UNIT_ALIASES.get(unit, UNIT_ALIASES.get(unit.lower(), unit.lower()))


def normalize_operator(operator: str) -> str:
    if operator in ("<=", "≤", "до", "не более", "менее"):
        return "le"
    if operator in (">=", "≥", "не менее", "более"):
        return "ge"
    if operator == "<":
        return "lt"
    if operator == ">":
        return "gt"
    return "eq"


def format_quantity_value(quantity: Quantity) -> str:
    if quantity.operator == "range":
        return f"{quantity.range_min:g}-{quantity.range_max:g} {quantity.unit}"
    if quantity.operator == "eq":
        return f"{quantity.value:g} {quantity.unit}"
    return f"{quantity.operator} {quantity.value:g} {quantity.unit}"


def extract_sentences(text: str) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return []
    parts = SENTENCE_SPLIT_PATTERN.split(normalized)
    return [part.strip(" ;") for part in parts if len(part.strip(" ;")) >= 8]


def extract_entities(text: str) -> list[str]:
    entities: list[str] = []
    for match in CHEMICAL_PATTERN.finditer(text):
        entities.append(match.group(0))
    lowered = text.lower()
    for term in PROCESS_TERMS:
        if term in lowered:
            entities.append(term)
    for original in GEO_TERMS.values():
        if original.lower() in lowered:
            entities.append(original)
    return stable_unique(entities)


def extract_domain_values(text: str) -> dict[str, list[str]]:
    lowered = text.lower()
    values: dict[str, list[str]] = {
        "material": [],
        "substance": [],
        "process": [],
        "equipment": [],
        "property": [],
        "date": [],
        "geography": [],
        "expert": [],
        "source": [],
        "conclusion": [],
    }
    for term in MATERIAL_TERMS:
        if term in lowered:
            values["material"].append(term)
    for match in CHEMICAL_PATTERN.finditer(text):
        values["substance"].append(match.group(0))
    for term in PROCESS_TERMS:
        if term in lowered:
            values["process"].append(term)
    for term in EQUIPMENT_TERMS:
        if term in lowered:
            values["equipment"].append(term)
    for term in PROPERTY_TERMS:
        if term in lowered:
            values["property"].append(term)
    for match in DATE_PATTERN.finditer(text):
        values["date"].append(match.group(0))
    for term, normalized in GEO_TERMS.items():
        if term in lowered:
            values["geography"].append(normalized)
    for match in EXPERT_PATTERN.finditer(text):
        values["expert"].append(match.group(0))
    if any(term in lowered for term in ("doi", "патент", "гост", "iso", "отчет", "отчёт", "journal")):
        values["source"].append(compact_snippet(text))
    for sentence in extract_sentences(text):
        if any(term in sentence.lower() for term in ("вывод", "заключ", "показано", "recommended", "conclusion")):
            values["conclusion"].append(sentence)
    return {kind: stable_unique(items) for kind, items in values.items() if items}


def extract_aliases(text: str) -> list[tuple[str, list[str], float]]:
    aliases = []
    seen_expansions: dict[str, str] = {}
    for match in ALIAS_PATTERN.finditer(text):
        long_name = " ".join(match.group("long").split())[-80:].strip(" -")
        short_name = match.group("short").strip()
        value = f"{short_name} -> {long_name}"
        reason_codes: list[str] = []
        confidence = 0.76
        if len(short_name) <= 2:
            reason_codes.append("ambiguous_alias")
            confidence = 0.58
        if short_name.lower() in seen_expansions and seen_expansions[short_name.lower()] != long_name.lower():
            reason_codes.append("conflicting_values")
            confidence = min(confidence, 0.56)
        seen_expansions[short_name.lower()] = long_name.lower()
        aliases.append((value, reason_codes, confidence))
    aliases.extend(extract_seed_aliases(text))
    aliases.extend(extract_translit_aliases(text))
    aliases.extend(extract_fuzzy_aliases(text))
    aliases.extend(extract_embedding_aliases(text))
    return unique_aliases(aliases)


def extract_seed_aliases(text: str) -> list[tuple[str, list[str], float]]:
    lowered = normalize_alias_text(text)
    aliases = []
    for alias, canonical in {**SEED_ALIASES, **RU_EN_ALIASES}.items():
        if normalize_alias_text(alias) in lowered:
            aliases.append((f"{alias} -> {canonical}", ["schema_candidate"], 0.66))
    return aliases


def extract_translit_aliases(text: str) -> list[tuple[str, list[str], float]]:
    aliases = []
    lowered = normalize_alias_text(text)
    for alias, canonical in RU_EN_ALIASES.items():
        transliterated = transliterate_ru_to_latin(canonical)
        if transliterated and transliterated in lowered:
            aliases.append((f"{transliterated} -> {canonical}", ["schema_candidate"], 0.62))
    return aliases


def extract_fuzzy_aliases(text: str) -> list[tuple[str, list[str], float]]:
    tokens = sorted({normalize_alias_text(token) for token in TOKEN_PATTERN.findall(text) if len(token) >= 4})
    choices = list({*SEED_ALIASES, *RU_EN_ALIASES, *SEED_ALIASES.values(), *RU_EN_ALIASES.values()})
    aliases = []
    for token in tokens[:80]:
        match_value, score = fuzzy_best_match(token, choices)
        if not match_value or score < FUZZY_ALIAS_THRESHOLD or token == normalize_alias_text(match_value):
            continue
        canonical = SEED_ALIASES.get(match_value.lower()) or RU_EN_ALIASES.get(match_value.lower()) or match_value
        aliases.append((f"{token} -> {canonical}", ["schema_candidate"], round(score / 100, 2)))
    return aliases


def extract_embedding_aliases(text: str) -> list[tuple[str, list[str], float]]:
    tokens = sorted({normalize_alias_text(token) for token in TOKEN_PATTERN.findall(text) if len(token) >= 3})
    choices = list({*SEED_ALIASES, *RU_EN_ALIASES, *SEED_ALIASES.values(), *RU_EN_ALIASES.values()})
    aliases = []
    choice_vectors = {choice: alias_embedding(normalize_alias_text(choice)) for choice in choices}
    for token in tokens[:80]:
        token_vector = alias_embedding(token)
        best_choice = None
        best_score = 0.0
        for choice, choice_vector in choice_vectors.items():
            score = cosine_similarity(token_vector, choice_vector)
            if score > best_score:
                best_choice = choice
                best_score = score
        if not best_choice or best_score < 0.72 or token == normalize_alias_text(best_choice):
            continue
        canonical = SEED_ALIASES.get(best_choice.lower()) or RU_EN_ALIASES.get(best_choice.lower()) or best_choice
        aliases.append((f"{token} -> {canonical}", ["schema_candidate"], round(best_score, 2)))
    return aliases


def cosine_similarity(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left)) or 1.0
    right_norm = math.sqrt(sum(value * value for value in right)) or 1.0
    return numerator / (left_norm * right_norm)


def alias_embedding(text: str, dimensions: int = 64) -> list[float]:
    vector = [0.0] * dimensions
    normalized = f"  {normalize_alias_text(text)}  "
    for size in (2, 3):
        for index in range(max(0, len(normalized) - size + 1)):
            ngram = normalized[index : index + size]
            bucket = int(hashlib.sha1(ngram.encode("utf-8")).hexdigest()[:8], 16) % dimensions
            vector[bucket] += 1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def fuzzy_best_match(token: str, choices: list[str]) -> tuple[str | None, int]:
    if process is not None:
        result = process.extractOne(token, choices, scorer=fuzz.WRatio if fuzz else None)
        if not result:
            return None, 0
        return str(result[0]), int(result[1])
    best = None
    best_score = 0
    for choice in choices:
        score = round(SequenceMatcher(None, token, normalize_alias_text(choice)).ratio() * 100)
        if score > best_score:
            best = choice
            best_score = score
    return best, best_score


def normalize_alias_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower().replace("–", "-").replace("—", "-").replace("‑", "-")).strip()


def unique_aliases(aliases: list[tuple[str, list[str], float]]) -> list[tuple[str, list[str], float]]:
    result = []
    seen = set()
    for value, reason_codes, confidence in aliases:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append((value, stable_unique(reason_codes), confidence))
    return result


def transliterate_ru_to_latin(value: str) -> str:
    table = str.maketrans(
        {
            "а": "a",
            "б": "b",
            "в": "v",
            "г": "g",
            "д": "d",
            "е": "e",
            "ё": "e",
            "ж": "zh",
            "з": "z",
            "и": "i",
            "й": "y",
            "к": "k",
            "л": "l",
            "м": "m",
            "н": "n",
            "о": "o",
            "п": "p",
            "р": "r",
            "с": "s",
            "т": "t",
            "у": "u",
            "ф": "f",
            "х": "h",
            "ц": "ts",
            "ч": "ch",
            "ш": "sh",
            "щ": "sch",
            "ы": "y",
            "э": "e",
            "ю": "yu",
            "я": "ya",
            "ь": "",
            "ъ": "",
        }
    )
    return normalize_alias_text(value.translate(table))


def extract_relation(text: str) -> str | None:
    entities = extract_entities(text)
    if len(entities) < 2:
        return None
    lowered = text.lower()
    for term in ("влияет", "примен", "used", "applied", "affects", "between"):
        if term in lowered:
            return f"{entities[0]} related_to {entities[1]}"
    return None


def has_conflict_signal(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in ("противореч", "расхожд", "conflict", "disagree", "inconsistent"))


def needs_unit_check(text: str) -> bool:
    return not any(unit in text.lower() for unit in UNIT_ALIASES)


def stable_unique(values: list[str]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        normalized = value.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(value)
    return result


def suggest_document_profile(document: NormalizedDocument) -> DocumentProfileSuggestion:
    text = f"{document.source_type} {document.title} {document.content[:2000]}".lower()
    purpose = "unknown"
    if any(term in text for term in ("patent", "патент")):
        purpose = "patent"
    elif any(term in text for term in ("standard", "regulation", "норматив", "гост")):
        purpose = "regulation"
    elif any(term in text for term in ("experiment", "protocol", "эксперимент", "протокол")):
        purpose = "experiment_log"
    elif any(term in text for term in ("report", "отчет", "отчёт")):
        purpose = "technical_report"
    elif any(term in text for term in ("article", "journal", "publication", "статья", "публикац")):
        purpose = "research_article"
    source_type = document.source_type.strip() or "unknown"
    confidence = 0.7 if purpose != "unknown" else 0.45
    return DocumentProfileSuggestion(
        source_type=source_type,
        document_purpose=purpose,
        access_policy_suggestion=document.access_policy,
        confidence=confidence,
    )


def build_query_ir(request: QueryIRBuildRequest) -> QueryIRBuildResponse:
    raw_query = request.raw_query
    selected_model = settings.yandex_fast_model
    key = cache_key("query_ir", "query_ir.v1", selected_model, request.model_dump(mode="json"))
    cached = cached_response(QueryIRBuildResponse, key)
    if cached:
        return cached
    numeric_constraints = extract_numeric_constraints(raw_query)
    entities = stable_unique(extract_entities(raw_query) + extract_query_terms(raw_query))
    geo_constraints = extract_geo_constraints(raw_query)
    time_constraints = extract_time_constraints(raw_query)
    source_type_filter = extract_source_type_filter(raw_query)
    constraints: dict[str, Any] = {
        "numeric_constraints": [quantity.model_dump() for quantity in numeric_constraints],
        "geo_constraints": geo_constraints,
        "time_constraints": time_constraints,
        "source_type_constraints": source_type_filter,
        "aliases": extract_query_aliases(raw_query),
    }
    query_ir = QueryIR(
        raw_query=raw_query,
        entities=entities,
        intent=detect_intent(raw_query),
        filters=constraints,
        geo_filter=GeoContext(location_name=geo_constraints[0]) if geo_constraints else None,
        numeric_filter=numeric_constraints[0] if numeric_constraints else None,
        source_type_filter=source_type_filter or None,
        limit=request.limit,
    )
    mode = "deterministic_degraded"
    warnings: list[str] = []
    client = YandexModelClient(settings)
    if client.is_configured:
        try:
            llm_response = build_llm_query_ir(client, request)
            query_ir = merge_query_ir(llm_response.query_ir, query_ir)
            constraints = merge_constraints(llm_response.constraints, constraints)
            query_ir.filters = constraints
            mode = "llm"
            warnings.extend(llm_response.warnings)
        except Exception as exc:
            warnings.append(f"Yandex Query IR failed, deterministic fallback used: {exc}")
    if mode == "deterministic_degraded":
        warnings.append(DEGRADED_WARNING)
    response = QueryIRBuildResponse(
        mode=mode,
        query_ir=query_ir,
        constraints=constraints,
        warnings=warnings,
    )
    return store_cache(key, QueryIRBuildResponse.model_validate(response.model_dump()))


def build_llm_query_ir(client: YandexModelClient, request: QueryIRBuildRequest) -> QueryIRBuildResponse:
    data = complete_json_with_fallback(
        client,
        "Convert the question into QueryIR. Preserve numeric constraints, units, ranges, geography, time ranges, source type constraints, aliases and entity hints. Do not answer.",
        json_dumps(request.model_dump(mode="json")),
        QueryIRBuildResponse.model_json_schema(),
        settings.yandex_fast_model,
        [settings.yandex_chat_model],
    )
    data.setdefault("query_ir", {"raw_query": request.raw_query, "limit": request.limit})
    data.setdefault("constraints", {})
    data.setdefault("warnings", [])
    normalize_llm_query_ir_payload(data)
    return QueryIRBuildResponse.model_validate(data)


def complete_json_with_fallback(
    client: YandexModelClient,
    system_prompt: str,
    user_prompt: str,
    schema: dict[str, Any],
    primary_model: str,
    fallback_models: list[str],
) -> dict[str, Any]:
    errors = []
    for model_name in stable_unique([primary_model, *fallback_models]):
        try:
            return client.complete_json(system_prompt, user_prompt, schema, model_name)
        except Exception as exc:
            errors.append(f"{model_name}: {exc}")
    raise RuntimeError("; ".join(errors))


def normalize_llm_query_ir_payload(data: dict[str, Any]) -> None:
    query_ir = data.get("query_ir")
    if not isinstance(query_ir, dict):
        return
    geo_filter = query_ir.get("geo_filter")
    if isinstance(geo_filter, dict) and not geo_filter.get("location_name"):
        query_ir["geo_filter"] = None
    numeric_filter = query_ir.get("numeric_filter")
    if isinstance(numeric_filter, dict) and numeric_filter.get("value") is None:
        query_ir["numeric_filter"] = None


def merge_query_ir(llm_query_ir: QueryIR, rule_query_ir: QueryIR) -> QueryIR:
    return QueryIR(
        id=llm_query_ir.id,
        raw_query=rule_query_ir.raw_query,
        entities=stable_unique([*llm_query_ir.entities, *rule_query_ir.entities]),
        intent=llm_query_ir.intent or rule_query_ir.intent,
        filters=rule_query_ir.filters,
        geo_filter=rule_query_ir.geo_filter or llm_query_ir.geo_filter,
        numeric_filter=rule_query_ir.numeric_filter or llm_query_ir.numeric_filter,
        source_type_filter=rule_query_ir.source_type_filter or llm_query_ir.source_type_filter,
        limit=rule_query_ir.limit,
        offset=rule_query_ir.offset,
    )


def merge_constraints(llm_constraints: dict[str, Any], rule_constraints: dict[str, Any]) -> dict[str, Any]:
    merged = dict(llm_constraints)
    for key, value in rule_constraints.items():
        if value:
            merged[key] = value
        else:
            merged.setdefault(key, value)
    return merged


def extract_query_terms(query: str) -> list[str]:
    lowered = query.lower()
    terms = []
    for term in PROCESS_TERMS:
        if term in lowered:
            terms.append(term)
    for token in ("сульфаты", "хлориды", "сухой остаток", "католит", "шахтные воды", "штейн", "шлак", "ферроникель"):
        if token in lowered:
            terms.append(token)
    return terms


def extract_geo_constraints(query: str) -> list[str]:
    lowered = query.lower()
    result = []
    for term, normalized in GEO_TERMS.items():
        if term in lowered:
            result.append(normalized)
    return stable_unique(result)


def extract_time_constraints(query: str) -> dict[str, Any]:
    lowered = query.lower()
    relative_match = re.search(r"последн(?:ие|их|ими)?\s+(\d+)\s+лет", lowered)
    if relative_match:
        return {"relative_years": int(relative_match.group(1))}
    range_match = re.search(r"(20\d{2})\s*[-–—]\s*(20\d{2})", lowered)
    if range_match:
        return {"start_year": int(range_match.group(1)), "end_year": int(range_match.group(2))}
    return {}


def extract_source_type_filter(query: str) -> list[str]:
    lowered = query.lower()
    result = []
    for term, source_type in SOURCE_TYPE_TERMS.items():
        if term in lowered:
            result.append(source_type)
    return stable_unique(result)


def extract_query_aliases(query: str) -> list[dict[str, str]]:
    return [{"alias": short, "canonical_hint": long_name} for value, _, _ in extract_aliases(query) for short, long_name in [value.split(" -> ", 1)]]


def detect_intent(query: str) -> str:
    lowered = query.lower()
    if any(term in lowered for term in ("сравн", "соотно", "compare", "versus")):
        return "compare"
    if any(term in lowered for term in ("какие", "методы", "способы", "решения", "технологии", "methods")):
        return "find_methods"
    if any(term in lowered for term in ("параметр", "диапазон", "скорост", "temperature", "flow")):
        return "extract_constraints"
    return "evidence_lookup"


def rerank_evidence(request: RerankRequest) -> RerankResponse:
    query_tokens = normalized_tokens(request.query_ir.raw_query)
    scored = []
    for evidence_item in request.evidence_items:
        text = evidence_item.source_span.text
        overlap = token_overlap(query_tokens, normalized_tokens(text))
        constraint_score = constraint_match_score(request.query_ir.filters, text)
        base_score = max(evidence_item.relevance_score, 0.0)
        score = min(1.0, (0.45 * overlap) + (0.35 * constraint_score) + (0.2 * base_score))
        reasons = []
        if overlap > 0:
            reasons.append("lexical_overlap")
        if constraint_score > 0:
            reasons.append("constraint_match")
        if evidence_item.source_span.text:
            reasons.append("source_span_present")
        scored.append((score, evidence_item, reasons))
    scored.sort(key=lambda item: item[0], reverse=True)
    response = RerankResponse(
        scored_items=[
            ScoredEvidenceItem(rank=index + 1, score=round(score, 6), evidence_item=item, reasons=reasons)
            for index, (score, item, reasons) in enumerate(scored[: request.limit])
        ],
        warnings=[DEGRADED_WARNING],
    )
    return RerankResponse.model_validate(response.model_dump())


def normalized_tokens(text: str) -> set[str]:
    return {token.lower().strip(".,;:()[]{}") for token in TOKEN_PATTERN.findall(text) if len(token.strip(".,;:()[]{}")) >= 2}


def token_overlap(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left)


def constraint_match_score(filters: dict[str, Any], text: str) -> float:
    score = 0.0
    lowered = text.lower()
    numeric_constraints = filters.get("numeric_constraints", [])
    if numeric_constraints and extract_numeric_constraints(text):
        score += 0.45
    geo_constraints = [str(value).lower() for value in filters.get("geo_constraints", [])]
    if any(value in lowered for value in geo_constraints):
        score += 0.25
    aliases = filters.get("aliases", [])
    if any(alias.get("alias", "").lower() in lowered for alias in aliases if isinstance(alias, dict)):
        score += 0.15
    if filters.get("time_constraints") and re.search(r"\b20\d{2}\b", text):
        score += 0.15
    return min(score, 1.0)


def synthesize_answer(request: AnswerSynthesisRequest) -> AnswerSynthesisResponse:
    evidence_items = request.evidence_bundle.evidence_items
    unsupported_warnings = [
        UnsupportedWarning(statement=item.value, reason_codes=item.reason_codes)
        for item in request.candidate_items
    ]
    warnings = []
    if not evidence_items:
        answer_text = "Недостаточно подтвержденных источников для фактического ответа. Неподтвержденные кандидаты оставлены для экспертной проверки."
        confidence = 0.0
    else:
        snippets = [compact_snippet(item.source_span.text) for item in evidence_items[:3]]
        answer_text = "По подтвержденным источникам найдены опорные фрагменты: " + " | ".join(snippets)
        if request.evidence_bundle.has_gaps:
            answer_text += " Есть пробелы в доказательствах."
        if request.evidence_bundle.has_conflicts:
            answer_text += " Есть признаки конфликта источников."
        confidence = min(0.95, sum(max(item.relevance_score, 0.1) for item in evidence_items) / max(len(evidence_items), 1))
        client = YandexModelClient(settings)
        if client.is_configured:
            try:
                answer_text = client.complete_text(
                    "Синтезируй краткий ответ только по EvidenceBundle. Не используй candidates как факты. Укажи ограничения и слабые места.",
                    json_safe_payload(
                        {
                            "query": request.query_ir.raw_query,
                            "evidence": [item.source_span.text for item in evidence_items[:8]],
                            "gaps": request.evidence_bundle.gaps,
                            "conflicts": request.evidence_bundle.conflicts,
                        }
                    ),
                    settings.yandex_chat_model,
                )
            except Exception as exc:
                warnings.append(f"Yandex answer synthesis failed, deterministic fallback used: {exc}")
    if not settings.yandex_enabled:
        warnings.append(DEGRADED_WARNING)
    answer = AnswerPayload(
        id=uuid.uuid4().hex,
        query_ir=request.query_ir,
        evidence_bundle=request.evidence_bundle,
        answer_text=answer_text,
        confidence=round(confidence, 6),
        sources_count=len(evidence_items),
        model_used="deterministic-degraded-v1",
    )
    response = AnswerSynthesisResponse(
        mode="llm" if settings.yandex_enabled and evidence_items else "deterministic_degraded",
        answer=answer,
        unsupported_warnings=unsupported_warnings,
        candidate_count=len(request.candidate_items),
        warnings=warnings,
    )
    return AnswerSynthesisResponse.model_validate(response.model_dump())


def detect_conflicts(request: ConflictDetectionRequest) -> ConflictDetectionResponse:
    groups: dict[str, list[ExtractionArtifact]] = {}
    for artifact in request.artifacts:
        if artifact.kind not in ("measurement", "claim", "property"):
            continue
        key = artifact.metadata.get("quantity", {}).get("unit") if isinstance(artifact.metadata.get("quantity"), dict) else artifact.kind
        groups.setdefault(str(key), []).append(artifact)
    conflicts = []
    for key, artifacts in groups.items():
        numeric_values = [extract_first_number(item.value) for item in artifacts]
        numeric_values = [value for value in numeric_values if value is not None]
        if len(set(round(value, 6) for value in numeric_values)) > 1:
            conflicts.append(
                ConflictSignal(
                    value_key=key,
                    artifact_ids=[item.id for item in artifacts],
                    reason="conflicting numeric values for comparable unit or property",
                    confidence=0.74,
                )
            )
        conflicting_candidates = [item for item in artifacts if "conflicting_values" in item.reason_codes]
        if conflicting_candidates:
            conflicts.append(
                ConflictSignal(
                    value_key=key,
                    artifact_ids=[item.id for item in conflicting_candidates],
                    reason="candidate reason code marks conflicting values",
                    confidence=0.82,
                )
            )
    return ConflictDetectionResponse(conflicts=conflicts, warnings=[DEGRADED_WARNING] if not settings.yandex_enabled else [])


def suggest_gaps(request: GapSuggestionRequest) -> GapSuggestionResponse:
    gaps = []
    if not request.evidence_bundle.evidence_items:
        gaps.append(GapSuggestion(gap_type="missing_evidence", description="Нет подтвержденных SourceSpan в EvidenceBundle.", priority="high"))
    filters = request.query_ir.filters
    if filters.get("numeric_constraints") and not any(extract_numeric_constraints(item.source_span.text) for item in request.evidence_bundle.evidence_items):
        gaps.append(GapSuggestion(gap_type="missing_numeric_constraint", description="Вопрос содержит числовые ограничения, но evidence не подтверждает числовые значения.", priority="high"))
    if filters.get("geo_constraints"):
        evidence_text = " ".join(item.source_span.text.lower() for item in request.evidence_bundle.evidence_items)
        if not any(str(geo).lower() in evidence_text for geo in filters["geo_constraints"]):
            gaps.append(GapSuggestion(gap_type="missing_geo", description="Вопрос содержит географию, но evidence не подтверждает географический контекст.", priority="medium"))
    candidate_ids = [item.id for item in request.candidates if item.reason_codes]
    if candidate_ids:
        gaps.append(GapSuggestion(gap_type="candidate_review", description="Есть кандидаты, требующие экспертной проверки.", priority="medium", related_candidate_ids=candidate_ids))
    if request.evidence_bundle.has_conflicts:
        gaps.append(GapSuggestion(gap_type="conflict_review", description="EvidenceBundle содержит конфликт, нужны условия сравнения источников.", priority="high"))
    return GapSuggestionResponse(gaps=gaps, warnings=[DEGRADED_WARNING] if not settings.yandex_enabled else [])


def extract_user_interests(request: UserInterestExtractionRequest) -> UserInterestExtractionResponse:
    lowered = request.text.lower()
    interests = []
    sources = {
        "materials": MATERIAL_TERMS,
        "processes": set(PROCESS_TERMS),
        "equipment": EQUIPMENT_TERMS,
        "properties": PROPERTY_TERMS,
        "geography": set(GEO_TERMS),
    }
    for label, terms in sources.items():
        matched = sorted(term for term in terms if term in lowered)
        if matched:
            interests.append(UserInterest(label=label, weight=min(1.0, 0.35 + 0.1 * len(matched)), source_terms=matched[:8]))
    for formula in CHEMICAL_PATTERN.findall(request.text):
        interests.append(UserInterest(label=f"substance:{formula}", weight=0.8, source_terms=[formula]))
    return UserInterestExtractionResponse(interests=interests, warnings=[DEGRADED_WARNING] if not settings.yandex_enabled else [])


def match_notifications(request: NotificationMatchRequest) -> NotificationMatchResponse:
    matches = []
    for interest in request.interests:
        interest_terms = {interest.label.lower(), *[term.lower() for term in interest.source_terms]}
        for artifact in request.artifacts:
            artifact_text = f"{artifact.kind} {artifact.value}".lower()
            overlap = [term for term in interest_terms if term and term in artifact_text]
            if not overlap:
                continue
            score = min(1.0, interest.weight * (0.5 + 0.1 * len(overlap)) * max(artifact.confidence, 0.1))
            matches.append(NotificationMatch(interest_label=interest.label, artifact_id=artifact.id, score=round(score, 6), reason=", ".join(overlap[:4])))
    matches.sort(key=lambda item: item.score, reverse=True)
    return NotificationMatchResponse(matches=matches, warnings=[DEGRADED_WARNING] if not settings.yandex_enabled else [])


def enrich_jsonld(request: JsonLdEnrichmentRequest) -> JsonLdEnrichmentResponse:
    evidence = request.answer.evidence_bundle.evidence_items
    jsonld = {
        "@context": {
            "st": "https://scientific-tangle.local/ontology#",
            "schema": "https://schema.org/",
        },
        "@type": "st:Answer",
        "@id": f"st:answer:{request.answer.id}",
        "schema:text": request.answer.answer_text,
        "st:confidence": request.answer.confidence,
        "st:query": request.answer.query_ir.raw_query,
        "st:evidence": [
            {
                "@type": "st:SourceSpan",
                "st:documentId": item.source_span.document_id,
                "st:page": item.source_span.page,
                "st:startOffset": item.source_span.start_offset,
                "st:endOffset": item.source_span.end_offset,
                "schema:text": item.source_span.text,
            }
            for item in evidence
        ],
    }
    return JsonLdEnrichmentResponse(jsonld=jsonld, warnings=[DEGRADED_WARNING] if not settings.yandex_enabled else [])


def model_status() -> ModelStatusResponse:
    return ModelStatusResponse(
        provider=settings.llm_provider,
        yandex_configured=settings.yandex_enabled,
        chat_model=settings.yandex_chat_model,
        embedding_doc_model=settings.yandex_embedding_doc_model,
        embedding_query_model=settings.yandex_embedding_query_model,
        embedding_dimensions=settings.yandex_embedding_dim,
        mode="llm" if settings.yandex_enabled else "deterministic_degraded",
    )


def extract_first_number(text: str) -> float | None:
    match = re.search(r"\d+(?:[,.]\d+)?", text)
    if not match:
        return None
    return parse_float(match.group(0))


def json_safe_payload(payload: dict[str, Any]) -> str:
    return json_dumps(payload)


def json_dumps(payload: dict[str, Any]) -> str:
    import json

    return json.dumps(payload, ensure_ascii=False)


def compact_snippet(text: str) -> str:
    snippet = " ".join(text.split())
    if len(snippet) <= 180:
        return snippet
    return snippet[:177].rstrip() + "..."
