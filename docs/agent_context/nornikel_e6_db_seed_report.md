# НорСинтез E6: repeatable seed report (Databases)

**Дата:** 2026-07-04  
**Ветка:** `feat/nornikel-e6-db-seed-reliability`  
**Этап:** E6 — Offline quality и CI

Связанные документы: [`nornikel_parallel_execution_plan.md`](nornikel_parallel_execution_plan.md), [`nornikel_e5_db_storage_ownership.md`](nornikel_e5_db_storage_ownership.md), [`nornikel_e6_db_backup_restore_gaps.md`](nornikel_e6_db_backup_restore_gaps.md).

---

## 1. Цель

Повторяемый clean reset/reseed gate для offline quality и CI без live models: PostgreSQL fixtures E2–E5, auth users, orchestrator RBAC, опционально Neo4j/Qdrant/MinIO reset и demo corpus ingest.

---

## 2. Скрипты

| Скрипт | Назначение |
|--------|------------|
| `scripts/seed_inventory.py` | Counts report + offline/full reset gate |
| `scripts/seed_reset_gate.py` | Тонкая обёртка над `seed_inventory.main` |
| `scripts/reset_pg_demo.py` | TRUNCATE PG demo tables (используется gate) |

---

## 3. Режимы gate

### 3.1 `report` (по умолчанию)

```bash
python scripts/seed_inventory.py --mode report
python scripts/seed_inventory.py --mode report --include-remote
```

Считает объекты в PostgreSQL; с `--include-remote` — Neo4j, Qdrant, MinIO (если доступны).

### 3.2 `offline`

```bash
python scripts/seed_inventory.py --mode offline --output tmp/seed_offline_report.json
```

Шаги:

1. TRUNCATE таблиц из `reset_pg_demo.DEFAULT_TABLES`
2. Seed auth users (`admin`, `researcher`, `analyst`, `manager`, `external_partner`)
3. Seed orchestrator RBAC (`roles`, `permissions`, `role_permissions`)
4. Seed offline fixtures E2→E5 (`seed_e5_fixtures`)
5. Counts report + validation против fixture expectations

Не требует Docker services кроме PostgreSQL.

### 3.3 `full`

```bash
python scripts/seed_inventory.py --mode full --output tmp/seed_full_report.json
```

Дополнительно:

1. `POST /v1/graph/reset` (knowledge → Neo4j)
2. `POST /v1/index/reset` (retrieval → Qdrant `st_evidence_v1`)
3. MinIO purge buckets через `docker exec` (`MINIO_CONTAINER`, default `st-minio`)
4. `scripts/seed_demo.py` — dictionaries + demo corpus ingest через gateway API

`--skip-demo-ingest` отключает corpus ingest (только storage reset).

---

## 4. Counts report (schema `seed_inventory.v1`)

| Метрика | Источник | Offline minimum (fixtures) |
|---------|----------|----------------------------|
| `users` | PG `users` | 2 |
| `indexed_documents` | PG `indexed_documents` | 5 |
| `source_span_lookup` | PG `source_span_lookup` | 4+ |
| `table_rows` | fixture metadata | spans с `table_row_id` |
| `review_decisions` | PG | E2 fixtures |
| `export_jobs` / `export_artifacts` | PG | E5 fixtures |
| `audit_events` / `audit_csv_exports` | PG | E4+E5 |
| `notifications` | PG | E5 product events |
| `user_interests` | PG | E3 workflow |
| `vectors` | Qdrant `st_evidence_v1` | 0 offline / >0 после ingest |
| `graph_nodes`, `claims` | Neo4j labels | 0 offline / >0 после ingest |
| `dictionary_versions` | Neo4j `DictionaryVersion` | 0 offline / ≥1 после seed_demo |

Validation: `inventory.validation.status` = `pass` если PG counts ≥ fixture minimums.

---

## 5. Makefile targets

```makefile
seed-counts:
	python scripts/seed_inventory.py --mode report --include-remote

reset-reseed-offline:
	python scripts/seed_inventory.py --mode offline --output tmp/seed_offline_report.json

reset-reseed:
	python scripts/seed_inventory.py --mode full --output tmp/seed_full_report.json
```

---

## 6. Зависимости этапа

| ID | Статус | Комментарий |
|----|--------|-------------|
| E5 product events storage | **merged** | `origin/dev` @ PR #89 |
| E5 validator | **merged** | PR #92 |
| Demo corpus ingest (`seed_demo.py`) | **runtime** | Требует поднятый stack; без live models |
| Live model quality | **blocked_by_policy** | Не входит в E6 DB scope |

---

## 7. Локальные проверки

```bash
python -m pytest tests/performance/test_seed_inventory.py -q
python scripts/seed_inventory.py --mode report
git diff --check
```

Offline reseed (при доступном PostgreSQL):

```bash
python scripts/seed_inventory.py --mode offline --output tmp/seed_offline_report.json
```

**blocked_by_policy:** full gate с `seed_demo.py` не запускался без поднятого stack и live model policy.
