# E4 Backend/ML-1: eval regression

**Дата:** 2026-07-04
**Ветка:** `feat/top1-e4-bm1-eval-regression`
**Scope:** pinned demo artifact, regression suites, report comparison. Production query path и реальные модели не запускались.

## Результат

E4 фиксирует воспроизводимый eval-вход без live model outputs:

- `eval/pinned_demo_artifact.json` закрепляет входные файлы, роли и sha256.
- `eval/regression_suites.json` разделяет eval на suites: official questions, hybrid retrieval, access filtering, unsupported claims, answer completeness.
- `eval/run_eval.py` умеет запускать один suite через `--suite`, добавляет manifest/git metadata в report и пишет comparison report через `--baseline-report`.
- `eval/gold_questions.json` получил первое `expected_forbidden_source_span_ids` поле для dedicated access filtering gate.

## Pinned artifact

Закреплённые входы:

| Файл | Роль | sha256 |
|---|---|---|
| `eval/gold_questions.json` | gold questions | `8f98910198215edd37de23716f02bcc1f47fdbde91e383ff5d1a05cf5d3c12a0` |
| `demo/seed_data/mvp_normalized_documents.json` | normalized demo corpus | `4b1131075f0219e83138138b63ed4b1ee450e400b074a75c89267de58eeacb08` |
| `demo/official_questions.md` | official questions mirror | `967204c1fbdad4fbc74d725662c53f047aadfc9cf66f0273492adf5f57853a25` |

Правила обновления:

- менять artifact только отдельным eval regression PR;
- после изменения входного файла пересчитывать sha256;
- не коммитить ответы реальных моделей в pinned artifact;
- generated reports хранить отдельно в `eval/reports/`.

## Regression suites

| Suite | Назначение | Ключевые метрики |
|---|---|---|
| `official_questions` | 4 официальных MVP-вопроса | `query_trace_completeness`, `unsupported_claim_rate`, `answer_completeness`, `latency_ms_p95` |
| `hybrid_retrieval` | corpus-derived вопросы с expected spans | `citation_coverage`, `evidence_recall_at_k`, `numeric_correctness`, `entity_linking_f1`, `query_ir_constraint_recall` |
| `access_filtering` | forbidden source span leak check | `access_leak_rate` |
| `unsupported_claims` | контроль unsupported/candidate leakage | `unsupported_claim_rate`, `candidate_quality_review_rate`, `gap_precision` |
| `answer_completeness` | вопросы с `answer_outline` | `answer_completeness`, `query_trace_completeness` |

Примеры команд без запуска реальных моделей невозможны, потому что `run_eval.py` обращается к `--service-url`. Для CI/unit gate использовать только тесты runner-а. Для live gate после поднятия seeded stack:

```bash
python eval/run_eval.py --suite official_questions --documents demo/seed_data/mvp_normalized_documents.json
python eval/run_eval.py --suite hybrid_retrieval --documents demo/seed_data/mvp_normalized_documents.json
python eval/run_eval.py --suite access_filtering --documents demo/seed_data/mvp_normalized_documents.json
```

Сравнение до/после:

```bash
python eval/run_eval.py --suite official_questions --baseline-report eval/reports/before.json --output-base eval/reports/after
```

Runner создаст `eval/reports/after_comparison.json` и `eval/reports/after_comparison.md`.

## Gate для E6

Минимальный regression gate:

- `python -m pytest tests/integration/test_eval_runner.py tests/integration/test_access_leak.py`;
- `git diff --check`;
- для live seeded stack после разрешения организаторов: `official_questions`, `hybrid_retrieval`, `access_filtering`;
- при наличии baseline report comparison должен иметь `regression=false`;
- `access_leak_rate` должен оставаться `0.0` для suite `access_filtering`;
- `unsupported_claim_rate` не должен ухудшаться относительно baseline.

## Ограничения

- Реальные модели не запускались.
- `official-*` вопросы всё ещё не имеют reviewed `expected_source_span_ids`, поэтому `citation_coverage` для official suite остаётся проверкой наличия evidence, а не строгим recall.
- Access suite пока содержит один forbidden span smoke; E6 должен расширить fixture после auth-backed review.
