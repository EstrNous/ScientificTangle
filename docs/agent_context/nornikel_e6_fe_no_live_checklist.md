# E6 Frontend: no-live demo checklist и streaming flags

Карточка: `feat/nornikel-e6-fe-e2e-hardening`.

## Production build (`VITE_USE_MOCK=false`)

| Переменная | Значение по умолчанию в prod/e2e | Назначение |
|---|---|---|
| `VITE_USE_MOCK` | `false` | Реальные API clients с `apiOptions().real`; mock catalog не используется |
| `VITE_CHAT_LIFECYCLE_SIMULATION` | не задан / `false` | Simulated lifecycle отключён; в prod mode игнорируется даже при `true` |
| `VITE_CHAT_STREAMING_UX` | не задан / `false` | Streaming draft UI выключен |
| `VITE_REVIEW_CONSOLE_ENABLED` | `false` (prod), `true` (e2e mode) | Route `/review` |
| `VITE_LIVE_NOTIFICATIONS_ENABLED` | `false` | Poll notifications в mock; в prod poll всегда активен |

Сборка no-live UI gate:

```bash
cd ui
npm ci
npm run build:e2e
npm run preview:e2e
```

Mode `e2e` задаёт production env через `ui/vite.config.js` (`VITE_USE_MOCK=false`).

## Streaming и fallback

| Режим | Поведение |
|---|---|
| `VITE_USE_MOCK=false`, `VITE_CHAT_STREAMING_UX=false` | Запрос через `sendChatMessage`; без pipeline simulation |
| `VITE_USE_MOCK=false`, `VITE_CHAT_STREAMING_UX=true`, stream доступен | `tryRunQueryEventStream` + fallback abort после session reply |
| `VITE_USE_MOCK=false`, `VITE_CHAT_STREAMING_UX=true`, stream недоступен | Non-streaming reply + optional `revealMarkdownText` для draft UX |
| `VITE_USE_MOCK=true`, `VITE_CHAT_LIFECYCLE_SIMULATION=true` | Dev-only simulated/streaming lifecycle через mock fixtures |

**Prod default:** streaming UX выключен (`VITE_CHAT_STREAMING_UX` unset). Live latency и answer quality — `blocked_by_policy`.

**Simulated lifecycle:** при `VITE_USE_MOCK=false` функция `isSimulatedLifecycleEnabled()` всегда возвращает `false`, даже если `VITE_CHAT_LIFECYCLE_SIMULATION=true`.

## E2E targets

| Команда | Когда запускать |
|---|---|
| `npm run test:e2e` | Offline Playwright с API mocks, prod build (`@offline`) |
| `RUN_UI_E2E=1 npm run test:e2e:stack` | Stack поднят, gateway health OK (`@stack`) |

Offline suite покрывает сценарии 1–10 из `prod_readiness_analysis.md` на уровне UI flows с intercepted API.

Stack suite — smoke login/profile без mocks; требует seed users (`researcher` / `researcher`).

## No-live demo checklist (scenarios 1–10)

| # | Scenario | Offline e2e | Stack e2e | Live quality |
|---|---|---|---|---|
| 1 | Interests save | `scenario 1` | partial | n/a |
| 2 | Upload stages | `scenario 2` | needs stack | n/a |
| 3 | Notification → source | `scenario 3` | needs stack | n/a |
| 4 | Source highlight / 403 | `scenario 4a/4b` | needs stack | n/a |
| 5 | Export MD/JSON | `scenario 5` | needs stack | n/a |
| 6 | Admin save | `scenario 6` | needs stack | n/a |
| 7 | Review decision | `scenario 7` | needs stack | n/a |
| 8 | Search filters | `scenario 8` | needs stack | n/a |
| 9 | Dictionary activate | `scenario 9` | needs stack | n/a |
| 10 | Audit filtering | `scenario 10` | needs stack | n/a |

## Blocked by policy

- Live model answer quality и latency p95 не проверяются в E6 Frontend.
- Yandex live smoke не входит в UI gate.

## Зависимости этапа

- E6 DB seed reliability и E6 BML offline quality merged в `dev` (PR #94, #93).
- Stack-backed `@stack` tests optional; skip без `RUN_UI_E2E=1`.
