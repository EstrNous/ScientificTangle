# E7 Backend/ML: final no-live readiness summary

Дата: 2026-07-04

## Итоговый статус

Backend/ML no-live readiness: `warn`.

E7 Backend/ML готов к финальному handoff в рамках E0-E7: offline gates есть, official questions имеют reviewed demo `SourceSpan`, regression suites описаны, live checks честно отложены. Статус не `pass`, потому что часть production-risk остаётся вне no-live проверки или требует данных/инфраструктуры.

## P0

| ID | Статус | Описание |
|----|--------|----------|
| P0-BML-01 | closed | Confirmed artifacts требуют `SourceSpan`; слабые результаты остаются candidates с reason codes. |
| P0-BML-02 | closed | No-live gate `eval/offline_quality_gate.py` проверяет official `SourceSpan`, QueryIR constraints, access filtering fixture, e2e inventory и pinned inputs. |
| P0-BML-03 | closed | Live answer quality, Yandex smoke и live latency p95 явно помечены `blocked_by_policy`, без обхода demo-ответами. |
| P0-BML-04 | closed | Export Markdown/JSON boundary documented; JSON-LD/PDF не маскируются под готовые production formats. |
| P0-BML-05 | closed | E6 validator merged в `dev`, E7 может стартовать без dependency на несмёрженные PR предыдущего этапа. |

## P1 risks

| ID | Статус | Owner | Описание |
|----|--------|-------|----------|
| P1-BML-01 | open | Backend/ML | MinIO object delete при document purge остаётся открытым product-flow risk. |
| P1-BML-02 | open | Backend/ML | Runtime `ingestion_complete` / `interest_match` delivery не закрыт для production notifications. |
| P1-BML-03 | open | Backend/ML | Retrieval source identity drift (`document_id` vs span id) остаётся риском source correctness. |
| P1-BML-04 | open | Backend/ML + Frontend | Server-side audit CSV endpoint остаётся optional/open; UI может иметь client-only путь. |
| P1-BML-05 | blocked_by_data | Backend/ML + data | Full corpus не нормализован до reviewed `SourceSpan` expectations. |
| P1-BML-06 | dependency | External Orchestrator Refactor Owner | Large refactor `services/orchestrator/app/service/service.py` не входит в E7 Backend/ML. |

## No-live gates

| Проверка | Команда | Ожидаемый результат |
|----------|---------|---------------------|
| Offline readiness | `python eval/offline_quality_gate.py` | `overall_status: warn`; live checks `blocked_by_policy`; full corpus `blocked_by_data` |
| Make target | `make eval-offline-quality` | тот же gate и отчёты в `eval/reports/` |
| Demo quality без live report | `python eval/demo_quality_gate.py` | blocked overall из-за отсутствия live eval report |
| Backend suites | `python scripts/run_tests.py` | no-live suite; model live tests не включать |
| Diff hygiene | `git diff --check` | pass |

## Export / notification boundary

Authoritative export boundary остаётся в orchestrator.

Готово:

- Markdown export;
- JSON export;
- evidence table;
- source links;
- graph;
- gaps/conflicts;
- confidence/warnings;
- `QueryIR`;
- `retrieval_trace`;
- user role/access scope;
- audit event `document_exported`.

Backlog:

- JSON-LD production export wiring;
- PDF renderer;
- MinIO artifact storage как отдельная export service boundary;
- runtime notification delivery for ingestion/review/interest events.

## Deferred live-model tasks

Эти задачи не входят в E0-E7 и остаются `blocked_by_policy`:

- Yandex live smoke;
- live eval official questions;
- live eval corpus regression suite;
- generated final answer quality;
- live p50/p95 latency;
- comparison offline vs live reports;
- live model prompt/model tuning claims.

После отдельного разрешения команды их нужно вынести в новый post-E7 live-model plan.

## Handoff

Оператору использовать `docs/agent_context/nornikel_e7_bml_operator_runbook.md`.

Validator E7 должен проверить, что:

- no-live readiness status остаётся honest `warn`;
- `blocked_by_policy` не заменён live claims;
- `blocked_by_data` по full corpus не замаскирован demo coverage;
- `README.md`, public contracts, migrations, security и orchestrator god object refactor не затронуты этой карточкой.
