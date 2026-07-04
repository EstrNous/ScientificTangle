# НорСинтез E0: аудит UI (Frontend)

**Дата:** 2026-07-04  
**Ветка:** `feat/nornikel-e0-fe-ui-audit`  
**Этап:** E0 — baseline и аудит  
**База:** `origin/dev` (проверка по коду, без изменений production behavior)

Связанные документы: [`nornikel_parallel_execution_plan.md`](nornikel_parallel_execution_plan.md), [`top1_e0_ui_audit.md`](top1_e0_ui_audit.md) (узкий chat-аудит Top-1), [`docs/tz/mvp.md`](../tz/mvp.md).

**E0 dependency:** блокеров от других ролей нет — карточка audit-only.  
**Live models:** не использовались; live quality gates помечены `blocked_by_policy`.

---

## 1. Цель и метод

Зафиксировать текущее состояние UI: маршруты, stores, API clients, mock/live границы, ключевые экраны и отсутствующие компоненты. Mock layer **не удалялся**.

Проверено: `ui/src/app/routes.jsx`, `ui/src/pages/`, `ui/src/components/`, `ui/src/api/`, `ui/src/stores/`, `ui/src/hooks/`, `ui/src/context/`, `ui/src/utils/`.

---

## 2. Маршруты (`ui/src/app/routes.jsx`)

| Path | Page | RoleRoute key | Статус |
|------|------|---------------|--------|
| `/login`, `/register`, `/forgot-password` | Auth pages | — | live auth API |
| `/` | redirect → `/chat` | — | — |
| `/chat` | `ChatPage.jsx` | `chat` | production chat sessions |
| `/graph` | `GraphPage.jsx` | `graph` | live graph API |
| `/strategic/coverage` | `StrategicCoveragePage.jsx` | `strategic` | live strategic API |
| `/strategic/quality` | `StrategicQualityPage.jsx` | `strategic` | live + `EvaluationDashboard` |
| `/lab/matrix` | `LabMatrixPage.jsx` | `lab` | live lab API |
| `/lab/insights` | `LabInsightsPage.jsx` | `lab` | gaps + conflicts |
| `/admin` | `AdminPage.jsx` | `admin` | users + access policies |
| `/admin/stats` | `AdminStatsPage.jsx` | `admin` | ops metrics |
| `/admin/audit` | `AdminAuditPage.jsx` | `admin` | audit + source viewer |
| `/upload` | `UploadPage.jsx` | `upload` | live upload/delete |
| `/search` | `SearchPage.jsx` | `lab`, `search` | live search API |
| `/profile` | `ProfilePage.jsx` | `profile` | auth + local interests |
| `*` | redirect → `/chat` | — | — |

### Отсутствующие маршруты (gaps)

| Компонент / route | Этап | Примечание |
|-------------------|------|------------|
| `/review` → `ReviewConsolePage` | E2 | нет page, route, feature flag |
| Dictionary version manager (admin tab) | E4 | upload dictionary есть; activate/list versions — нет |
| Ingestion queue page | E4/E6 | `IngestionDashboard.jsx` есть, **не подключён** ни к одному route |
| Dedicated notification center page | E5 | только dropdown в `NotificationBell` |
| Dedicated eval report dashboard route | E5/E6 | eval только как виджет на `/strategic/quality` |

---

## 3. Stores (`ui/src/stores/`)

| Store | Файл | Назначение | Gaps |
|-------|------|------------|------|
| `authStore` | `authStore.js` | `role`, `user`, `token`, `canAccess`, `ROLE_PAGES` | client-side RBAC; `setRole` не синхронизирован с backend |
| `notificationStore` | `notificationStore.js` | items, unreadCount, mark read | нет poll/`since`, нет navigation по `reference_id` |
| `chatAnswerStore` | `chatAnswerStore.js` | phase, retrievalTrace, streaming draft | есть lifecycle store (отличие от старого top1 аудита) |
| `themeStore` | `themeStore.js` | dark mode | — |
| `localeStore` | `localeStore.js` | i18n | — |

Отсутствуют: interests store (E1), export job store (E5), review queue store (E2), audit cursor store (E5).

---

## 4. API layer и mock/live границы

### Переключатель mock

| Механизм | Файл | Поведение |
|----------|------|-----------|
| `VITE_USE_MOCK !== 'false'` | `api/client.js` | mock по умолчанию |
| `{ real: true }` | большинство domain API | обход mock для конкретного вызова |
| `export { useMock }` | `api/client.js` | runtime ветвление |
| `isLiveProductionMode()` | `utils/uiFeatureFlags.js` | `!useMock` |
| `isDevRoleSwitcherEnabled()` | `utils/uiFeatureFlags.js` | `useMock \|\| import.meta.env.DEV` |

### API-модули

| Модуль | Endpoints / функции | Mock | Real flag | Этап gap |
|--------|---------------------|------|-----------|----------|
| `client.js` | generic GET/POST/DELETE, `submitChatQuery` | yes | per-call | E1 interests/export/review clients |
| `chat.js` | `/chat/sessions/*` | no | always real | — |
| `auth.js` | `/api/auth/*` | partial (credentials) | live JWT | E4 server RBAC |
| `source.js` | `GET /source/{id}` | no | always real | E2 highlight offsets; E4 403 UI |
| `sourceResolver/` | adapter mock/live | via `useMock` | index | E2/E4 доработка live adapter |
| `notifications.js` | list, mark read | mock seed | `real` | E3 poll; E5 product events |
| `upload.js` | upload, delete, task poll | no | direct fetch | E4 stages UI |
| `graph.js` | graph, search catalog | throws in mock | `real` | — |
| `strategic.js` | metrics, evaluation | throws in mock | `real` | E5 backend eval report |
| `lab.js` | coverage | throws in mock | `real` | — |
| `queryTransport.js` | SSE/stream query | live path | — | E4/E6 streaming policy |

### Mock seeds (`ui/src/api/mock/`)

| Файл | Назначение |
|------|------------|
| `index.js` | `mockFetch` router: admin, audit, notifications, ingestion/tasks, query |
| `chatQuery.js` | retrieval steps, mock assistant reply |
| `sourceCatalog.js` | mock source pages, highlight text |
| `sourceBindings.js` | evidence row → span mapping |
| `admin.json`, `audit.json`, `notifications.json`, `ingestion.json` | static seeds |
| `scientificAnswerFixtures.js` | test fixtures |

`mockFetch` **бросает** для chat/graph/search/strategic/lab — эти зоны требуют backend даже в mock mode UI.

---

## 5. Прямые импорты `api/mock/` — inventory

### Production / runtime path (не тесты)

| Файл | Импорт | Классификация | Этап выноса |
|------|--------|---------------|-------------|
| `api/client.js` | `./mock/index.js` | **допустимо** — mock boundary entry | E4 grep gate |
| `api/sourceResolver/mockAdapter.js` | `../mock/sourceCatalog.js`, `../mock/sourceBindings.js` | **допустимо** — adapter behind resolver | E4 |
| `api/sourceResolver/index.js` | `./mockAdapter.js` | **допустимо** — adapter switch | E4 |
| `utils/runSimulatedAnswerLifecycle.js` | `../api/mock/chatQuery.js` | **dev/mock lifecycle** | E6 disable in prod |
| `utils/runStreamingAnswerLifecycle.js` | `../api/mock/chatQuery.js` | **dev/mock lifecycle** | E6 disable in prod |

### Только тесты (допустимо)

| Файл | Импорт |
|------|--------|
| `components/chat/AnswerRenderer.test.jsx` | `api/mock/scientificAnswerFixtures.js` |
| `api/client.test.js` | vi.mock `api/mock/index.js` |
| `api/sourceResolver/sourceResolver.test.js` | `mockAdapter.js` |

### Production components — прямых `api/mock/` импортов **нет**

Компоненты используют `api/sourceResolver/index.js` или `useSourceResolver`:

| Файл | Resolver API |
|------|--------------|
| `context/SourceDocumentContext.jsx` | `fetchSourceDocument`, `mergeSourceSpan` |
| `components/shared/SourceDocumentPanel.jsx` | `getDocumentViewPages` |
| `components/chat/EvidenceTable.jsx` | `getEvidenceRowSources` |
| `components/graph/GraphCombinationsTable.jsx` | `getCombinationRowSources`, `resolveSourceRef` |
| `utils/downloadSource.js` | `getFullDocumentPages` |
| `hooks/useSourceResolver.js` | hook facade |
| `hooks/useSourceRefRenderer.js` | via hook |
| `components/shared/SourceLink.jsx` | via `useSourceRefRenderer` |

**Вывод E0:** по сравнению с top1 аудитом mock catalog **централизован** через `sourceResolver`; grep rule E4 — не импортировать `api/mock/` из `components/` и `pages/` (сейчас соблюдается).

---

## 6. Ключевые UI-компоненты

### RoleSwitcher (`components/shared/RoleSwitcher.jsx`)

- Рендер: `layout/TopBar.jsx` только если `isDevRoleSwitcherEnabled()` (`useMock || DEV`).
- Store: `authStore.setRole` перезаписывает backend role.
- **Gap FE-01:** production RBAC должен идти от session claims (E4/E5).

### Source resolver

- `useSourceResolver` + `SourceDocumentContext.openSource` → `fetchSourceDocument` (live) или mock adapter.
- `SourceDocumentPanel` + `HighlightedText`: highlight по **substring**, scroll к cited page.
- **Gap FE-02:** нет `highlight_start`/`highlight_end` offset scroll (E2).
- **Gap FE-03:** нет locked/403 state в modal — `openSource` молча `catch` (E2/E4).
- **Gap FE-04:** нет table row/cell rendering по `table_row_id` (E2).

### NotificationBell (`components/shared/NotificationBell.jsx`)

- One-shot `fetchNotifications()` при mount; mark read/all read → API + store.
- **Gap FE-05:** нет incremental poll `?since=` (E3/E5).
- **Gap FE-06:** click не открывает document/source по `reference_id`/`reference_type` (E3).
- **Gap FE-07:** titles не i18n по `type` (E3).

### ExportPanel (`components/chat/ExportPanel.jsx`)

- Client-side only: `utils/reportExport.js` (md/json/pdf из messages).
- **Gap FE-08:** нет `POST /api/export`, job poll, JSON-LD (E5).
- **Gap FE-09:** нет feature flag server vs client export (E1/E5).

### AdminPage (`pages/AdminPage.jsx`)

- Load: `GET /admin` с `{ real: true }`.
- Edits: local state only — **нет PATCH/save API** (E3).
- Нет dictionaries tab / version manager (E4).

### ProfilePage (`pages/ProfilePage.jsx`)

- Interests: `utils/interestsStorage.js` (localStorage) + `extractInterests` client-side.
- **Gap FE-10:** нет `GET/PUT /api/interests` (E1 client, E3 flow).

### EvaluationDashboard (`components/strategic/EvaluationDashboard.jsx`)

- Data: `StrategicQualityPage` → `fetchStrategicEvaluation()` → `GET /strategic/evaluation`.
- **Gap FE-11:** не читает pinned offline eval report / backend eval summary contract (E5/E6).
- Нет отдельной eval report dashboard page (E5).

### UploadPage + `UploadAnalysisPanel`

- Live upload, task poll via raw `fetch`, `deleteDocument` API.
- Показывает `task.status`, `task.report` metrics — **не** `task.stages[]` stepper (E4).
- Dictionary upload через dropzone — нет admin activate UI (E4).

### SearchPage

- Простой question + limit; live `GET /search`.
- **Gap FE-12:** нет geo/year/numeric filters, pagination (E4).

### GraphPage + Lab

| Компонент | Файл | Статус |
|-----------|------|--------|
| `VerificationInbox` | `components/graph/VerificationInbox.jsx` | approve/reject buttons **без handlers** |
| `IngestionDashboard` | `components/graph/IngestionDashboard.jsx` | **orphan**, не в GraphPage |
| `GapAnalysisView` | `components/lab/GapAnalysisView.jsx` | read-only, no source links on gaps |
| `GapConflictView` | `components/lab/GapConflictView.jsx` | `SourceLink` на conflicts; no review actions |

### Chat UX (`ChatPage` + `useChatAnswerFlow`)

- Sessions: `api/chat.js` (always real).
- Answer flow: `chatAnswerStore`, simulated/streaming lifecycle utils, optional `queryTransport` stream.
- `RetrievalProgress` подключён через `useChatAnswerFlow` / `ChatWindow` (улучшение vs top1 аудит).
- **Gap FE-13:** gaps/conflicts/reason codes в `AnswerRenderer` ограничены (E3).
- **Gap FE-14:** streaming UX за флагом `VITE_CHAT_STREAMING_UX` (E4/E6).

### Audit (`AdminAuditPage`, `AuditLogTable`)

- Load all events once; client-side action filter.
- **Gap FE-15:** нет cursor pagination, CSV export, drill-down run (E5).

---

## 7. Отсутствующие pages/components (явный список E0)

| ID | Компонент | Этап владельца |
|----|-----------|----------------|
| M-01 | `ReviewConsolePage`, route `/review` | E2 |
| M-02 | `CandidateTable`, `ConflictDiffView`, `ReviewActionBar` | E2 |
| M-03 | Dictionary version manager (list, active badge, activate) | E4 |
| M-04 | Ingestion queue UI (wire `IngestionDashboard` or replacement) | E4/E6 |
| M-05 | Eval report dashboard (offline/backend report reader) | E5/E6 |
| M-06 | Source locked state panel (403 `access_denied`) | E2/E4 |
| M-07 | Offset/table-row highlight in source viewer | E2 |
| M-08 | API clients: interests, export, review, admin PATCH | E1 |
| M-09 | Notification center page / poll UX | E5 |
| M-10 | Audit pagination + CSV | E5 |

---

## 8. Frontend gaps по этапам E1–E7

### E1 — API foundation

- API clients/helpers: interests, notifications (since), review, export, admin PATCH, delete document (upload.js есть).
- Common async states: loading, optimistic update, rollback, toast/error — частично на upload delete only.
- Feature flags: `server export`, `live notifications`, `review console`, `source live mode` — нет централизованного модуля (есть `uiFeatureFlags.js`, `chatFeatureFlags.js`).

### E2 — Review and source UI

- `ReviewConsolePage` + route behind flag.
- Source viewer: offset highlight, 403 locked, table row rendering.
- Mock fixtures для review states.

### E3 — User workflows

- Profile interests → API; NotificationBell poll + navigation; admin save persistence; review decisions with rollback.
- Upload delete error messages 403/404 — базовый catch есть, специфичные сообщения слабые.

### E4 — Evidence and access

- Убрать прямые mock imports из production (сейчас OK); довести live source adapter.
- RoleSwitcher только dev+mock (частично есть).
- Search filters; dictionary admin tab; upload stepper from `task.stages[]`.
- Gap/conflict row → sources + review defer (если API ready).

### E5 — Export, notifications, audit

- ExportPanel → `POST /api/export`; JSON-LD unavailable state.
- Notification product UX; audit filters/pagination/CSV.
- EvaluationDashboard → backend/pinned offline report.

### E6 — E2E hardening

- Playwright/Cypress scenarios 1–10; `VITE_USE_MOCK=false` build smoke.
- Disable simulated lifecycle when real backend mode.
- Document streaming fallback.

### E7 — Polish

- Empty/error/degraded states; health indicator; PWA/OG; mobile layout; remove demo labels in prod.

---

## 9. Сводная таблица gaps (owner: Frontend)

| ID | Gap | Severity | Файлы-touch | Этап |
|----|-----|----------|-------------|------|
| FE-01 | Client RBAC vs backend role | high | `authStore.js`, `RoleSwitcher.jsx`, `RoleRoute.jsx` | E4/E5 |
| FE-02 | No offset highlight | high | `SourceDocumentPanel.jsx`, `liveAdapter.js`, `mapSourcePayload` | E2 |
| FE-03 | No 403 locked source UI | high | `SourceDocumentContext.jsx`, modal | E2/E4 |
| FE-04 | No table row source render | medium | `SourceDocumentPanel.jsx` | E2 |
| FE-05 | Notifications no poll/since | medium | `NotificationBell.jsx`, `notifications.js` | E3/E5 |
| FE-06 | Notification click no navigation | medium | `NotificationBell.jsx` | E3 |
| FE-07 | Notification i18n by type | low | `NotificationBell.jsx`, i18n | E3 |
| FE-08 | Export client-only | high | `ExportPanel.jsx` | E5 |
| FE-09 | No export feature flags | medium | new flags module | E1/E5 |
| FE-10 | Interests localStorage only | high | `ProfilePage.jsx`, `interestsStorage.js` | E1/E3 |
| FE-11 | Eval dashboard not offline-report aware | medium | `EvaluationDashboard.jsx`, `strategic.js` | E5/E6 |
| FE-12 | Search filters missing | medium | `SearchPage.jsx` | E4 |
| FE-13 | Answer gaps/conflicts/reason codes | medium | `AnswerRenderer.jsx`, `WarningsPanel.jsx` | E3 |
| FE-14 | Streaming behind env flag | low | `chatFeatureFlags.js`, `useChatAnswerFlow.js` | E4/E6 |
| FE-15 | Audit no pagination/CSV | medium | `AdminAuditPage.jsx`, `AuditLogTable.jsx` | E5 |
| FE-16 | Admin save local-only | high | `AdminPage.jsx` | E3 |
| FE-17 | Review console missing | high | new page | E2 |
| FE-18 | IngestionDashboard orphan | low | `IngestionDashboard.jsx`, routes | E4 |
| FE-19 | VerificationInbox actions stub | medium | `VerificationInbox.jsx` | E2/E3 |
| FE-20 | Dictionary version UI missing | medium | admin components | E4 |
| FE-21 | Upload no stages stepper | medium | `UploadAnalysisPanel.jsx` | E4 |
| FE-22 | Simulated lifecycle uses mock in utils | info | `runSimulatedAnswerLifecycle.js` | E6 |

---

## 10. Mock/live freeze (E0–E4)

- **Не удалять** `ui/src/api/mock/` и `VITE_USE_MOCK` до E4/E5 merge gate.
- `sourceResolver/mockAdapter.js` — единственная точка mock catalog для components.
- `runSimulatedAnswerLifecycle` / `runStreamingAnswerLifecycle` — mock chatQuery только для dev/simulation path.
- `chat.js` always real — контракт с gateway sessions.

---

## 11. Проверки (E0 card)

| Проверка | Результат |
|----------|-----------|
| `git diff --check` | после коммита отчёта |
| UI unit tests | `cd ui && npm test` |
| UI build | `cd ui && npm run build` |
| Live model calls | **не выполнялись** (`blocked_by_policy`) |

---

## 12. Итог E0

- Маршруты покрывают MVP pages кроме **Review Console** и dedicated ingestion/eval routes.
- Mock layer **сохранён**; production components **не импортируют** `api/mock/` напрямую — abstraction через `sourceResolver`.
- Крупнейшие product gaps: **interests API**, **admin save**, **server export**, **notification navigation/poll**, **review console**, **source 403/offset highlight**, **audit pagination**.
- Распределение работ по этапам E1–E7 зафиксировано в §8–§9 для Validator unified gaps table.
