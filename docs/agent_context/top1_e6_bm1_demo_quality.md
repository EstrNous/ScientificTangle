# E6 Backend/ML-1: demo quality

**Дата:** 2026-07-04  
**Ветка:** `feat/top1-e6-bm1-demo-quality`  
**Scope:** финальный demo quality gate по official questions и regression suites без запуска реальных моделей.

## Результат

E6 не запускал live model/eval stack, потому что организаторы запретили трогать реальные модели. Вместо подмены результата добавлен offline quality gate `eval/demo_quality_gate.py`, который:

- проверяет sha256 pinned inputs из `eval/pinned_demo_artifact.json`;
- проверяет наличие обязательных suites в `eval/regression_suites.json`;
- валидирует уже полученный live JSON report, если он передан через `--report`;
- явно возвращает `overall_status=blocked`, если live report отсутствует.

Команда для текущего безопасного preflight:

```bash
python eval/demo_quality_gate.py
```

Команда для финального gate после отдельного разрешения на seeded stack и реальные модели:

```bash
python eval/run_eval.py --suite official_questions --documents demo/seed_data/mvp_normalized_documents.json --output-base eval/reports/e6_official_questions
python eval/run_eval.py --suite hybrid_retrieval --documents demo/seed_data/mvp_normalized_documents.json --output-base eval/reports/e6_hybrid_retrieval
python eval/run_eval.py --suite access_filtering --documents demo/seed_data/mvp_normalized_documents.json --output-base eval/reports/e6_access_filtering
python eval/run_eval.py --suite unsupported_claims --documents demo/seed_data/mvp_normalized_documents.json --output-base eval/reports/e6_unsupported_claims
python eval/run_eval.py --suite answer_completeness --documents demo/seed_data/mvp_normalized_documents.json --output-base eval/reports/e6_answer_completeness
python eval/run_eval.py --documents demo/seed_data/mvp_normalized_documents.json --output-base eval/reports/e6_all
python eval/demo_quality_gate.py --report eval/reports/e6_all.json
```

## Pass/fail критерии

| Проверка | Pass |
|---|---|
| Pinned input integrity | sha256 всех inputs совпадает с manifest |
| Regression suite inventory | объявлены `official_questions`, `hybrid_retrieval`, `access_filtering`, `unsupported_claims`, `answer_completeness` |
| `answered_questions` | `answered_200 == total_questions` |
| `question_blockers` | нет blocker question ids |
| `citation_coverage` | `>= 0.8` |
| `unsupported_claim_rate` | `<= 0.1` |
| `answer_completeness` | `>= 0.8` |
| `query_trace_completeness` | `>= 1.0` |
| `access_leak_rate` | `== 0.0` |
| `latency_ms_p95` | `<= 5000` |

## Текущий статус

| Блок | Статус | Пояснение |
|---|---|---|
| Pinned input integrity | pass | manifest остаётся E4/E5-compatible |
| Regression suite inventory | pass | все обязательные suites объявлены |
| Official questions live run | blocked | запрещён запуск реальных моделей |
| Unsupported claim rate | blocked | нужен live report |
| SourceSpan coverage | blocked | нужен live report с evidence |
| Answer completeness | blocked | нужен live report |
| Conflict/gap behavior | blocked | нужен live report и reviewed expectations |

Итог: demo quality gate готов как проверяемая процедура, но финальный demo pass/fail остаётся `blocked` до разрешённого live прогона.

## Известные ограничения

- Нельзя коммитить live model answers как baseline artifact.
- `official-*` вопросы всё ещё не имеют reviewed `expected_source_span_ids`; для них `citation_coverage` остаётся проверкой наличия evidence, а не строгим recall.
- `access_filtering` пока покрывает узкий forbidden span smoke; для демо-финала нужен расширенный auth-backed fixture.
- E5-D-01 остаётся preflight-требованием: active dictionary должен быть создан и активирован до `/api/query`.
- Retrieval source identity drift из E5 требует отдельного решения команды перед тем, как делать `access_filtering` hard blocker для широкого корпуса.

## Проверки карточки

- `python -m pytest tests/integration/test_eval_runner.py tests/integration/test_access_leak.py tests/integration/test_demo_quality_gate.py`
- `python eval/demo_quality_gate.py`
- `git diff --check`
