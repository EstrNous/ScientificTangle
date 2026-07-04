import re

from shared.contracts import GeoContext, NormalizedDocument, Quantity
from shared.contracts.facts import AliasRef, TimeConstraint

NUMERIC_PATTERN = re.compile(
    r"(?P<operator><=|>=|≤|≥|<|>|до|не более|не менее|более|менее)?\s*"
    r"(?P<first>\d+(?:[,.]\d+)?)"
    r"(?:\s*[-–—]\s*(?P<second>\d+(?:[,.]\d+)?))?\s*"
    r"(?P<unit>%|мг/л|mg/l|мг/дм3|мг/дм³|г/л|g/l|м/с|m/s|л/с|l/s|°c|°C|кг/т|kg/t)",
    re.IGNORECASE,
)
ALIAS_PATTERN = re.compile(r"(?P<long>[A-Za-zА-Яа-яЁё0-9][A-Za-zА-Яа-яЁё0-9\s-]{2,80}?)\s*\((?P<short>[A-Za-zА-Яа-яЁё0-9-]{2,16})\)")
YEAR_RANGE_PATTERN = re.compile(r"(20\d{2})\s*[-–—]\s*(20\d{2})")
YEAR_PATTERN = re.compile(r"\b(20\d{2})\b")

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
    "russia": "Россия",
    "норильск": "Норильский регион",
    "norilsk": "Норильский регион",
    "кольский": "Кольский полуостров",
    "kola": "Кольский полуостров",
}


def enrich_normalized_document(document: NormalizedDocument) -> NormalizedDocument:
    quantities: list[Quantity] = []
    geo_contexts: list[GeoContext] = []
    time_contexts: list[TimeConstraint] = []
    alias_refs: list[AliasRef] = []
    seen_quantities: set[tuple[str, float, str, float | None, float | None, str | None]] = set()
    seen_geo: set[tuple[str, str | None]] = set()
    seen_time: set[tuple[int | None, int | None]] = set()
    seen_aliases: set[tuple[str, str, str | None]] = set()

    for span in document.source_spans:
        for quantity in extract_quantities(span.text, span.id):
            key = (quantity.operator, quantity.value, quantity.unit, quantity.range_min, quantity.range_max, span.id)
            if key not in seen_quantities:
                quantities.append(quantity)
                seen_quantities.add(key)
        for geo in extract_geo_contexts(span.text, span.id):
            key = (geo.location_name.lower(), span.id)
            if key not in seen_geo:
                geo_contexts.append(geo)
                seen_geo.add(key)
        for time_context in extract_time_contexts(span.text):
            key = (time_context.start_year, time_context.end_year)
            if key not in seen_time:
                time_contexts.append(time_context)
                seen_time.add(key)
        for alias_ref in extract_alias_refs(span.text, span.id):
            key = (alias_ref.alias.lower(), alias_ref.canonical_hint.lower(), span.id)
            if key not in seen_aliases:
                alias_refs.append(alias_ref)
                seen_aliases.add(key)

    metadata = {
        **document.metadata,
        "normalization_coverage": {
            "documents": 1,
            "source_spans": len(document.source_spans),
            "tables": len(document.table_blocks),
            "measurements": len(quantities),
            "geo_contexts": len(geo_contexts),
            "time_contexts": len(time_contexts),
            "aliases": len(alias_refs),
            "claims": 0,
            "time_context_source_span_ids": [
                span.id
                for span in document.source_spans
                if extract_time_contexts(span.text)
            ],
        },
    }
    return document.model_copy(
        update={
            "quantities": quantities,
            "geo_contexts": geo_contexts,
            "time_contexts": time_contexts,
            "alias_refs": alias_refs,
            "metadata": metadata,
        }
    )


def extract_quantities(text: str, source_span_id: str | None = None) -> list[Quantity]:
    quantities = []
    for match in NUMERIC_PATTERN.finditer(text):
        first = parse_float(match.group("first"))
        second_text = match.group("second")
        unit = normalize_unit(match.group("unit"))
        operator_text = (match.group("operator") or "").lower()
        if second_text is not None:
            second = parse_float(second_text)
            quantities.append(
                Quantity(
                    value=first,
                    unit=unit,
                    operator="range",
                    range_min=min(first, second),
                    range_max=max(first, second),
                    source_span_id=source_span_id,
                )
            )
            continue
        quantities.append(
            Quantity(
                value=first,
                unit=unit,
                operator=normalize_operator(operator_text),
                source_span_id=source_span_id,
            )
        )
    return quantities


def extract_geo_contexts(text: str, source_span_id: str | None = None) -> list[GeoContext]:
    lowered = text.lower()
    contexts = []
    for term, location_name in GEO_TERMS.items():
        if term in lowered:
            contexts.append(GeoContext(location_name=location_name, source_span_id=source_span_id))
    return unique_geo_contexts(contexts)


def extract_time_contexts(text: str) -> list[TimeConstraint]:
    contexts = []
    for match in YEAR_RANGE_PATTERN.finditer(text):
        contexts.append(
            TimeConstraint(
                start_year=int(match.group(1)),
                end_year=int(match.group(2)),
            )
        )
    if contexts:
        return contexts
    return [
        TimeConstraint(start_year=int(match.group(1)), end_year=int(match.group(1)))
        for match in YEAR_PATTERN.finditer(text)
    ]


def extract_alias_refs(text: str, source_span_id: str | None = None) -> list[AliasRef]:
    refs = []
    for match in ALIAS_PATTERN.finditer(text):
        canonical_hint = " ".join(match.group("long").split())[-80:].strip(" -")
        refs.append(
            AliasRef(
                alias=match.group("short").strip(),
                canonical_hint=canonical_hint,
                source_span_id=source_span_id,
            )
        )
    return refs


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


def unique_geo_contexts(contexts: list[GeoContext]) -> list[GeoContext]:
    result = []
    seen = set()
    for context in contexts:
        key = context.location_name.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(context)
    return result
