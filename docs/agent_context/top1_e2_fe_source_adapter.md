# Top-1 E2: source adapter (Frontend)

**Дата:** 2026-07-04  
**Ветка:** `feat/top1-e2-fe-source-adapter`  
**Этап:** E2 — data и retrieval base  
**Область:** `ui/src/api/sourceResolver/`, hooks, chat/shared source touchpoints

Связанные документы: [`top1_e0_ui_audit.md`](top1_e0_ui_audit.md), [`top1_parallel_execution_plan.md`](top1_parallel_execution_plan.md).

---

## 1. Цель

Централизовать mock/live границу источников через `SourceResolver` без удаления mock layer. Подготовить renderer hooks для переключения на live refs в E5.

---

## 2. Реализация

### Фасад `ui/src/api/sourceResolver/`

| Модуль | Назначение |
|--------|------------|
| `index.js` | выбор adapter по `VITE_USE_MOCK`, публичный API |
| `mockAdapter.js` | делегирует в `api/mock/sourceCatalog.js` и `sourceBindings.js` |
| `liveAdapter.js` | `fetchSource` + `mapSourcePayload`, минимальные bindings из payload |

### Публичный API

- `getSourceMode()` → `'mock' | 'live'`
- `resolveSourceRef`, `mergeSourceSpan`, `sourceRefLabel`
- `getEvidenceRowSources`, `getCombinationRowSources`, `getMatrixCellSources`
- `fetchSourceDocument` — единая точка открытия документа
- `getDocumentViewPages`, `getFullDocumentPages`

### Hooks

| Hook | Назначение |
|------|------------|
| `useSourceResolver` | доступ к resolver API в компонентах |
| `useSourceRefRenderer` | label, `openRef`, `isInteractive` для citation links |

### Обновлённые touchpoints (E2)

| Файл | Было | Стало |
|------|------|-------|
| `context/SourceDocumentContext.jsx` | прямой mock + `fetchSource` | `fetchSourceDocument` через resolver |
| `components/shared/SourceLink.jsx` | `resolveSourceRef` из mock | `useSourceRefRenderer` |
| `components/shared/SourceRefsPopover.jsx` | `sourceRefLabel` из mock | resolver |
| `components/chat/EvidenceTable.jsx` | `getEvidenceRowSources` из mock | resolver |

---

## 3. Оставшиеся mock dependencies (E5)

Прямые импорты `api/mock/*` — намеренно не тронуты до live backend readiness:

| Файл | Импорт | Этап выноса |
|------|--------|-------------|
| `components/graph/GraphCombinationsTable.jsx` | `getCombinationRowSources`, `resolveSourceRef` | E5 |
| `components/shared/SourceDocumentPanel.jsx` | `getDocumentViewPages` | E5 |
| `utils/downloadSource.js` | `getFullDocumentPages` | E5 |

Mock catalog и bindings остаются в `api/mock/` — freeze point E0–E4.

---

## 4. Переключение mock → live (E5)

1. Заменить оставшиеся прямые mock imports на `sourceResolver`.
2. Расширить `liveAdapter` bindings API, когда backend отдаёт row/column → span mapping.
3. `SourceDocumentPanel` / `downloadSource` — live page text через `GET /source/{id}`.
4. `VITE_USE_MOCK=false` — production path без удаления dev mock bundle.

---

## 5. Зависимости

| Зависимость | Статус |
|-------------|--------|
| E1 `fe-chat-state` merged в `dev` | ✅ PR #49 |
| Backend source bindings API | E5 blocker для graph/matrix live bindings |
| Stable `GET /source/{id}` | частично готов (`api/source.js`), E5 для full pages |

---

## 6. Проверки

- `ui`: `npm test` — `sourceResolver.test.js` + существующие тесты
- `ui`: `npm run build`
- `ui`: `npm run lint`
