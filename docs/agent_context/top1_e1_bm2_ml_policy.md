# Top-1 E1: ML policy для retrieval, verification и synthesis

**Дата:** 2026-07-04
**Ветка:** `feat/top1-e1-bm2-ml-policy`
**Этап:** E1 — safe foundation
**Роль:** Backend/ML-2
**Область:** policy/spec для `services/model/`, будущих `services/retrieval/` и synthesis. Production query flow, Qdrant adapters, orchestrator и gateway API не меняются.

Связанные документы: [`top1_e0_contract_audit.md`](top1_e0_contract_audit.md), [`query_pipeline.md`](query_pipeline.md), [`ml_mvp_status.md`](ml_mvp_status.md), [`top1_parallel_execution_plan.md`](top1_parallel_execution_plan.md).

---

## 1. Цель E1

Зафиксировать общий язык для E2–E4: классы запросов, правила retrieval planner, reason codes verification, ожидания к AnswerPayloadV2 и policy синтеза. Это foundation без подключения к production query flow.

Границы из E0 сохраняются:

- `SourceSpan`, `EvidenceItem.source_span`, `QueryIR.raw_query`, `QueryIR.limit`, `AnswerPayload.answer_text`, `AnswerPayload.confidence`, `QueryRunPayload` top-level — frozen.
- Расширения разрешены через `QueryIR.intent`, backward-compatible ключи `QueryIR.filters`, `retrieval_trace`, model-local reason codes и synthesis wrapper.
- `AnswerPayloadV2` в E1 не добавляется в shared contracts; E3 должен принять BC-решение отдельно.

---

## 2. Классы запросов

Классы не являются новым shared enum в E1. Для E2 planner они задают нормализованную taxonomy поверх текущего `QueryIR.intent` и `filters`.

| Класс | Сигналы в Query IR | Primary retrieval | Verification focus |
|-------|--------------------|-------------------|--------------------|
| `semantic` | широкий вопрос без строгих numeric/geo/time constraints; intent `find_methods`, `explain`, `summarize` | semantic vector + rerank | SourceSpan presence, entity overlap, unsupported claims |
| `numeric` | `filters.numeric_constraints`, `numeric_filter`, единицы измерения, диапазоны, операторы | numeric/table + semantic fallback | unit compatibility, range match, comparable property/material/process |
| `geo` | `filters.geo_constraints`, `geo_filter`, геонимы, страны, регионы | geo-filtered semantic/table | source geography vs practice geography, jurisdiction mismatch |
| `temporal` | `filters.time_constraints`, годы, периоды, relative years | time-filtered semantic/table | source publication date, experiment date, requested interval |
| `comparative` | маркеры сравнения: лучше/хуже, максимум/минимум, vs, между, по сравнению | table/numeric + graph candidates + semantic | comparable dimensions, conflict separation, missing baseline |
| `graph_centric` | сущности/связи важнее текста: кто связан, какие claims, цепочки, противоречия | graph candidates + exact entity/claim lookup | claim/source provenance, entity resolution, alias confidence |
| `mixed` | два и более строгих constraint family или неоднозначный вопрос | planner fan-out по нескольким retriever profiles | per-profile reason codes, degraded/partial state |

Рекомендуемый deterministic classifier для E2:

1. Если есть numeric constraints и сравнительные маркеры — `comparative`.
2. Если есть numeric constraints без сравнения — `numeric`.
3. Если есть geo и time вместе с numeric или graph hints — `mixed`.
4. Если есть только geo — `geo`.
5. Если есть только time — `temporal`.
6. Если вопрос просит связи, граф, источник claim, противоречия или соседей сущности — `graph_centric`.
7. Иначе — `semantic`.

---

## 3. Retrieval Planner Rules

E2 должен создать deterministic `RetrievalPlan` или эквивалентный internal object без изменения shared contracts. Минимальная форма plan:

```json
{
  "query_class": "mixed",
  "retriever_profiles": ["semantic", "numeric", "table"],
  "filters": {
    "numeric_constraints": [],
    "geo_constraints": [],
    "time_constraints": {},
    "source_type_constraints": []
  },
  "trace": [
    {
      "profile": "numeric",
      "selected": true,
      "reason": "numeric_constraints_present",
      "filter_keys": ["numeric_constraints"]
    }
  ],
  "degraded_reasons": []
}
```

Planner не должен исполнять свободный Cypher и не должен заменять graph exact implementation из E3. Graph mode в E2 только планирует candidate channel и trace.

### Профили retrieval

| Profile | Когда выбирать | Минимальный выход trace |
|---------|----------------|-------------------------|
| `semantic` | всегда как fallback, кроме точных internal lookups | selected terms, embedding model, limit |
| `lexical` | короткие именованные сущности, формулы, аббревиатуры, exact phrase hints | normalized tokens, aliases used |
| `table` | numeric/comparative/table source hints | table/source type filters, row/column hints |
| `numeric` | `numeric_constraints` непустые | operator, value/range, unit, property hint |
| `geo` | `geo_constraints` непустые | requested geo values, normalized geo keys if available |
| `time` | `time_constraints` непустые | requested interval, source/experiment date field preference |
| `graph` | graph-centric или comparative/mixed с entity IDs | entity hints, relation hints, no Cypher in E2 |

### Правила фильтров

- `source_type_constraints` и legacy `source_types` должны нормализоваться в один planner key, но без удаления старого ключа до отдельного BC-gate.
- Numeric filters обязаны сохранять исходные единицы из Query IR; conversion допускается только как отдельный trace step.
- Geo filters не должны смешивать source country, practice country и jurisdiction без явного `geo_role`.
- Time filters должны различать `source_published_at`, `experiment_performed_at`, `source_ingested_at`, если эти поля доступны; если нет — trace пишет degraded reason.
- Access filter остаётся до synthesis и не может быть ослаблен planner-ом.

---

## 4. Verification Reason Codes

E1 расширяет только model-local `CandidateReasonCode`. Shared contracts не меняются.

| Code | Когда ставить | Layer |
|------|---------------|-------|
| `missing_source_span` | нет SourceSpan для факта или candidate | model extraction/synthesis |
| `low_confidence` | confidence ниже порога confirmed | model extraction |
| `ambiguous_alias` | alias связывает несколько entity или scope неясен | alias/entity verification |
| `conflicting_values` | сопоставимые claims дают разные значения | conflict detection |
| `needs_unit_check` | единицы не сопоставлены автоматически | numeric verification |
| `access_filtered` | evidence недоступен роли пользователя | retrieval/orchestrator warning |
| `schema_candidate` | тип/отношение не подтверждены schema registry | extraction/schema |
| `outside_time_range` | источник или измерение вне периода запроса | temporal verification |
| `geo_mismatch` | evidence относится к другой географии или geo role | geo verification |
| `unit_mismatch` | единицы несовместимы с constraint или между claims | numeric verification |
| `unsupported_claim` | утверждение не подтверждено verified evidence | synthesis |
| `unresolved_alias` | alias не удалось связать с canonical entity | alias/entity verification |
| `inaccessible_source` | SourceSpan или документ нельзя открыть/проверить | source resolver/access |

Правила применения:

- Confirmed layer не содержит reason codes.
- Candidate, conflicting и unsupported layer обязаны иметь хотя бы один reason code.
- `unsupported_claim` не заменяет конкретный код: если причина известна, используется пара, например `unsupported_claim` + `missing_source_span`.
- `inaccessible_source` применяется к ситуации, где ссылка или документ не проверены; `access_filtered` — когда access control осознанно отсёк evidence.
- `needs_unit_check` означает review needed; `unit_mismatch` означает проверенное несоответствие.

---

## 5. AnswerPayloadV2 Expectations

E1 не вводит `AnswerPayloadV2` в shared contracts. Для E3 целевая форма может быть новым DTO или BC-расширением `AnswerPayload`, но должна покрывать:

```json
{
  "short_answer": "",
  "confirmed_observations": [
    {
      "statement": "",
      "source_span_ids": [],
      "claim_ids": [],
      "confidence": 0.0
    }
  ],
  "candidate_observations": [
    {
      "statement": "",
      "reason_codes": []
    }
  ],
  "limitations": [],
  "conflicts": [],
  "gaps": [],
  "follow_up": [],
  "degraded_reasons": []
}
```

Минимальные требования:

- Every confirmed observation has at least one `source_span_id`.
- Candidate observations are not phrased as established facts.
- Conflicts stay separate from gaps and limitations.
- `short_answer` is either sourced summary or explicit degraded answer.
- Backward compatibility keeps `AnswerPayload.answer_text`, `confidence`, `evidence_bundle`, `query_ir` valid for old clients.

---

## 6. Synthesis Policy

Synthesis sees only `QueryIR`, verified `EvidenceBundle` and explicit candidate inputs. It must not read raw corpus or infer facts from unsupported context.

Rules:

1. Use `EvidenceBundle.evidence_items` as the only source for confirmed facts.
2. Cite every confirmed factual statement through SourceSpan IDs or source rows derived from them.
3. Do not promote candidate content to confirmed text.
4. If evidence is empty, return degraded answer with `insufficient_accessible_evidence` or equivalent warning.
5. If numeric/geo/time constraints are not covered, state limitation/gap instead of answering as if covered.
6. If evidence conflicts, summarize conflict and comparable conditions; do not average values.
7. If aliases are unresolved, state ambiguity in candidate/limitation layer.
8. Preserve unsupported warnings as structured data where possible; string flattening remains legacy until E3/E4.

Prompt/template policy:

- `answer_synthesis_v1` remains the current production prompt.
- E1 policy authorizes a future `answer_synthesis_v2` template, but it must be introduced in E3 with tests for unsupported synthesis ban and SourceSpan requirements.
- Prompt must require: evidence-only answer, citations, limitations, conflicts/gaps, no candidate-as-fact.

---

## 7. Decisions For E2-E4

| Этап | Разрешено после merge E1 | Запрещено в E1 |
|------|--------------------------|----------------|
| E2 retrieval planner | internal `RetrievalPlan`, trace, planner filter normalization | graph exact implementation, shared DTO break |
| E3 evidence synthesis | verified/candidate/conflicting/unsupported split, AnswerPayloadV2 decision, reason-code application | final production UI switch without backend gate |
| E4 orchestrator wiring | feature-flagged planner + verification + synthesis in query path | live streaming/source/auth cleanup from E5 |

Open decision carried from E0 D-04:

- Preferred E3 path: keep verified/candidate split in model-local synthesis response first, then add BC shared fields only after review. Do not mutate `EvidenceItem.source_span` or `SourceSpan`.

---

## 8. Checks For Later Stages

E3 tests must cover:

- unsupported candidate never appears in confirmed answer;
- confirmed observation without SourceSpan is rejected;
- numeric mismatch gets `unit_mismatch` or `needs_unit_check`;
- time mismatch gets `outside_time_range`;
- geo mismatch gets `geo_mismatch`;
- inaccessible source and access-filtered evidence are distinguishable;
- AnswerPayload legacy fields remain valid.

E4/E6 regression must include `git diff --check`, model unit tests, retrieval planner tests, orchestrator payload tests and gateway chat mapping tests after wiring.
