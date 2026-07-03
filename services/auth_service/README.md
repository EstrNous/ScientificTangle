# Сервис аутентификации

`auth_service` выдаёт короткоживущие JWT access-токены, управляет ротацией refresh-токенов и предоставляет зависимости FastAPI для проверки ролей. Политики доступа к документам и публичный API аудита развиваются отдельно после фиксации общих контрактов.

## Требования

- Python 3.12;
- PostgreSQL;
- RSA-ключи в формате PEM.

## Настройка

Все переменные имеют префикс `AUTH_`.

| Переменная | Назначение |
|---|---|
| `AUTH_DATABASE_URL` | Асинхронный PostgreSQL URL |
| `AUTH_JWT_PRIVATE_KEY_PATH` | Путь к закрытому RSA-ключу |
| `AUTH_JWT_PUBLIC_KEY_PATH` | Путь к открытому RSA-ключу |
| `AUTH_JWT_ISSUER` | Издатель JWT |
| `AUTH_JWT_AUDIENCE` | Получатель JWT |
| `AUTH_JWT_KEY_ID` | Идентификатор ключа в JWT и JWKS |
| `AUTH_ALLOWED_ORIGINS` | Разделённый запятыми список допустимых Origin |
| `AUTH_REFRESH_COOKIE_SECURE` | Требовать HTTPS для refresh cookie |

Для локальной разработки ключи можно передать через `AUTH_JWT_PRIVATE_KEY` и `AUTH_JWT_PUBLIC_KEY`. Секреты нельзя сохранять в репозитории.

## Запуск

```bash
python -m venv .venv
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

Для локального HTTP требуется явно установить `AUTH_REFRESH_COOKIE_SECURE=false`.

## Начальные пользователи

Команда `auth-seed-users` создаёт или обновляет пользователей из переменных окружения. Для каждой роли используются пары вида `AUTH_SEED_ADMIN_USERNAME` и `AUTH_SEED_ADMIN_PASSWORD`; электронная почта задаётся необязательной переменной `AUTH_SEED_ADMIN_EMAIL`. Аналогичные имена поддерживаются для остальных ролей.

## API

- `POST /api/auth/login`;
- `POST /api/auth/refresh`;
- `POST /api/auth/logout`;
- `GET /api/auth/me`;
- `GET /.well-known/jwks.json`;
- `GET /health`;
- `GET /ready`;
- `GET /metrics`.

Refresh-токен хранится только в cookie с атрибутами `HttpOnly` и `SameSite=Strict`. В PostgreSQL сохраняется SHA-256 хеш токена. Повторное использование ротированного токена отзывает всё семейство сессий.

## Проверка

```bash
pytest
ruff check .
mypy app
```

Интеграционный тест миграций и транзакционной ротации запускается при наличии отдельной тестовой базы:

```bash
AUTH_TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/auth_test pytest
```

Тест применяет миграции к указанной базе и откатывает их после завершения.
