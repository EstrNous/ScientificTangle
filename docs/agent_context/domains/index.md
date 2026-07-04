# Доменные контексты

Краткие указатели по сервисам. Полная карта — `docs/agent_context/project_structure.md`.

| Сервис | Файл | Зрелость (2026-07-04) |
|--------|------|------------------------|
| gateway | `gateway.md` | 4 — полный BFF, chat_db |
| auth_audit | `auth_audit.md` | 5 — JWT, RBAC, audit |
| orchestrator | `orchestrator.md` | 4 — ingestion + query + export |
| ingestion | `ingestion.md` | 4 — parsers, MinIO |
| knowledge | `knowledge.md` | 4 — Neo4j live |
| retrieval | `retrieval.md` | 4 — Qdrant live; hybrid gaps |
| model | `model.md` | 5 — 13 v1 endpoints |
| export | `export.md` | 2 — stub HTTP |
| notification | `notification.md` | 5 — wired HTTP, runtime delivery, Redis worker |

**Сводка vs ТЗ:** [`implementation_quality_report.md`](../implementation_quality_report.md)  
**ML статус:** [`ml_mvp_status.md`](../ml_mvp_status.md)  
**Аудит gaps:** [`audit_report.md`](../audit_report.md)

При значимых изменениях сервиса обнови соответствующий domain-файл в том же коммите.
