# E7 Frontend: production polish checklist

**Дата:** 2026-07-04  
**Ветка:** `feat/nornikel-e7-fe-polish`  
**Этап:** E7 — production polish  
**Live models:** не использовались (`blocked_by_policy`)

## Реализовано

| Область | Изменения |
|---------|-----------|
| Empty/error/degraded states | `PageState.jsx` (`EmptyState`, `ErrorBanner`, `DegradedBanner`); подключено в chat, search, review, admin, audit, upload, export, strategic quality, `RoleRoute` |
| Service health | `api/health.js`, `stores/healthStore.js`, `ServiceHealthIndicator` в TopBar, `SystemDegradedBanner` в shell; poll `/health/all` в production mode |
| PWA / OG / branding | `public/manifest.webmanifest`, meta OG/Twitter в `index.html`, `alt="НорСинтез"` у логотипа |
| Demo labels | `ErrorBoundary` без user-facing mock-режима в production; dev-only hint при `VITE_USE_MOCK` + `DEV` |
| Mobile polish | responsive TopBar, `min-w-0` в chat/export/review grid, i18n empty prompt в чате |

## Smoke checklist (no-live)

- [ ] `VITE_USE_MOCK=false`: индикатор «Сервисы» в шапке, tooltip со списком peers
- [ ] При недоступном backend: amber banner «Не удалось связаться…»
- [ ] Поиск без результатов: empty state «По запросу ничего не найдено»
- [ ] Ошибка загрузки review queue: `ErrorBanner` + «Повторить»
- [ ] `manifest.webmanifest` отдаётся на `/manifest.webmanifest`
- [ ] View source OG tags в `index.html`
- [ ] Mobile (<640px): заголовок не перекрывает кнопки шапки
- [ ] Chat/export/review: нет горизонтального overflow на узком экране

## Blocked / deferred

| Item | Reason |
|------|--------|
| Live model quality smoke | `blocked_by_policy` |
| Visual regression screenshots | нет Playwright visual baseline в E7 scope |
| Full-page empty states audit | покрыты основные product flows; orphan routes вне E7 |

## Проверки

```bash
cd ui && npm test && npm run build && npm run lint
git diff --check
```
