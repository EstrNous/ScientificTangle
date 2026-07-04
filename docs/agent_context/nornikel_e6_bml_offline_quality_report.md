# E6 Backend/ML: offline quality readiness

Дата: 2026-07-04

## Итог

E6 Backend/ML добавляет no-live quality gate для официальных сценариев и regression fixtures без вызовов live-моделей.

Статус: `warn`.

Причины:

- `pass`: official MVP questions имеют reviewed `expected_source_span_ids`.
- `pass`: regression suites покрывают official questions, retrieval, access filtering, unsupported claims и answer completeness.
- `pass`: access filtering имеет fixture с `expected_forbidden_source_span_ids`.
- `blocked_by_policy`: live answer quality и live latency p95 не проверяются на этапах E0-E7.
- `blocked_by_data`: full corpus ещё не нормализован до reviewed `SourceSpan` expectations.

## Gate

Команда для CI/no-live проверки:

```powershell
python eval/offline_quality_gate.py
```

Опционально можно усилить проверку заранее подготовленным offline eval report:

```powershell
python eval/offline_quality_gate.py --report eval/reports/latest.json
```

Makefile target:

```powershell
make eval-offline-quality
```

Если нужен нестандартный путь отчёта:

```powershell
make eval-offline-quality EVAL_OFFLINE_ARGS="--report eval/reports/latest.json"
```

## Что проверяется

- целостность pinned input manifest;
- наличие обязательных regression suites;
- запрет live model calls через `blocked_by_policy`;
- reviewed `expected_source_span_ids` для official MVP questions;
- наличие QueryIR expectations: entities, numeric, geo или time constraints;
- access filtering fixture с forbidden source spans;
- inventory no-live e2e smoke: source resolve, export и audit actions;
- явный `blocked_by_data` для full corpus reviewed source expectations.

## Не проверяется в E6

- live answer quality;
- Yandex live smoke;
- live latency p95;
- generated final answer quality from external models.

Эти проверки должны остаться отдельным post-E7 live-model планом.
