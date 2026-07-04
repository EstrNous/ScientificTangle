import hashlib
import json
import math
import re
import uuid
from datetime import UTC, datetime
from difflib import SequenceMatcher
from typing import Any

try:
    from redis import Redis
    from redis.exceptions import RedisError
except ImportError:
    Redis = None
    RedisError = Exception

try:
    from thefuzz import fuzz, process
except ImportError:
    fuzz = None
    process = None

from shared.contracts import (
    AnswerPayload,
    EvidenceItem,
    GeoContext,
    NormalizedDocument,
    Quantity,
    QueryIR,
    SourceSpan,
)
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
    EvidenceLayerItem,
    EvidenceSynthesisLayers,
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
    ScientificAnswerPayload,
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
REDIS_CLIENT: Any | None = None
REDIS_CACHE_AVAILABLE: bool | None = None
REDIS_CACHE_DEGRADED_REASON = ""
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
    provider_signature = f"{settings.llm_provider}:{settings.yandex_enabled}:{model_name}:{settings.embedding_dimensions}:{settings.confirmed_confidence_threshold}"
    provider_digest = hashlib.sha256(provider_signature.encode("utf-8")).hexdigest()[:16]
    return f"st:model:v1:{operation}:{version}:{provider_digest}:{digest}"


def cache_ttl_seconds(operation: str) -> int:
    if operation == "embeddings":
        return settings.model_embedding_cache_ttl_seconds
    return settings.model_cache_ttl_seconds


def redis_cache_enabled() -> bool:
    return settings.model_cache_backend.lower() == "redis"


def redis_client() -> Any | None:
    global REDIS_CLIENT, REDIS_CACHE_AVAILABLE, REDIS_CACHE_DEGRADED_REASON
    if not redis_cache_enabled():
        REDIS_CACHE_AVAILABLE = False
        REDIS_CACHE_DEGRADED_REASON = "redis cache backend is disabled"
        return None
    if Redis is None:
        REDIS_CACHE_AVAILABLE = False
        REDIS_CACHE_DEGRADED_REASON = "redis package is not installed"
        return None
    if REDIS_CLIENT is not None:
        return REDIS_CLIENT
    try:
        REDIS_CLIENT = Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=settings.model_cache_connect_timeout_seconds,
            socket_timeout=settings.model_cache_connect_timeout_seconds,
            decode_responses=True,
        )
        REDIS_CLIENT.ping()
        REDIS_CACHE_AVAILABLE = True
        REDIS_CACHE_DEGRADED_REASON = ""
        return REDIS_CLIENT
    except RedisError as exc:
        REDIS_CLIENT = None
        REDIS_CACHE_AVAILABLE = False
        REDIS_CACHE_DEGRADED_REASON = str(exc)
        return None


def redis_cache_status() -> tuple[bool, str]:
    client = redis_client()
    if client is not None:
        return True, ""
    return bool(REDIS_CACHE_AVAILABLE), REDIS_CACHE_DEGRADED_REASON


def cached_response(model_cls: type[Any], key: str, redis_allowed: bool = True) -> Any | None:
    cached = MODEL_CACHE.get(key)
    if cached is not None:
        return model_cls.model_validate(cached)
    if not redis_allowed:
        return None
    client = redis_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
    except RedisError as exc:
        global REDIS_CACHE_AVAILABLE, REDIS_CACHE_DEGRADED_REASON
        REDIS_CACHE_AVAILABLE = False
        REDIS_CACHE_DEGRADED_REASON = str(exc)
        return None
    if raw is None:
        return None
    try:
        payload = json.loads(raw)
        response = model_cls.model_validate(payload)
    except (TypeError, ValueError):
        return None
    MODEL_CACHE[key] = response.model_dump(mode="json")
    return response


def store_cache(key: str, response: Any, operation: str, redis_allowed: bool = True) -> Any:
    payload = response.model_dump(mode="json")
    MODEL_CACHE[key] = payload
    if not redis_allowed:
        return response
    client = redis_client()
    if client is None:
        return response
    try:
        client.setex(key, cache_ttl_seconds(operation), json.dumps(payload, ensure_ascii=False))
    except RedisError as exc:
        global REDIS_CACHE_AVAILABLE, REDIS_CACHE_DEGRADED_REASON
        REDIS_CACHE_AVAILABLE = False
        REDIS_CACHE_DEGRADED_REASON = str(exc)
    return response


def build_embeddings(request: EmbeddingRequest) -> EmbeddingResponse:
    client = YandexModelClient(settings)
    selected_model = select_embedding_model(request)
    cached_items: list[EmbeddingItem | None] = []
    missing: list[tuple[int, str, str]] = []
    for index, text in enumerate(request.texts):
        item_payload = {
            "text": text,
            "dimensions": request.dimensions,
            "model_name": selected_model,
            "input_type": request.input_type,
        }
        item_key = cache_key("embeddings", "embeddings.v1", selected_model, item_payload)
        cached = cached_response(EmbeddingItem, item_key)
        if cached is None:
            cached_items.append(None)
            missing.append((index, text, item_key))
        else:
            cached_items.append(EmbeddingItem(index=index, text=text, vector=cached.vector))
    if not missing:
        return EmbeddingResponse(
            mode="llm" if settings.yandex_enabled else "deterministic_degraded",
            model_name=selected_model if settings.yandex_enabled else request.model_name,
            dimensions=request.dimensions,
            embeddings=[item for item in cached_items if item is not None],
            warnings=[],
        )
    warnings = []
    mode = "deterministic_degraded"
    missing_embeddings: list[EmbeddingItem] = []
    if client.is_configured:
        try:
            missing_embeddings = [
                EmbeddingItem(index=index, text=text, vector=client.embedding(text, selected_model, request.dimensions))
                for index, text, _ in missing
            ]
            mode = "llm"
        except Exception as exc:
            warnings.append(f"Yandex embeddings failed, deterministic fallback used: {exc}")
    if not missing_embeddings:
        missing_embeddings = [
            EmbeddingItem(index=index, text=text, vector=hash_embedding(text, request.dimensions))
            for index, text, _ in missing
        ]
        warnings.append(DEGRADED_WARNING)
    redis_allowed_for_embeddings = mode == "llm" or not settings.yandex_enabled
    for item, (_, _, item_key) in zip(missing_embeddings, missing, strict=True):
        store_cache(item_key, item, "embeddings", redis_allowed=redis_allowed_for_embeddings)
        cached_items[item.index] = item
    embeddings = [item for item in cached_items if item is not None]
    response = EmbeddingResponse(
        mode=mode,
        model_name=selected_model if mode == "llm" else request.model_name,
        dimensions=request.dimensions,
        embeddings=embeddings,
        warnings=warnings,
    )
    return EmbeddingResponse.model_validate(response.model_dump())


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
        digest = hashlib.sha256(f"{counter}:{text}".encode()).digest()
        values.extend((byte / 127.5) - 1.0 for byte in digest)
        counter += 1
    vector = values[:dimensions]
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [round(value / norm, 6) for value in vector]


def build_structured_extraction(request: StructuredExtractionRequest) -> StructuredExtractionResponse:
    document = request.document
    selected_model = settings.yandex_long_context_model
    key = cache_key("structured_extraction", "structured_extraction.v1", selected_model, request.model_dump(mode="json"))
    redis_allowed = document.access_policy.level != "restricted"
    cached = cached_response(StructuredExtractionResponse, key, redis_allowed=redis_allowed)
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
    return store_cache(key, StructuredExtractionResponse.model_validate(response.model_dump()), "structured_extraction", redis_allowed=redis_allowed)


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
        quantity = quantity.model_copy(update={"source_span_id": span_id})
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
                quantities = [quantity.model_copy(update={"source_span_id": span_id}) for quantity in quantities]
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
    return store_cache(key, QueryIRBuildResponse.model_validate(response.model_dump()), "query_ir")


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


def synthesize_evidence_layers(
    query_ir: QueryIR,
    evidence_items: list[EvidenceItem],
    candidate_items: list[ExtractionArtifact],
) -> EvidenceSynthesisLayers:
    layers = EvidenceSynthesisLayers()
    for index, item in enumerate(evidence_items):
        reason_codes = evidence_reason_codes(query_ir, item)
        layer = layer_name_for_reason_codes(reason_codes)
        layer_item = EvidenceLayerItem(
            layer=layer,
            statement=compact_snippet(item.source_span.text),
            confidence=max(0.0, min(item.relevance_score, 1.0)),
            reason_codes=reason_codes,
            source_span_ids=[item.source_span.id],
            evidence_item_index=index,
            metadata={
                "extraction_method": item.extraction_method,
                "claim_ids": item.claim_ids,
                "entity_ids": item.entity_ids,
            },
        )
        getattr(layers, layer).append(layer_item)
    for artifact in candidate_items:
        reason_codes = stable_unique([str(code) for code in artifact.reason_codes] or ["unsupported_claim"])
        layer = layer_name_for_reason_codes(reason_codes)
        layer_item = EvidenceLayerItem(
            layer=layer,
            statement=artifact.value,
            confidence=artifact.confidence,
            reason_codes=reason_codes,
            source_span_ids=artifact.source_span_ids,
            artifact_id=artifact.id,
            metadata={"kind": artifact.kind, **artifact.metadata},
        )
        getattr(layers, layer).append(layer_item)
    return layers


def evidence_reason_codes(query_ir: QueryIR, item: EvidenceItem) -> list[str]:
    span = item.source_span
    text = span.text or ""
    filters = query_ir.filters
    reason_codes: list[str] = []
    if not span.id or not text.strip():
        reason_codes.append("missing_source_span")
    if filters.get("numeric_constraints") and not numeric_constraints_covered(filters.get("numeric_constraints", []), text):
        requested_units = {
            normalize_unit(str(constraint.get("unit", "")))
            for constraint in filters.get("numeric_constraints", [])
            if isinstance(constraint, dict) and constraint.get("unit")
        }
        evidence_units = {quantity.unit for quantity in extract_numeric_constraints(text) if quantity.unit}
        if requested_units and evidence_units and requested_units.isdisjoint(evidence_units):
            reason_codes.append("unit_mismatch")
        else:
            reason_codes.append("unsupported_claim")
    if filters.get("geo_constraints") and not geo_constraints_covered(filters.get("geo_constraints", []), text):
        reason_codes.append("geo_mismatch")
    if filters.get("time_constraints") and not time_constraints_covered(filters.get("time_constraints", {}), text):
        reason_codes.append("outside_time_range")
    source_types = [str(value).lower() for value in filters.get("source_type_constraints", [])]
    if source_types and not any(value in text.lower() for value in source_types):
        reason_codes.append("inaccessible_source")
    query_entities = [str(value).lower() for value in query_ir.entities]
    if query_entities and not any(value and value in text.lower() for value in query_entities):
        reason_codes.append("unresolved_alias")
    return stable_unique(reason_codes)


def layer_name_for_reason_codes(reason_codes: list[str]) -> str:
    if not reason_codes:
        return "verified"
    if any(code in {"conflicting_values", "needs_unit_check"} for code in reason_codes):
        return "conflicting"
    if any(code in {"missing_source_span", "unsupported_claim", "inaccessible_source"} for code in reason_codes):
        return "unsupported"
    return "candidate"


def build_scientific_answer_payload(
    answer_text: str,
    layers: EvidenceSynthesisLayers,
    evidence_bundle_gaps: list[str],
    evidence_bundle_conflicts: list[str],
) -> ScientificAnswerPayload:
    limitations = []
    if layers.candidate:
        limitations.append("candidate_evidence_requires_review")
    if layers.unsupported:
        limitations.append("unsupported_claims_excluded")
    if layers.conflicting:
        limitations.append("conflicting_evidence_requires_resolution")
    follow_up = []
    if evidence_bundle_gaps or layers.unsupported:
        follow_up.append("collect_or_link_missing_sources")
    if evidence_bundle_conflicts or layers.conflicting:
        follow_up.append("resolve_conflicting_measurements_or_conditions")
    if layers.candidate:
        follow_up.append("review_candidate_reason_codes")
    return ScientificAnswerPayload(
        short_answer=answer_text,
        facts=[item.statement for item in layers.verified],
        limitations=stable_unique(limitations),
        conflicts=[*evidence_bundle_conflicts, *[item.statement for item in layers.conflicting]],
        gaps=evidence_bundle_gaps,
        follow_up=stable_unique(follow_up),
        sources_count=len(layers.verified),
    )


def synthesize_answer(request: AnswerSynthesisRequest) -> AnswerSynthesisResponse:
    layers = synthesize_evidence_layers(request.query_ir, request.evidence_bundle.evidence_items, request.candidate_items)
    evidence_items = [
        request.evidence_bundle.evidence_items[item.evidence_item_index]
        for item in layers.verified
        if item.evidence_item_index is not None
    ]
    unsupported_warnings = [
        UnsupportedWarning(statement=item.statement, reason_codes=item.reason_codes, source_span_ids=item.source_span_ids)
        for item in [*layers.candidate, *layers.conflicting, *layers.unsupported]
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
        evidence_layers=layers,
        answer_v2=build_scientific_answer_payload(
            answer_text,
            layers,
            request.evidence_bundle.gaps,
            request.evidence_bundle.conflicts,
        ),
        warnings=warnings,
    )
    return AnswerSynthesisResponse.model_validate(response.model_dump())


def detect_conflicts(request: ConflictDetectionRequest) -> ConflictDetectionResponse:
    groups: dict[str, list[ExtractionArtifact]] = {}
    for artifact in request.artifacts:
        if artifact.kind not in ("measurement", "claim", "property"):
            continue
        key = comparable_artifact_key(artifact)
        groups.setdefault(key, []).append(artifact)
    conflicts = []
    for key, artifacts in groups.items():
        unit_values = [(item, artifact_quantity(item)) for item in artifacts]
        unit_values = [(item, quantity) for item, quantity in unit_values if quantity is not None]
        units = {quantity["unit"] for _, quantity in unit_values if quantity.get("unit")}
        if len(units) > 1:
            conflicts.append(
                ConflictSignal(
                    value_key=key,
                    artifact_ids=[item.id for item, _ in unit_values],
                    reason="needs_unit_check: comparable artifacts use incompatible units",
                    confidence=0.64,
                )
            )
            continue
        values = [(item, quantity["value"]) for item, quantity in unit_values if quantity.get("value") is not None]
        if has_numeric_conflict([value for _, value in values], next(iter(units), "")):
            conflicts.append(
                ConflictSignal(
                    value_key=key,
                    artifact_ids=[item.id for item, _ in values],
                    reason="conflicting_values: comparable numeric values differ beyond tolerance",
                    confidence=0.78,
                )
            )
        conflicting_candidates = [item for item in artifacts if "conflicting_values" in item.reason_codes]
        if conflicting_candidates:
            conflicts.append(
                ConflictSignal(
                    value_key=key,
                    artifact_ids=[item.id for item in conflicting_candidates],
                    reason="conflicting_values: candidate reason code marks conflict",
                    confidence=0.82,
                )
            )
    return ConflictDetectionResponse(conflicts=conflicts, warnings=[DEGRADED_WARNING] if not settings.yandex_enabled else [])


def suggest_gaps(request: GapSuggestionRequest) -> GapSuggestionResponse:
    gaps = []
    if not request.evidence_bundle.evidence_items:
        gaps.append(GapSuggestion(gap_type="missing_evidence", description="Нет подтвержденных SourceSpan в EvidenceBundle.", priority="high"))
    filters = request.query_ir.filters
    evidence_text = " ".join(item.source_span.text for item in request.evidence_bundle.evidence_items)
    evidence_text_lower = evidence_text.lower()
    if filters.get("numeric_constraints") and not numeric_constraints_covered(filters.get("numeric_constraints", []), evidence_text):
        gaps.append(GapSuggestion(gap_type="missing_numeric_constraint", description="Вопрос содержит числовые ограничения, но evidence не подтверждает числовые значения.", priority="high"))
    if filters.get("geo_constraints"):
        if not geo_constraints_covered(filters["geo_constraints"], evidence_text):
            gaps.append(GapSuggestion(gap_type="missing_geo", description="Вопрос содержит географию, но evidence не подтверждает географический контекст.", priority="medium"))
    if filters.get("time_constraints") and not time_constraints_covered(filters.get("time_constraints", {}), evidence_text):
        gaps.append(GapSuggestion(gap_type="missing_time", description="Вопрос содержит временной диапазон, но evidence не подтверждает дату или период.", priority="medium"))
    source_types = [str(value).lower() for value in filters.get("source_type_constraints", [])]
    if source_types and not any(value in evidence_text_lower for value in source_types):
        gaps.append(GapSuggestion(gap_type="candidate_review", description="Вопрос ограничен типом источника, но evidence не подтверждает этот тип источника.", priority="medium"))
    query_entities = [str(value).lower() for value in request.query_ir.entities]
    if query_entities and request.evidence_bundle.evidence_items:
        missing_entities = [value for value in query_entities if value and value not in evidence_text_lower]
        if len(missing_entities) == len(query_entities):
            gaps.append(GapSuggestion(gap_type="candidate_review", description="Ключевые сущности Query IR не покрыты подтвержденным evidence.", priority="medium"))
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
            artifact_metadata = json.dumps(artifact.metadata, ensure_ascii=False).lower()
            artifact_text = f"{artifact.kind} {artifact.value} {artifact_metadata}".lower()
            overlap = [term for term in interest_terms if term and term in artifact_text]
            if not overlap:
                continue
            metadata_boost = metadata_match_boost(interest_terms, artifact.metadata)
            candidate_penalty = 0.55 if artifact.status != "confirmed" else 1.0
            reason_penalty = max(0.5, 1.0 - (0.12 * len(artifact.reason_codes)))
            score = min(
                1.0,
                interest.weight
                * (0.45 + 0.12 * len(overlap) + metadata_boost)
                * max(artifact.confidence, 0.1)
                * candidate_penalty
                * reason_penalty,
            )
            matches.append(NotificationMatch(interest_label=interest.label, artifact_id=artifact.id, score=round(score, 6), reason=", ".join(stable_unique(overlap)[:4])))
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
        "schema:dateCreated": request.answer.created_at.isoformat(),
        "st:generatedAt": datetime.now(UTC).isoformat(),
        "schema:text": request.answer.answer_text,
        "st:confidence": request.answer.confidence,
        "st:query": {
            "@type": "st:QueryIR",
            "@id": f"st:query:{request.answer.query_ir.id}",
            "schema:text": request.answer.query_ir.raw_query,
            "st:intent": request.answer.query_ir.intent,
            "st:entities": request.answer.query_ir.entities,
            "st:filters": request.answer.query_ir.filters,
        },
        "st:gaps": request.answer.evidence_bundle.gaps,
        "st:conflicts": request.answer.evidence_bundle.conflicts,
        "st:evidence": [
            {
                "@type": "st:SourceSpan",
                "@id": f"st:source-span:{item.source_span.id}",
                "st:documentId": item.source_span.document_id,
                "st:page": item.source_span.page,
                "st:startOffset": item.source_span.start_offset,
                "st:endOffset": item.source_span.end_offset,
                "st:sourceType": item.source_span.source_type,
                "st:claimIds": item.claim_ids,
                "st:entityIds": item.entity_ids,
                "st:relevanceScore": item.relevance_score,
                "st:extractionMethod": item.extraction_method,
                "schema:text": item.source_span.text,
            }
            for item in evidence
        ],
    }
    return JsonLdEnrichmentResponse(jsonld=jsonld, warnings=[DEGRADED_WARNING] if not settings.yandex_enabled else [])


def model_status() -> ModelStatusResponse:
    cache_available, cache_degraded_reason = redis_cache_status()
    return ModelStatusResponse(
        provider=settings.llm_provider,
        yandex_configured=settings.yandex_enabled,
        chat_model=settings.yandex_chat_model,
        embedding_doc_model=settings.yandex_embedding_doc_model,
        embedding_query_model=settings.yandex_embedding_query_model,
        embedding_dimensions=settings.yandex_embedding_dim,
        mode="llm" if settings.yandex_enabled else "deterministic_degraded",
        cache_backend=settings.model_cache_backend,
        cache_available=cache_available,
        cache_mode="memory+redis" if cache_available else "memory",
        cache_degraded_reason=cache_degraded_reason,
    )


def extract_first_number(text: str) -> float | None:
    match = re.search(r"\d+(?:[,.]\d+)?", text)
    if not match:
        return None
    return parse_float(match.group(0))


def comparable_artifact_key(artifact: ExtractionArtifact) -> str:
    metadata = artifact.metadata
    fields = {
        "kind": artifact.kind,
        "property": metadata_value(metadata, "property") or metadata_value(metadata, "parameter") or artifact.kind,
        "material": metadata_value(metadata, "material"),
        "process": metadata_value(metadata, "process"),
        "equipment": metadata_value(metadata, "equipment"),
        "geography": metadata_value(metadata, "geography") or metadata_value(metadata, "geo"),
        "time": metadata_value(metadata, "time") or metadata_value(metadata, "date"),
        "condition": metadata_value(metadata, "condition") or metadata_value(metadata, "conditions"),
    }
    return "|".join(f"{key}={normalize_comparable_value(value)}" for key, value in fields.items() if value)


def metadata_value(metadata: dict[str, Any], key: str) -> str:
    value = metadata.get(key)
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return ",".join(sorted(str(item) for item in value if item is not None))
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def normalize_comparable_value(value: str) -> str:
    return normalize_alias_text(str(value).replace("_", " "))


def artifact_quantity(artifact: ExtractionArtifact) -> dict[str, Any] | None:
    quantity = artifact.metadata.get("quantity")
    if isinstance(quantity, dict):
        unit = normalize_unit(str(quantity.get("unit", ""))) if quantity.get("unit") else ""
        value = quantity.get("value")
        return {"unit": unit, "value": float(value) if isinstance(value, int | float) else parse_optional_float(value)}
    quantities = artifact.metadata.get("quantities")
    if isinstance(quantities, list) and quantities and isinstance(quantities[0], dict):
        first = quantities[0]
        unit = normalize_unit(str(first.get("unit", ""))) if first.get("unit") else ""
        value = first.get("value")
        return {"unit": unit, "value": float(value) if isinstance(value, int | float) else parse_optional_float(value)}
    value = extract_first_number(artifact.value)
    unit_match = next((unit for unit in UNIT_ALIASES if unit.lower() in artifact.value.lower()), "")
    return {"unit": normalize_unit(unit_match), "value": value} if value is not None else None


def parse_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return parse_float(str(value))
    except ValueError:
        return None


def has_numeric_conflict(values: list[float], unit: str) -> bool:
    if len(values) < 2:
        return False
    tolerance = numeric_tolerance(unit)
    ordered = sorted(values)
    return (ordered[-1] - ordered[0]) > tolerance


def numeric_tolerance(unit: str) -> float:
    if unit == "%":
        return 0.05
    if unit in {"m/s", "mg/l", "mg/dm3"}:
        return 0.01
    return 0.000001


def numeric_constraints_covered(constraints: list[Any], evidence_text: str) -> bool:
    evidence_quantities = extract_numeric_constraints(evidence_text)
    if not constraints:
        return True
    if not evidence_quantities:
        return False
    return all(any(quantity_covers_constraint(quantity, constraint) for quantity in evidence_quantities) for constraint in constraints if isinstance(constraint, dict))


def quantity_covers_constraint(quantity: Quantity, constraint: dict[str, Any]) -> bool:
    expected_unit = normalize_unit(str(constraint.get("unit", ""))) if constraint.get("unit") else ""
    if expected_unit and quantity.unit != expected_unit:
        return False
    operator = str(constraint.get("operator", "eq"))
    expected_value = parse_optional_float(constraint.get("value"))
    expected_min = parse_optional_float(constraint.get("range_min"))
    expected_max = parse_optional_float(constraint.get("range_max"))
    if operator == "range" and expected_min is not None and expected_max is not None:
        if quantity.operator == "range":
            return quantity.range_min is not None and quantity.range_max is not None and quantity.range_min <= expected_min and quantity.range_max >= expected_max
        return quantity.value is not None and expected_min <= quantity.value <= expected_max
    if expected_value is None:
        return True
    if quantity.value is None:
        return False
    tolerance = numeric_tolerance(quantity.unit)
    return abs(quantity.value - expected_value) <= tolerance


def time_constraints_covered(constraints: dict[str, Any], evidence_text: str) -> bool:
    if not constraints:
        return True
    years = [int(match.group(0)) for match in re.finditer(r"\b(?:19|20)\d{2}\b", evidence_text)]
    if not years:
        return False
    start_year = constraints.get("start_year")
    end_year = constraints.get("end_year")
    if start_year is not None and end_year is not None:
        return any(int(start_year) <= year <= int(end_year) for year in years)
    return True


def geo_constraints_covered(constraints: list[Any], evidence_text: str) -> bool:
    if not constraints:
        return True
    extracted = {normalize_alias_text(value) for value in extract_geo_constraints(evidence_text)}
    normalized_text = normalize_alias_text(evidence_text)
    for constraint in constraints:
        normalized = normalize_alias_text(str(constraint))
        if normalized in normalized_text or normalized in extracted:
            continue
        return False
    return True


def metadata_match_boost(interest_terms: set[str], metadata: dict[str, Any]) -> float:
    metadata_text = json.dumps(metadata, ensure_ascii=False).lower()
    matches = sum(1 for term in interest_terms if term and term in metadata_text)
    return min(0.25, 0.08 * matches)


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
