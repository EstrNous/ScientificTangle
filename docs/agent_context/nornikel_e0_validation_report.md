# НорСинтез E0: validation report (Validator)

**Дата:** 2026-07-04  
**Ветка:** `feat/nornikel-e0-validator`  
**Этап:** E0 — baseline и аудит  
**База:** `origin/dev` @ `dec5323` (после merge PR #68, #69, #70)

Связанные документы:

- [`nornikel_parallel_execution_plan.md`](nornikel_parallel_execution_plan.md)
- [`nornikel_e0_db_baseline.md`](nornikel_e0_db_baseline.md) — Databases (PR #68)
- [`nornikel_e0_bml_contract_api_eval_baseline.md`](nornikel_e0_bml_contract_api_eval_baseline.md) — Backend/ML (PR #69)
- [`nornikel_e0_fe_ui_audit.md`](nornikel_e0_fe_ui_audit.md) — Frontend (PR #70)

---

## 1. Merge gate

| PR | Ветка | Merge в `dev` | Артефакт |
|----|-------|---------------|----------|
| #68 | `feat/nornikel-e0-db-baseline` | да (`c0fe381`) | `nornikel_e0_db_baseline.md` |
| #69 | `feat/nornikel-e0-bml-contract-audit` | да (`9075b66`) | `nornikel_e0_bml_contract_api_eval_baseline.md` |
| #70 | `feat/nornikel-e0-fe-ui-audit` | да (`dec5323`) | `nornikel_e0_fe_ui_audit.md` |

**Вердикт:** gate E0 для ролей Databases, Backend/ML, Frontend — **pass**. Validator может закрывать этап.

---

## 2. Проверки Validator gate (план E0)

| Критерий | Результат | Детали |
|----------|-----------|--------|
| Три baseline report в `dev` | **pass** | только `docs/agent_context/*.md`, без кода |
| Нет live model claims | **pass** | live gates помечены `blocked_by_policy` в BML/FE; DB — N/A |
| Единая таблица gaps и owners | **pass** | §4 ниже |
| Production behavior не менялся | **pass** | коммиты E0 — docs-only (`34c28ea`, `55db538`, `e4f094a`) |
| `services/orchestrator/app/service/service.py` | **pass** | не трогался |
| Feature work E1+ | **pass** | не обнаружено в E0 merges |

---

## 3. Quality checks

| Проверка | Результат | Примечание |
|----------|-----------|------------|
| `git diff --check` | **pass** | на `origin/dev` |
| `python -m pytest shared/tests` | **pass** | 31 passed |
| `python -m pytest services/model/tests/test_model_v1.py` | **skipped** | 66 skipped (offline env, без `RUN_MODEL_TESTS`) |
| `cd ui && npm test` | **skipped** | `npm` отсутствует в PATH среды валидатора |
| `cd ui && npm run build` | **skipped** | `npm` отсутствует в PATH среды валидатора |
| Yandex live smoke | **blocked_by_policy** | `RUN_MODEL_TESTS=1` + credentials |
| Live eval `eval/run_eval.py` | **blocked_by_policy** | может вызвать live model path |
| Live answer quality / latency p95 | **blocked_by_policy** | запрещено планом E0–E7 |

### Spot-checks по baseline claims

| Claim | Проверка | Результат |
|-------|----------|-----------|
| Official `expected_source_span_ids` пустые | `eval/gold_questions.json` | **pass** — 4 official questions с `[]` |
| Production components без прямых `api/mock/` | grep `ui/src` (кроме tests/utils boundary) | **pass** — только `client.js`, `sourceResolver/*`, lifecycle utils |
| `user_interests` / `notifications` migrations | `notification_db/0001` | **pass** — подтверждено DB baseline |
| Orchestrator `export_jobs` authoritative | orchestrator `0002`+`0006` vs export_db `0001` | **pass** — drift зафиксирован как E1/E5 gap |

---

## 4. Единая таблица gaps и owners (E0 → E7)

Сводка согласованных gaps из трёх baseline report. Severity — максимум из ролевых оценок.

| ID | Gap | DB | BML | FE | Owner этапа | Blocker E1 |
|----|-----|----|-----|-----|-------------|------------|
| G-01 | PG `review_decisions` / queue indexes | да | да | — | E1 DB, E2 DB | нет (E1 scope) |
| G-02 | Review API / `ReviewDecisionPayload` | — | да | FE-17 | E1 BML, E2 FE | нет |
| G-03 | `notifications.reference_type` | да | — | — | E1 DB | **да** — typed notification contract |
| G-04 | Notification match result persistence | да | да | — | E1 DB, E1 BML | **да** |
| G-05 | Interests GET/PUT API + shared payload | — | да | FE-10 | E1 BML, E1 FE | **да** |
| G-06 | Delete document API + tombstone/cascade | да | да | — | E1 DB, E1 BML, E2 DB | частично E1 |
| G-07 | Export job async contract + export_db drift | да | да | FE-08 | E1 boundary, E5 | **да** (boundary) |
| G-08 | Eval report payload vs `StrategicEvaluationPayload` | — | да | FE-11 | E1 BML, E6 | нет |
| G-09 | Source highlight / `table_row_id` fields | да | да | FE-02, FE-04 | E2 DB, E1/E4 BML, E2 FE | нет |
| G-10 | Source 403 `access_denied` UI + typed retrieval | — | да | FE-03 | E4 BML, E2/E4 FE | нет |
| G-11 | Notification poll `?since=` / cursor | да | да | FE-05 | E3/E5 DB, E3/E5 BML, E3 FE | нет |
| G-12 | Notification click → source/document | — | — | FE-06 | E3 FE | нет |
| G-13 | Admin save PATCH + audit | да | — | FE-16 | E3 BML/FE | нет |
| G-14 | Audit cursor pagination / CSV | да | — | FE-15 | E3/E5 DB, E5 FE | нет |
| G-15 | Client RBAC vs backend role | — | — | FE-01 | E4 FE | нет |
| G-16 | Search geo/year/numeric filters | — | — | FE-12 | E4 FE/BML | нет |
| G-17 | Dictionary version manager UI | — | — | FE-20 | E4 FE | нет |
| G-18 | Upload `task.stages[]` stepper | — | — | FE-21 | E4 FE | нет |
| G-19 | Server export + JSON-LD honesty | да | да | FE-08, FE-09 | E5 | нет |
| G-20 | Official reviewed `SourceSpan` ids | — | да | — | E2 BML | **blocked_by_data** |
| G-21 | reset без Neo4j/Qdrant/MinIO | да | — | — | E6 DB | нет |
| G-22 | Simulated lifecycle mock in prod utils | — | — | FE-22 | E6 FE | нет |

---

## 5. Blockers и dependencies перед E1

### Blockers (нужно закрыть в E1, baseline неполный без них)

| ID | Blocker | Роли E1 | Dependency |
|----|---------|---------|------------|
| B-E1-01 | Нет shared contracts: interests GET/PUT, notification typed list, delete result, export job status, review queue/decision | BML + FE clients | G-05, G-04, G-06, G-07, G-02 |
| B-E1-02 | `notifications.reference_type` и match-result storage | DB | G-03, G-04 |
| B-E1-03 | Authoritative export boundary (orchestrator vs `export_db`) | DB + BML doc | G-07, R-01 из DB baseline |
| B-E1-04 | Document deletion tombstone / cascade metadata (минимум PG) | DB | G-06 |
| B-E1-05 | PG `review_decisions` foundation | DB | G-01 |

### Dependencies (не блокируют старт E1, но требуют координации)

| ID | Dependency | Этап |
|----|------------|------|
| D-E1-01 | Source highlight field naming (`highlight_*` vs offsets) — согласовать BML/FE при E1 contracts | E1 |
| D-E1-02 | `export_db` migrations не в compose CMD — риск при ручном seed | E1 DB |
| D-E1-03 | Official expected spans — `blocked_by_data` до E2 corpus review | E2 BML |

### Не входит в Validator / E0

| Item | Статус |
|------|--------|
| God object refactor `orchestrator/.../service.py` | deferred — External Orchestrator Refactor Owner |
| Live model eval / Yandex smoke / p95 | `blocked_by_policy` |
| Mock layer removal | E4+ per plan |

---

## 6. Мелкие интеграционные исправления (Validator)

| Fix | Файл | Причина |
|-----|------|---------|
| Добавлены E0 baseline и validation report в навигацию агентов | `project_structure.md` | новые значимые `docs/agent_context/` артефакты не были перечислены |
| Cross-link sibling baselines между тремя E0 report | `nornikel_e0_*_baseline.md`, `nornikel_e0_fe_ui_audit.md` | единая навигация между ролевыми артефактами |

Код production services, migrations, UI — **не менялся**.

---

## 7. Итог

| Вопрос | Ответ |
|--------|-------|
| E0 baseline complete? | **да** — три ролевых report согласованы, gaps разнесены по E1–E7 |
| Можно начинать E1? | **да** — с учётом blockers §5 (это scope E1, не дефект E0) |
| Live quality | **blocked_by_policy** — честно зафиксировано во всех report |
| Validator PR ready? | **да** — `feat/nornikel-e0-validator` |

**Вердикт этапа E0:** **pass** (audit-only, production behavior не изменён).
