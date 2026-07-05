# Домен: model

Порт 8006. Evidence-first ML-слой.

## Ключевые файлы

- `services/model/app/api/v1.py` — v1 endpoints
- `services/model/app/contracts.py` — confirmed/candidate layer, reason codes
- `services/model/app/services.py` — операции с Yandex provider и fallback
- `services/model/app/yandex_client.py` — Yandex AI Studio
- `services/model/app/prompt_registry.py`, `app/prompts/` — prompt templates
- `services/model/app/schema_registry.py` — JSON Schema registry
- `services/model/tests/test_model_v1.py`

## Ограничения

Confirmed outputs требуют `SourceSpan`. Candidates — с reason codes.

## Импорты

В `services/model/app/` — relative imports (`from .`, `from ..`); `shared.*` — абсолютный. В тестах — `from app.*` через PYTHONPATH.

## Статус

`docs/agent_context/ml_mvp_status.md` — закрыто, gaps, top-1 backlog, VL/OCR позиция.
