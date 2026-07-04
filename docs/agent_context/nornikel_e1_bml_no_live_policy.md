# E1 Backend/ML no-live policy

Дата: 2026-07-04.

Ветка: `feat/nornikel-e1-bml-core-api-contracts`.

## Статус

E1 добавляет только offline/API foundation:

- shared DTO для interests, notifications, delete document, export job, review queue/decision, eval summary и source highlight;
- gateway OpenAPI routes для `/interests`, `/notifications`, `/documents/{document_id}`, `/review/*`, `/eval/report/summary`;
- типизированные notification responses и интересы пользователя поверх существующего notification storage.

## Live model policy

Live model calls не запускались и не требуются для этой карточки.

Проверки, которые требуют live model answer quality, Yandex live smoke, live latency p95 или generated live answer quality, имеют статус `blocked_by_policy` для E1.

`/eval/report/summary` читает только локальный offline report `eval/reports/latest.json`. Если report отсутствует, endpoint возвращает `blocked_by_data`, а не генерирует live-оценку.

## Storage dependencies

`/documents/{document_id}` и `/review/*` добавлены как контрактные skeleton routes. В текущем `origin/dev` нет завершенной storage foundation для document deletion purge и review queue decisions, поэтому endpoints возвращают `document_delete_not_implemented` или `review_storage_not_implemented` до merge соответствующей DB/workflow реализации.
