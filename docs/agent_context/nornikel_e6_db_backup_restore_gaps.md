# НорСинтез E6: backup/restore gaps (Databases)

**Дата:** 2026-07-04  
**Ветка:** `feat/nornikel-e6-db-seed-reliability`  
**Этап:** E6 — Offline quality и CI

Связанные документы: [`nornikel_e6_db_seed_report.md`](nornikel_e6_db_seed_report.md), [`nornikel_e0_db_baseline.md`](nornikel_e0_db_baseline.md).

---

## 1. Текущий scope backup/restore

| Store | Backup script | Restore script | Статус E6 |
|-------|---------------|----------------|-----------|
| PostgreSQL | `scripts/backup_db.sh` → `postgres.dump` (pg_dump custom) | `scripts/restore_db.sh` → pg_restore `--clean --if-exists` | **covered** |
| Neo4j | `scripts/backup_db.sh` → `neo4j.cypher` (APOC export) | `scripts/restore_db.sh` → cypher-shell stdin | **partial** |
| Qdrant | — | — | **gap** |
| MinIO | — | — | **gap** |
| Redis | — | — | **out of scope E6** (ephemeral cache) |

---

## 2. PostgreSQL

**Покрытие:** single-database dump `scientific_tangle` включает все PG chains:

- auth_audit (`users`, `refresh_sessions`)
- orchestrator (`indexed_documents`, `export_jobs`, `audit_events`, …)
- notification_db tables в той же БД (`notifications`, `user_interests`, …)
- chat_ui_db tables (`admin_settings`, `chat_sessions`, …)

**Ограничения:**

- `infra/postgres/export_db` deprecated stub — не в runtime compose
- После restore нужен `python scripts/migrate_pg_layers.py` если schema drift
- Seed gate (`--mode offline`) восстанавливает offline fixtures без dump

---

## 3. Neo4j

**Backup:** `backup_db.sh` пытается `apoc.export.cypher.all`; при отсутствии APOC пишет placeholder `neo4j.meta`.

**Restore:** `restore_db.sh` pipe в cypher-shell; ошибки проглатываются (`|| echo skipped`).

**Gaps (E6):**

| Gap | Риск | Mitigation E6 |
|-----|------|---------------|
| APOC не в community image | Backup без полного graph dump | `POST /v1/graph/reset` + `seed_demo.py` re-ingest |
| Нет label-level counts в backup manifest | Нельзя verify restore completeness | `seed_inventory.py --include-remote` → `graph_nodes`, `graph_claim` |
| Constraints/indexes после restore | Могут дублироваться | Reset endpoint вызывает `seed_schema_registry` |

**Рекомендация E7:** neo4j-admin dump/load runbook.

---

## 4. Qdrant

**Gaps:**

| Gap | Риск | Mitigation E6 |
|-----|------|---------------|
| Нет backup script | Потеря vectors при volume wipe | `POST /v1/index/reset` + re-index через ingest |
| Collection `st_evidence_v1` не в pg_dump | Vectors only in Qdrant storage | `seed_inventory.py` reports `vectors` count |
| Payload indexes | Пересоздаются `index/bootstrap` | retrieval reset bootstraps indexes |

**Восстановление без backup:** `make reset-reseed` (full gate) → corpus re-ingest.

**Рекомендация E7:** snapshot API `/collections/{name}/snapshots` runbook.

---

## 5. MinIO

**Buckets** (`infra/minio/buckets.txt`): `source-files`, `normalized-artifacts`, `exports`, `demo-archives`, `temp-files`.

**Gaps:**

| Gap | Риск | Mitigation E6 |
|-----|------|---------------|
| Нет backup script | Потеря source PDFs и export artifacts | `seed_demo.py` re-upload corpus; E5 fixtures — metadata only |
| `export_artifacts.storage_key` без object | Broken download | Full gate purges + re-ingest; E5 BML uploads on export |
| Cross-bucket refs in `document_cascade_refs` | Orphan refs после partial restore | Cascade metadata в PG fixtures E2–E4 |

**E6 purge:** full gate via `docker exec st-minio mc rm --recursive` per bucket (требует `mc` в контейнере).

**Рекомендация E7:** `mc mirror` scheduled backup per bucket + retention runbook (см. E5 retention notes).

---

## 6. Verify matrix после restore

| Check | Command |
|-------|---------|
| PG counts vs fixtures | `python scripts/seed_inventory.py --mode report` |
| Remote stores | `python scripts/seed_inventory.py --mode report --include-remote` |
| Offline fixtures baseline | `python scripts/seed_inventory.py --mode offline` |
| Full stack | `python scripts/seed_inventory.py --mode full` |

Exit code `1` если `validation.status=fail` или full gate step `error`.

---

## 7. Итог E6

| Store | Backup | Restore | Repeatable reseed |
|-------|--------|---------|-------------------|
| PostgreSQL | yes | yes | yes (`offline` gate) |
| Neo4j | partial | partial | yes (`full` gate reset API) |
| Qdrant | **no** | **no** | yes (`full` gate reset API) |
| MinIO | **no** | **no** | partial (`full` gate purge + ingest) |

**blocked_by_policy:** live model re-embedding не проверялся; vector counts после ingest — зона E6 BML offline quality.

**Dependency:** нет blockers на несмёрженные PR; E5 merged в `origin/dev`.
