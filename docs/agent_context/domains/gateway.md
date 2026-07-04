# Домен: gateway

Порт 8000. API Gateway / BFF.

## Ключевые файлы

- `services/gateway/app/api/query.py` — query, runs, export, source, subgraph, search
- `services/gateway/app/api/chat.py` — chat sessions и messages
- `services/gateway/app/api/graph.py` — graph catalog
- `services/gateway/app/api/documents.py` — upload, task status
- `services/gateway/app/api/admin.py` — admin stats, audit events, strategic/lab
- `services/gateway/app/service/chat_service.py` — chat → orchestrator query
- `services/gateway/app/service/analytics_service.py` — graph/strategic/lab через knowledge/retrieval
- `infra/postgres/chat_ui_db/` — ChatSession, ChatMessage

## Внешние API (root `/api`)

| Группа | Endpoints |
|--------|-----------|
| Documents | upload, task status |
| Query | run, runs, export, source, subgraph, search |
| Chat | sessions CRUD, messages |
| Graph | graph, catalog |
| Admin | stats, audit, strategic metrics/evaluation, lab coverage, users/policies |

JWT validation через JWKS (`auth_audit`). `X-Request-ID` сквозной.

## Зависимости

orchestrator (основной proxy), auth_audit (JWKS), PostgreSQL chat_ui_db, knowledge/retrieval (analytics).

## Gaps

- Admin user/policy PATCH без полного persist
- Strategic/lab данные частично из knowledge + eval fixtures
