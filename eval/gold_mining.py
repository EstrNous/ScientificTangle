import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from shared.contracts import NormalizedDocument, SourceSpan


NUMERIC_PATTERN = re.compile(r"(\d+(?:[,.]\d+)?)(?:\s*[-–—]\s*(\d+(?:[,.]\d+)?))?\s*(%|мг/л|mg/l|мг/дм3|мг/дм³|м/с|m/s|кг/т|kg/t)", re.IGNORECASE)
ENTITY_PATTERN = re.compile(r"\b(?:Au|Ag|Mg|Ca|Na|Ni|Cu|Co|Fe|PGM|PGE|МПГ|ПГЭ)\b")


def load_documents(input_dir: Path) -> list[NormalizedDocument]:
    documents = []
    for path in input_dir.rglob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and "documents" in payload:
            documents.extend(NormalizedDocument.model_validate(item) for item in payload["documents"])
        elif isinstance(payload, dict):
            documents.append(NormalizedDocument.model_validate(payload))
    return documents


def mine_gold_items(documents: list[NormalizedDocument], limit: int) -> list[dict[str, Any]]:
    items = []
    for document in documents:
        for span in document.source_spans:
            if len(items) >= limit:
                return items
            numeric_constraints = extract_numeric_constraints(span.text)
            entities = sorted(set(ENTITY_PATTERN.findall(span.text)))
            if not numeric_constraints and not entities:
                continue
            items.append(
                {
                    "id": f"corpus-{len(items) + 1:03d}",
                    "split": "corpus_regression",
                    "text": build_question(document, span, numeric_constraints, entities),
                    "expected_entities": entities,
                    "expected_numeric_constraints": numeric_constraints,
                    "expected_geo_constraints": [],
                    "expected_time_constraints": {},
                    "expected_source_span_ids": [source_span_id(span)],
                    "answer_outline": [span.text[:240]],
                    "units_tolerance": default_tolerances(numeric_constraints),
                    "tags": ["corpus-derived"],
                }
            )
    return items


def build_question(document: NormalizedDocument, span: SourceSpan, numeric_constraints: list[dict[str, Any]], entities: list[str]) -> str:
    if numeric_constraints and entities:
        return f"Какие числовые параметры связаны с {', '.join(entities[:3])} в документе «{document.title}»?"
    if numeric_constraints:
        return f"Какие числовые параметры подтверждены в документе «{document.title}» на странице {span.page}?"
    return f"Какие сущности подтверждены источником в документе «{document.title}» на странице {span.page}?"


def extract_numeric_constraints(text: str) -> list[dict[str, Any]]:
    constraints = []
    for match in NUMERIC_PATTERN.finditer(text):
        first = parse_float(match.group(1))
        second_text = match.group(2)
        unit = normalize_unit(match.group(3))
        if second_text:
            second = parse_float(second_text)
            constraints.append({"operator": "range", "range_min": min(first, second), "range_max": max(first, second), "unit": unit})
        else:
            constraints.append({"operator": "eq", "value": first, "unit": unit})
    return constraints


def default_tolerances(numeric_constraints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"unit": item["unit"], "tolerance": 0.0} for item in numeric_constraints if item.get("unit")]


def parse_float(value: str) -> float:
    return float(value.replace(",", "."))


def normalize_unit(unit: str) -> str:
    aliases = {
        "мг/л": "mg/l",
        "mg/l": "mg/l",
        "мг/дм3": "mg/dm3",
        "мг/дм³": "mg/dm3",
        "м/с": "m/s",
        "m/s": "m/s",
        "кг/т": "kg/t",
        "kg/t": "kg/t",
        "%": "%",
    }
    return aliases.get(unit, aliases.get(unit.lower(), unit.lower()))


def source_span_id(span: SourceSpan) -> str:
    raw = f"{span.document_id}:{span.page}:{span.start_offset}:{span.end_offset}:{span.table_block_id or ''}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output", default="eval/corpus_gold_candidates.json")
    parser.add_argument("--limit", type=int, default=12)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    documents = load_documents(Path(args.input_dir))
    items = mine_gold_items(documents, args.limit)
    Path(args.output).write_text(json.dumps({"corpus_regression_questions": items}, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
