# Top-1 E1: fact contracts (Backend/ML-1)

**Дата:** 2026-07-04  
**Ветка:** `feat/top1-e1-bm1-fact-contracts`  
**Этап:** E1 — safe foundation  
**Основа:** [`top1_e0_contract_audit.md`](top1_e0_contract_audit.md), [`top1_e0_bm1_eval_baseline.md`](top1_e0_bm1_eval_baseline.md)

---

## 1. Решение

Существующих shared-структур **достаточно** для E2 normalization при минимальном BC-расширении provenance и типизации de-facto схем `QueryIR.filters`. Ontology, миграции и security **не менялись**.

E2 работает на:

| Домен | Shared-тип | Граница provenance | QueryIR.filters |
|-------|------------|--------------------|-----------------|
| Numeric | `Quantity` | `source_span_id` (optional, BC) | `numeric_constraints: list[Quantity dict]` |
| Geo | `GeoContext` | `source_span_id` (optional, BC) | `geo_constraints: list[str]` + `geo_filter` |
| Time | `TimeConstraint` (новый) | `NormalizedDocument.time_contexts` | `time_constraints: dict` |
| Alias | `AliasRef` (новый) | `source_span_id`, `entity_id` (optional) | `aliases: list[{alias, canonical_hint}]` |
| Table | `TableBlock` + `SourceSpan` | `SourceSpan.table_block_id`, `source_type="table"` | — |
| Table row/cell | `TableEvidenceRef` (новый) | `table_block_id` + `source_span_id` | metadata extraction |

Новые классы: `shared/contracts/facts.py` — `TimeConstraint`, `AliasRef`, `TableEvidenceRef`.

---

## 2. Минимальный contract layer

### 2.1 Quantity (numeric facts)

```python
Quantity(
    value: float,
    unit: str,
    operator: "eq" | "lt" | "le" | "gt" | "ge" | "range" = "eq",
    range_min: float | None = None,
    range_max: float | None = None,
    source_span_id: str | None = None,  # E1 BC
)
```

- Ingestion/knowledge E2: заполнять `NormalizedDocument.quantities` с `source_span_id`.
- Model extraction уже кладёт `quantity` в `ExtractionArtifact.metadata`; E2 выравнивает с document-level list.
- Query path: `QueryIR.filters["numeric_constraints"]` — сериализованные `Quantity`; `numeric_filter` — первый constraint.

### 2.2 GeoContext (geo facts)

```python
GeoContext(
    location_name: str,
    latitude: float | None = None,
    longitude: float | None = None,
    region: str | None = None,
    source_span_id: str | None = None,  # E1 BC
)
```

- Document-level: `NormalizedDocument.geo_contexts`.
- Query path: строковый список `geo_constraints` + дублирующий `geo_filter` для первого geo.

### 2.3 TimeConstraint (temporal facts)

De-facto ключи из model `build_query_ir` и knowledge Neo4j adapter:

| Ключ | Тип | Пример |
|------|-----|--------|
| `relative_years` | `int` | `{"relative_years": 5}` |
| `start_year`, `end_year` | `int` | `{"start_year": 2022, "end_year": 2025}` |
| `from`, `to` | `str` (ISO date) | published_after/before в graph search |

- Document-level: `NormalizedDocument.time_contexts: list[TimeConstraint]`.
- Query path: `QueryIR.filters["time_constraints"]` — dict, валидируется через `TimeConstraint.from_filter_dict`.
- E2 ingestion извлекает годы/периоды из текста и таблиц с привязкой к `SourceSpan`.

### 2.4 AliasRef (entity aliases)

De-facto формат в `QueryIR.filters["aliases"]`:

```json
{"alias": "Ni", "canonical_hint": "никель"}
```

Расширение E1 (optional, BC для filters):

```json
{"alias": "Ni", "canonical_hint": "никель", "source_span_id": "abc123", "entity_id": "ent-1"}
```

- Document-level: `NormalizedDocument.alias_refs`.
- Model-local: `ExtractionArtifact` kind=`alias` остаётся primary extraction boundary до E3.
- Seed dictionary: `dictionaries/aliases_mvp.json` — вне shared freeze.

### 2.5 Table evidence

**Новый shared DTO не обязателен** для базового table path:

1. `TableBlock` — структура таблицы (`headers`, `rows`, `caption`, `metadata`).
2. `SourceSpan` с `source_type="table"` и `table_block_id` — текстовый фрагмент строки/ячейки.
3. Model extraction: `metadata.table_block_id` + `metadata.quantities` на measurement artifacts.

`TableEvidenceRef` — optional typed link для row/cell provenance в E2 coverage report:

```python
TableEvidenceRef(
    table_block_id: str,
    source_span_id: str,
    row_index: int | None = None,
    column_index: int | None = None,
)
```

---

## 3. D-04: verified vs candidate layer

**Решение E1:** разделение confirmed/candidate **остаётся в model-local** `ExtractionArtifact` / `StructuredExtractionResponse`. Shared `EvidenceBundle` и `EvidenceItem` **не расширяются** до E3 gate.

Обоснование (из E0 audit):

- `EvidenceItem.source_span` — freeze point.
- E3 verification заполнит `has_conflicts`, `conflicts` и synthesis wrappers.
- E2 normalization пишет в `NormalizedDocument` fact fields, не в evidence bundle.

---

## 4. Freeze и extension zones (наследие E0)

| Объект | E1 действие |
|--------|-------------|
| `SourceSpan.*` | freeze — без изменений |
| `Quantity`, `GeoContext` core fields | freeze — добавлен только optional `source_span_id` |
| `TableBlock.*` | freeze |
| `QueryIR.filters` keys | extension doc — схемы формализованы |
| `NormalizedDocument` | BC fields `time_contexts`, `alias_refs` |
| `EvidenceBundle` verified split | отложено до E3 |

---

## 5. Контракт для E2 normalization

E2 Backend/ML-1 **может начинать** без дополнительных shared DTO:

1. Заполнять `quantities`, `geo_contexts`, `time_contexts`, `alias_refs` на `NormalizedDocument` с `source_span_id`.
2. Создавать table row `SourceSpan` с `table_block_id` и optional `TableEvidenceRef` в coverage metadata.
3. Использовать `TimeConstraint` / `AliasRef` helpers для валидации и сериализации.
4. Не трогать `QueryIR` core fields и `EvidenceBundle` shape.

Проверки E2 должны включить:

- `python -m pytest shared/tests/test_fact_contracts.py shared/tests/test_contracts.py`
- BC: старые `NormalizedDocument` JSON без новых полей десериализуются.
- Provenance: confirmed facts в document layer имеют non-empty `source_span_id` где применимо.

---

## 6. Связь с eval baseline (E0)

Official questions (`official-001`…`004`) требуют numeric/geo/time normalization для метрик `numeric_correctness`, `geo_correctness`, `query_ir_constraint_recall`. E1 контракты задают **куда** E2 пишет нормализованные факты, чтобы E4 eval regression мог проверять layer-aware coverage.

---

## 7. Итог

- Добавлен минимальный fact layer: `TimeConstraint`, `AliasRef`, `TableEvidenceRef` + provenance на `Quantity`/`GeoContext` + document fields `time_contexts`/`alias_refs`.
- Production query path **не изменён**.
- E2 normalization имеет явный contract boundary без ontology/migration changes.
