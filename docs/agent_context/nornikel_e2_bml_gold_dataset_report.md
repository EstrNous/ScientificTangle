# E2 Backend/ML: offline gold dataset

Дата: 2026-07-04.

## Scope

Карточка: `E2 Backend/ML`, ветка `feat/nornikel-e2-bml-gold-dataset`.

В рамках карточки обновлены только offline eval/gold artifacts, reviewed SourceSpan fixtures, no-live quality metadata и тесты схемы. Live model calls не запускались: этот класс проверок остается `blocked_by_policy`.

## Dataset access

Полный сырой dataset доступен локально по пути `F:\Задача 2. Научный клубок\Источники информации`.

Инвентаризация на момент проверки:

| Показатель | Значение |
|---|---:|
| Всего файлов | 1453 |
| Общий размер | 5220844533 байт |
| PDF | 1163 |
| DOCX | 115 |
| ZIP | 79 |
| XLS | 46 |
| DOC | 18 |
| RAR | 16 |
| PPTX | 5 |
| XLSX | 3 |
| DOCM | 3 |

Сырой corpus не коммитится в репозиторий. В каталоге нет готового normalized JSON слоя с `SourceSpan`, поэтому source ids из полного корпуса пока нельзя считать reviewed. Это зафиксировано в `eval/reviewed_source_fixtures.json` как `blocked_by_data` или `candidate` с reason codes `raw_corpus_not_normalized` и `needs_expert_source_span_review`.

## Official questions

Для всех 4 official questions заполнены reviewed expected `SourceSpan` ids из уже нормализованного demo seed `demo/seed_data/mvp_normalized_documents.json`.

| Question | SourceSpan id | Статус |
|---|---|---|
| `official-001` | `fd41e40302889dc4` | reviewed demo source |
| `official-002` | `5bbd52f818e388f0` | reviewed demo source |
| `official-003` | `e68ad5f96111645c` | reviewed demo source |
| `official-004` | `133421dd573f9d94` | reviewed demo source |

Для полного сырого корпуса подобраны candidate document paths там, где они видны по именам файлов:

| Question | Candidate paths |
|---|---|
| `official-001` | нет надежного filename match, `blocked_by_data` |
| `official-002` | `Обзоры\Электроэкстракция никеля. Влияние состава электролита.docx`; `Обзоры\Обзор технических решений в области электролитического производства никеля и меди.docx` |
| `official-003` | `Обзоры\Распределение Au, Ag и МПГ между меднымникелевым штейном и шлаком.docx`; `Статьи\43 Повышение селективности концентратов МПГ в химико-металлургическом цехе КГМК.docx` |
| `official-004` | `Обзоры\Методы очистки шахтных вод.docx` |

## Added artifacts

- `eval/gold_questions.json`: official questions now have reviewed expected `SourceSpan` ids and review metadata.
- `eval/reviewed_source_fixtures.json`: reviewed official source candidates, full corpus inventory, review queue fixtures, gap fixtures, conflict fixtures, reason codes.
- `eval/regression_suites.json`: added `reviewed_sources` suite.
- `eval/pinned_demo_artifact.json`: pinned reviewed fixture and updated input hash.
- `eval/demo_quality_gate.py`: known limits no longer say official questions have no reviewed spans; the remaining limit is full raw corpus normalization.

## Reason codes

Used in E2 fixtures:

| Reason code | Meaning |
|---|---|
| `blocked_by_policy` | live model calls are forbidden in E0-E7 |
| `blocked_by_data` | raw corpus is available but no reviewed normalized SourceSpan exists |
| `raw_corpus_not_normalized` | files are raw PDF/DOC/DOCX/PPTX/XLS/archive inputs |
| `reviewed_source_span_ids_missing_for_full_corpus` | full corpus source ids cannot be asserted yet |
| `no_reviewed_span_for_official_question` | no reliable full-corpus span for the question |
| `needs_expert_source_span_review` | candidate document path requires normalization and expert review |
| `needs_unit_check` | numeric or unit evidence requires review before confirmation |

## No-live status

Live answer quality, Yandex smoke, live eval and latency claims were not run and remain `blocked_by_policy`.

## Next dependencies

No dependency on unsmerged PR was needed for this Backend/ML E2 slice. Full-corpus reviewed ids for E3/E4 depend on a future normalization/review pass over the external raw corpus, not on live model calls.
