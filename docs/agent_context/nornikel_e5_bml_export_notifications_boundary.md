# E5 Backend/ML: export, notifications, audit

## Граница экспорта

На E5 authoritative boundary остаётся в orchestrator: `POST /export` создаёт `ExportJob` в `orchestrator_db`, резолвит доступные источники через retrieval/source resolver и возвращает inline Markdown или JSON. Отдельный `services/export` остаётся backlog до решения команды о MinIO artifact storage и HTTP API сервиса.

Поддерживаемые форматы сейчас:

- `markdown`: доступен, `text/markdown`;
- `json`: доступен, `application/json`;
- `jsonld`: явно помечен как backlog, потому что model JSON-LD enrichment готов, но export wiring не подключён;
- `pdf`: явно помечен как backlog, потому что server-side PDF renderer не подключён.

Экспорт включает `QueryIR`, `retrieval_trace`, evidence table, source links, graph, gaps/conflicts, confidence, warnings, роль пользователя, access scope и audit event `document_exported`. Перед выдачей выполняется повторный source resolve с ролью пользователя; если доступ изменился, export job переводится в failed и пишется `access_denied`.

## Уведомления

На E5 production notification list не должен зависеть только от seed. Реальный backend event source в этой карточке закрыт для query conflict flow: chat/query response с conflicts создаёт `conflict_detected` notification с `reference_type=query_run`, `match_score`, `match_reason` и match payload. `GET /notifications?since=` отдаёт эти поля из storage.

Ingestion/review notifications требуют отдельного межсервисного event delivery из orchestrator в notification storage или notification service. В текущей карточке это не расширялось, чтобы не брать storage/service-boundary работу других ролей.

## Audit

Покрытые product audit events:

- `query_created`;
- `answer_generated`;
- `document_exported`;
- `access_denied`;
- `document_uploaded`;
- `document_deleted`;
- `review_decision`;
- `admin_setting_changed`;
- `source_viewed`;
- `search`;
- `filtered_sources`.

Live model calls и live quality checks не выполнялись.
