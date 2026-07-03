# Контракты и синхронизация

Выдержка из `docs/nauchny_klubok_top1_tz.md` §23, §28.

## Shared DTO (Sync 1)

NormalizedDocument, SourceSpan, TableBlock, Claim, QueryIR, EvidenceBundle, AnswerPayload, GraphSubgraph, IngestionReport, UserRole, AccessPolicy, AuditEvent.

Расположение: `shared/contracts/`. После freeze — изменения только с явным решением команды.

## UI payload sync

AnswerPayload, SourceSpanPayload, GraphSubgraphPayload, IngestionTaskPayload, SearchResultPayload, UserRolePayload, ExportPayload — фиксация совместно frontend и backend.

## Ключевые точки синхронизации

| Sync | Содержание |
|------|------------|
| 0 | Старт: роли, MVP cutoff, структура репо |
| 1 | Контракты заморожены |
| 2 | Инфра поднята, healthchecks |
| 3 | Ingestion skeleton: файл → task_id → storage |
| 4 | NormalizedDocument + SourceSpan |
| 5 | Neo4j + Qdrant |
| 6 | Первый query end-to-end |
| 7 | MVP freeze — без крупных архитектурных изменений |
| 8+ | Top-1 features только через существующие contracts |

Полное описание sync-точек — §28 в `docs/nauchny_klubok_top1_tz.md`.
