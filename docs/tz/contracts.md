# Контракты и синхронизация

Выдержка из `docs/nauchny_klubok_top1_tz.md` §23, §28.

## Shared DTO (Sync 1)

NormalizedDocument, SourceSpan, TableBlock, Claim, QueryIR, EvidenceBundle, AnswerPayload, GraphSubgraph, IngestionReport, UserRole, AccessPolicy, AuditEvent.

Расположение: `shared/contracts/`. После freeze — изменения только с явным решением команды.

## UI payload sync

AnswerPayload, SourceSpanPayload, GraphSubgraphPayload, IngestionTaskPayload, SearchResultPayload, UserRolePayload, ExportPayload — фиксация совместно frontend и backend.

## Ключевые точки синхронизации

| Sync | Содержание | Статус (2026-07-04) |
|------|------------|---------------------|
| 0 | Старт: роли, MVP cutoff, структура репо | ✅ |
| 1 | Контракты заморожены | ✅ 53 Pydantic-класса в `shared/contracts` |
| 2 | Инфра поднята, healthchecks | ✅ compose + CI |
| 3 | Ingestion skeleton: файл → task_id → storage | ✅ MinIO |
| 4 | NormalizedDocument + SourceSpan | ✅ ingestion parsers |
| 5 | Neo4j + Qdrant | ✅ live adapters |
| 6 | Первый query end-to-end | ✅ orchestrator pipeline |
| 7 | MVP freeze — без крупных архитектурных изменений | ⚠️ hybrid retrieval gaps |
| 8+ | Top-1 features только через существующие contracts | в работе |

Полное описание sync-точек — §28 в `docs/nauchny_klubok_top1_tz.md`.
