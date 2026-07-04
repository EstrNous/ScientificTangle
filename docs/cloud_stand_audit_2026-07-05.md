# Отчёт по стенду `51.250.103.29`

Дата: 2026-07-05  
Стенд: `http://51.250.103.29/`  
Режим деплоя: `docker-compose.yml + docker-compose.prod.yml + docker-compose.cloud.yml + docker-compose.cloud.http.yml`

## Краткий вывод

Сейчас проблема не в том, что UI "не видит" уже загруженный полный датасет. По проверкам Postgres и MinIO в рабочем контуре приложения полного датасета нет.

Фактическое состояние:

- `ingestion_tasks`: есть 1 completed task.
- Эта task содержит только загрузку словаря, не документов.
- `indexed_documents`: `0`.
- `source_span_lookup`: `0`.
- `indexed_points`: `0`.
- MinIO bucket `source-files`: только `dictionary-package.zip`, документов корпуса нет.
- Qdrant/retrieval не содержит evidence для поиска.

Итог: чат, поиск, граф evidence, экспорт с источниками и source viewer не могут работать с датасетом, потому что документальный корпус не прошёл pipeline `upload -> normalize -> knowledge -> retrieval`.

## Что сейчас стягивать

Для диагностики данных ничего из Git стягивать не нужно. `git pull` чинит только код, но не создаёт документы в MinIO, source spans в Postgres и vectors в Qdrant.

Стягивать из Git нужно только в двух случаях:

1. Команда уже исправила код на `dev`, и нужно обновить приложение.
2. Нужно получить новый скрипт/фикс для batch-загрузки полного датасета.

Если цель прямо сейчас - восстановить данные, нужен не `git pull`, а найти или заново загрузить полный датасет в ingestion pipeline.

## Как безопасно обновлять код с `dev`

Если надо именно подтянуть свежий код:

```bash
cd ~/ScientificTangle
git fetch origin
git switch dev
git pull --ff-only origin dev

sudo bash scripts/cloud_deploy.sh 51.250.103.29 \
  --no-demo \
  --yandex-api-key "NEW_KEY" \
  --yandex-folder-id "b1ggusvist6c2sia1dno" \
  --install-docker
```

Важно:

- `--no-demo` нужен, потому что demo seed сейчас падает на больших загрузках и не нужен, если грузится свой полный датасет.
- Не делать `down -v`, если есть шанс, что в volumes лежат нужные данные.
- Yandex API key, который был отправлен в чат, нужно перевыпустить.

## Почему команда с Qdrant зависла

Команда:

```bash
"${COMPOSE[@]}" exec -T retrieval python - <<'PY'
...
PY
```

перешла в prompt `>`, потому что shell не увидел закрывающий heredoc-маркер `PY`. Обычно причина: перед `PY` есть пробелы, табы или вставка сломала перевод строки. Закрывающий `PY` должен стоять строго с первого символа строки.

Надёжная однострочная замена:

```bash
"${COMPOSE[@]}" exec -T retrieval python -c 'import httpx; 
urls=["http://qdrant:6333/collections","http://qdrant:6333/collections/st_evidence_v1"];
for u in urls:
 r=httpx.get(u,timeout=10); print(u,r.status_code); print(r.text[:2000])'
```

Если shell не любит переносы, совсем коротко:

```bash
"${COMPOSE[@]}" exec -T retrieval python -c 'import httpx; r=httpx.get("http://qdrant:6333/collections/st_evidence_v1",timeout=10); print(r.status_code); print(r.text[:4000])'
```

## Подтверждённые факты со стенда

### Контейнеры живые

`docker compose ps` показывает все основные сервисы `healthy` или `up`:

- `st-gateway`
- `st-orchestrator`
- `st-ingestion`
- `st-knowledge`
- `st-retrieval`
- `st-model`
- `st-export`
- `st-postgres`
- `st-qdrant`
- `st-minio`
- `st-neo4j`

Это означает: проблема не в том, что стек не поднялся.

### В БД нет документов

Проверка:

```sql
select status, count(*) from ingestion_tasks group by status;
select id,status,error_message,created_at,updated_at,
       report->>'documents_count' docs,
       report->>'source_spans_count' spans,
       report->>'indexed_points_count' points
from ingestion_tasks order by created_at desc limit 20;
select count(*) indexed_documents, coalesce(sum(indexed_points_count),0) indexed_points from indexed_documents;
select count(*) source_spans from source_span_lookup;
```

Факт:

```text
ingestion_tasks: completed = 1
latest task: docs = NULL, spans = NULL, points = NULL
indexed_documents = 0
indexed_points = 0
source_spans = 0
```

Интерпретация:

- Эта completed task не является document ingestion task с корпусом.
- Это похоже на dictionary ingestion task.
- Документальный pipeline ни разу не дошёл до состояния, где создаются `source_spans` и Qdrant points.

### В MinIO нет корпуса

Проверка:

```bash
"${COMPOSE[@]}" exec -T minio sh -lc 'mc alias set local http://localhost:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" && mc ls --recursive local/source-files | tail -100'
```

Факт:

```text
uploads/.../dictionary-package.zip
```

Больше файлов корпуса в `source-files` не видно.

Интерпретация:

- В рабочем bucket raw upload лежит только словарь.
- Полный датасет может существовать где-то на файловой системе VM, но не в storage приложения.
- Если он есть просто в папке на сервере, приложение само его не увидит. Его нужно отправить через `/api/documents/upload` или отдельный ingestion script.

## Архитектура данных

Полный путь документа:

```text
файл пользователя
  -> gateway /api/documents/upload
  -> orchestrator /ingestion/tasks
  -> ingestion сохраняет raw source в MinIO source-files
  -> ingestion normalize создаёт normalized documents
  -> knowledge пишет entities/claims/source spans в Neo4j
  -> retrieval пишет source payloads/vectors в Qdrant st_evidence_v1
  -> orchestrator пишет report и audit в Postgres
```

Для нормальной работы нужны все слои:

- MinIO: raw files.
- Postgres: ingestion reports, query runs, source span lookup/indexed docs.
- Neo4j: knowledge graph.
- Qdrant: searchable evidence/source payloads.

Если файл есть только на диске или только в MinIO, чат не сможет его цитировать.

## Почему файлы "не видно"

В UI нет глобального каталога всех файлов на сервере. Upload page показывает только:

- текущую выбранную очередь файлов;
- последнюю ingestion task;
- report конкретной task.

Admin endpoint сейчас тоже не отдаёт реальный список source spans или policies: он возвращает `access_policies: []` и `source_spans: {}`. Поэтому отсутствие файла в UI не является самостоятельным доказательством. Но твои SQL и MinIO-проверки уже доказывают сильнее: документов корпуса в рабочем контуре нет.

## Как найти датасет на VM

Проверить, лежит ли полный датасет просто файлами где-то на сервере:

```bash
find ~/ScientificTangle ~ -type f \
  \( -iname '*.pdf' -o -iname '*.docx' -o -iname '*.xlsx' -o -iname '*.csv' -o -iname '*.txt' -o -iname '*.md' \) \
  -printf '%s %p\n' 2>/dev/null | sort -nr | head -200
```

Если датасет лежит в отдельной папке, например `~/dataset`, проверить размер:

```bash
du -sh ~/dataset
find ~/dataset -type f | wc -l
find ~/dataset -type f -printf '%s %p\n' | sort -nr | head -20
```

Если там пусто, датасет нужно заново передать на VM, например через `rsync`:

```bash
rsync -avP /local/path/to/dataset/ darkmode@51.250.103.29:~/dataset/
```

## Как загрузить полный датасет правильно

Нельзя отправлять весь большой корпус одним multipart request. Сейчас лимит 100 MB на общий upload, а `seed_demo.py` отправляет все файлы одним запросом. Поэтому он и получил `413 Request Entity Too Large`.

Правильный подход: batch upload.

Базовая стратегия:

- одна пачка меньше 80-90 MB;
- лучше 5-20 файлов за запрос, в зависимости от размера;
- после каждой пачки ждать `task.status = completed`;
- если task failed, читать `error_message` и не продолжать вслепую;
- после каждой пачки проверять прирост `indexed_documents`, `source_spans`, `indexed_points`.

Минимальный ручной batch через UI:

1. Открыть Upload.
2. Выбрать не весь датасет, а маленькую пачку.
3. Дождаться завершения.
4. Проверить SQL counts.
5. Повторить.

Для большого датасета лучше нужен отдельный script, который:

- логинится в `/api/auth/login`;
- собирает файлы из папки;
- группирует их по суммарному размеру;
- отправляет в `/api/documents/upload`;
- poll-ит `/api/tasks/{task_id}`;
- пишет отчёт по каждой пачке.

## Проверка после загрузки

После настоящей загрузки корпуса эти значения должны стать больше нуля:

```bash
"${COMPOSE[@]}" exec -T postgres psql -U st_user -d scientific_tangle -c "
select count(*) indexed_documents, coalesce(sum(indexed_points_count),0) indexed_points from indexed_documents;
select count(*) source_spans from source_span_lookup;
select action, count(*) from audit_events group by action order by count(*) desc;
"
```

Qdrant:

```bash
"${COMPOSE[@]}" exec -T retrieval python -c 'import httpx; r=httpx.get("http://qdrant:6333/collections/st_evidence_v1",timeout=10); print(r.status_code); print(r.text[:4000])'
```

API:

```bash
TOKEN=$(curl -fsS http://127.0.0.1/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"identifier":"admin","password":"admin"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

curl -fsS "http://127.0.0.1/api/search?question=никель&limit=5" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

Ожидаемый результат:

- `items` не пустой;
- `total_found > 0`;
- query answer содержит `sources_count > 0`;
- audit содержит `ingestion_upload`;
- Qdrant `points_count > 0`.

## Ошибка 413 при demo seed

Причина:

- nginx: `client_max_body_size 100M`;
- gateway: `Upload exceeds the 100 MB limit`;
- `scripts/seed_demo.py` отправляет весь corpus одним запросом.

Что не делать:

- не пытаться снова запускать `seed_demo.py` на большом корпусе без batch;
- не делать `down -v`;
- не считать успешный dictionary seed успешной загрузкой документов.

Что делать:

- использовать `--no-demo` при deploy;
- грузить полный датасет отдельным batch-процессом;
- либо доработать `seed_demo.py` на batch upload.

## Критичная проблема безопасности HTTP-deploy

Текущий HTTP overlay использует dev nginx:

```yaml
NGINX_CONFIG: dev
./infra/nginx/nginx.dev.conf:/etc/nginx/nginx.conf
```

В dev nginx публично доступны:

- `/orchestrator/`
- `/ingestion/`
- `/knowledge/`
- `/retrieval/`
- `/model/`

Подтверждённые риски:

- публичный `/model/v1/embeddings` может тратить Yandex API;
- публичный `/retrieval/v1/index/bootstrap` может менять состояние Qdrant collection;
- публичные internal endpoints раскрывают архитектуру и часть внутренних возможностей.

Срочное временное решение:

- закрыть публичный доступ к `/orchestrator`, `/ingestion`, `/knowledge`, `/retrieval`, `/model` на уровне nginx/security group;
- лучше перейти на `--https`, где prod nginx содержит deny/404 для этих путей.

Правильный кодовый фикс:

- `docker-compose.cloud.http.yml` не должен монтировать `nginx.dev.conf`;
- нужен отдельный HTTP prod edge config: порт 80, `/api` и `/` доступны, internal service prefixes возвращают `404`.

## Export падает 500

Теперь root cause подтверждён логами.

Ошибка:

```text
sqlalchemy.exc.InvalidRequestError: A transaction is already begun on this Session.
```

Трасса:

```text
services/orchestrator/app/api/query.py:113 export_run
services/orchestrator/app/service/service.py:1065 export_query_run
infra/postgres/orchestrator_db/repository.py:292 complete_export_with_artifacts
infra/postgres/orchestrator_db/product_events_storage.py:100 attach_export_artifacts
async with self._session.begin()
```

Причина:

- orchestrator уже работает с активной `AsyncSession`;
- `complete_export_with_artifacts()` вызывает `attach_export_artifacts()`;
- внутри `attach_export_artifacts()` открывается новый `async with self._session.begin()`;
- SQLAlchemy запрещает начинать новую transaction на session, где transaction уже начата.

Что важно:

- `st-export` сам создаёт jobs успешно: в логах есть `POST /v1/jobs 201 Created`.
- Значит export service генерирует артефакт.
- Падает сохранение export artifacts/status в orchestrator Postgres.

Кодовый фикс:

- убрать вложенный `async with self._session.begin()` из `attach_export_artifacts()` для сценария, где session уже управляется вызывающим repository;
- или добавить вариант метода без открытия transaction;
- после добавления artifacts сохранить `ExportJob` и сделать один commit на верхнем уровне.

Минимальная идея исправления:

```python
async def attach_export_artifacts(...):
    job = await self._session.get(ExportJob, export_job_id)
    ...
    self._session.add(row)
    ...
    if mark_completed:
        job.status = ExportJobStatus.COMPLETED.value
```

А commit оставить в `complete_export_with_artifacts()` через `_save_export_job(job)`.

После фикса проверить:

```bash
TOKEN=...
RUN_ID=...
curl -fsS http://127.0.0.1/api/export \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"query_run_id\":\"$RUN_ID\",\"format\":\"markdown\"}" | python3 -m json.tool
```

Ожидание:

- HTTP 200;
- есть `export_job_id`;
- есть `file_url`;
- в Postgres есть строки в `export_jobs` и `export_artifacts`.

## Strategic evaluation падает 500

Root cause подтверждён логами gateway:

```text
FileNotFoundError: [Errno 2] No such file or directory: 'eval/gold_questions.json'
```

Трасса:

```text
services/gateway/app/api/admin.py:92 strategic_evaluation
services/gateway/app/service/analytics_service.py:154 get_strategic_evaluation
Path("eval/gold_questions.json").read_text(...)
```

Причина:

- gateway Docker image не содержит `eval/gold_questions.json`;
- код не обрабатывает отсутствие fallback-файла;
- `/api/eval/report/summary` умеет вернуть `blocked_by_data`, а `/api/strategic/evaluation` падает 500.

Кодовый фикс:

1. Либо копировать `eval/` в gateway image.
2. Либо лучше: если нет `eval/reports/latest.json` и нет `eval/gold_questions.json`, возвращать пустую evaluation payload со статусом/предупреждением, а не 500.

Быстрый Dockerfile-вариант:

```dockerfile
COPY eval /app/services/gateway/eval
```

Более надёжный кодовый вариант:

```python
gold_path = Path("eval/gold_questions.json")
if not gold_path.is_file():
    return StrategicEvaluationPayload(
        summary=StrategicEvaluationSummary(),
        questions=[],
    )
```

## Knowledge graph warnings

В логах Neo4j warnings:

```text
relationship type does not exist: DESCRIBED_IN, PART_OF, QUANTIFIED_BY,
VALIDATED_BY, RELATED_TO, APPLIED_IN_GEOGRAPHY, USES_MATERIAL
property key does not exist: claim_last_updated_at
```

Причина на текущем стенде:

- в graph нет document/claim/source-span отношений, которые появляются после document ingestion;
- есть словарь и часть entity/gap данных, но нет корпуса claims/evidence.

Это не первичная причина падения, но симптом той же проблемы: документы не были загружены и извлечены в knowledge graph.

После настоящей загрузки корпуса эти warnings должны уменьшиться или исчезнуть для документных связей. Если после загрузки они останутся, тогда надо отдельно сверять writer queries knowledge service и reader queries graph evidence.

## Search/query сейчас работают технически, но без данных

Поведение:

- `/api/search` возвращает 200, но `items: []`;
- `/api/query` возвращает 200, но answer без источников;
- warnings включают `insufficient_accessible_evidence` или query-ir fallback;
- confidence `0.0`;
- `sources_count = 0`.

Это не LLM-проблема и не проблема Yandex credentials. Модель работает, но retrieval не даёт evidence.

## Query stream

`POST /api/query/stream` возвращает:

```text
404 stream_disabled
```

Причина:

- feature flag `top1_live_stream_enabled` выключен.

Это не блокирует обычный `/api/query`.

## Dictionary upload bug в UI

В UI helper для dictionary выбран путь:

```text
/documents/upload/dictionary
```

Backend endpoint:

```text
/dictionaries/upload
```

Последствия:

- document upload может работать;
- dictionary upload из этого UI helper может ломаться;
- `seed_demo.py` использует правильный backend путь для dictionary: `/dictionaries/upload`.

Кодовый фикс:

- заменить dictionary path в frontend на `/dictionaries/upload`;
- для dictionary form field использовать `package`, не `files`, если endpoint ожидает package.

## Что делать по шагам

### Шаг 1. Закрыть internal endpoints

До загрузки данных закрыть публичные `/model`, `/retrieval`, `/knowledge`, `/ingestion`, `/orchestrator`.

Временный вариант: перейти на `--https`.

Более правильный вариант: исправить `docker-compose.cloud.http.yml`, чтобы HTTP cloud не использовал dev nginx.

### Шаг 2. Найти датасет

```bash
find ~/ScientificTangle ~ -type f \
  \( -iname '*.pdf' -o -iname '*.docx' -o -iname '*.xlsx' -o -iname '*.csv' -o -iname '*.txt' -o -iname '*.md' \) \
  -printf '%s %p\n' 2>/dev/null | sort -nr | head -200
```

Если датасет не найден, перенести его на VM.

### Шаг 3. Загрузить документы batch-ами

Не через `seed_demo.py` одним запросом. Нужен batch upload меньше 100 MB на запрос.

### Шаг 4. Проверять каждую пачку

```bash
"${COMPOSE[@]}" exec -T postgres psql -U st_user -d scientific_tangle -c "
select status, count(*) from ingestion_tasks group by status;
select count(*) indexed_documents, coalesce(sum(indexed_points_count),0) indexed_points from indexed_documents;
select count(*) source_spans from source_span_lookup;
"
```

### Шаг 5. Проверить поиск

```bash
curl -fsS "http://127.0.0.1/api/search?question=никель&limit=5" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

### Шаг 6. Исправить export и strategic evaluation в коде

Нужны кодовые фиксы:

- export: убрать nested transaction в artifact attach path;
- strategic evaluation: не падать при отсутствии `eval/gold_questions.json` или копировать `eval/` в gateway image;
- frontend dictionary upload: путь `/dictionaries/upload`.

## Приоритеты

P0:

- закрыть публичные internal endpoints;
- перевыпустить Yandex key;
- восстановить ingestion полного датасета.

P1:

- исправить export 500;
- исправить strategic evaluation 500;
- добавить batch upload script.

P2:

- сделать реальный admin/source catalog;
- улучшить UI видимости загруженных документов;
- почистить graph/evaluation заглушки и synthetic metrics.

## Финальное состояние на момент отчёта

Стек живой, но corpus отсутствует в рабочем контуре. Единственный найденный raw upload в MinIO - dictionary package. Поэтому сейчас система может логинить пользователей, принимать запросы, показывать словарь/часть графа и health checks, но не может отвечать по полному датасету с источниками.

Главное исправление для данных: найти полный датасет и прогнать document ingestion batch-ами, затем проверить `indexed_documents > 0`, `source_spans > 0`, `Qdrant points_count > 0`.

## Дополнение после проверки датасета на VM

После дополнительной проверки на VM найден локальный скачанный корпус:

```text
demo/seed_data/yandex_disk_corpus
размер: 2.2G
файлов: 369
```

Это меняет диагноз с "датасет не найден" на более точный:

```text
датасет скачан на диск VM,
но не загружен в рабочее хранилище приложения.
```

Простыми словами: папка с файлами лежит рядом с проектом, но приложение работает не с этой папкой. Приложение работает с MinIO, Postgres, Neo4j и Qdrant. Сейчас в MinIO лежит только словарь, а документов корпуса там нет. Поэтому UI, поиск и чат ведут себя так, будто датасета нет.

Причина почти наверняка такая:

1. `cloud_deploy.sh` скачал corpus в `demo/seed_data/yandex_disk_corpus`.
2. Потом запустил `scripts/seed_demo.py`.
3. `seed_demo.py` попытался отправить все 2.2G одним upload request.
4. Gateway/nginx ограничивают upload 100 MB.
5. Запрос упал с `413 Request Entity Too Large`.
6. В приложение успел попасть словарь, но документы не попали.

## Почему найдено 2.2G, если ожидается около 5G

Это отдельный риск. Найденная папка `demo/seed_data/yandex_disk_corpus` весит 2.2G и содержит 369 файлов. Если согласованный полный датасет должен быть около 5G, значит нельзя считать найденную папку полной.

Возможные причины:

1. Публичная папка на Яндекс.Диске изменилась и сейчас отдаёт только 2.2G.
2. Скачивание прервалось, но скрипт не проверил ожидаемый общий размер.
3. В каталоге лежит только часть корпуса, а остальное должно быть в другой директории или другом архиве.
4. Команда `du -sh` показывает физический размер текущей папки, а ожидаемые 5G могли относиться к другому формату: архив плюс распакованные файлы, другая версия корпуса или полный коммерческий датасет.
5. Часть файлов могла быть пропущена из-за сетевой ошибки, лимита API, удаления на источнике или ручной чистки.

Важный технический момент: `eval/yandex_disk_corpus.py` скачивает список файлов с внешнего публичного ресурса и пишет локальный `manifest.json`, но в коде нет закреплённого ожидаемого размера, ожидаемого количества файлов или эталонного checksum всего корпуса. Поэтому текущий проект не умеет сам сказать: "скачано 2.2G из ожидаемых 5G, корпус неполный".

Проверить локальный manifest:

```bash
python3 - <<'PY'
import json
from pathlib import Path

root = Path("demo/seed_data/yandex_disk_corpus")
manifest = root / "manifest.json"
print("manifest_exists:", manifest.exists())
if manifest.exists():
    data = json.loads(manifest.read_text(encoding="utf-8"))
    files = data.get("files", [])
    total = sum(int(item.get("size") or 0) for item in files)
    print("manifest_files:", len(files))
    print("manifest_size_bytes:", total)
    print("manifest_size_gib:", round(total / 1024 / 1024 / 1024, 2))
    print("source:", data.get("source"))
PY
```

Проверить фактический размер файлов без `du`:

```bash
python3 - <<'PY'
from pathlib import Path

root = Path("demo/seed_data/yandex_disk_corpus")
files = [p for p in root.rglob("*") if p.is_file() and p.name != "manifest.json"]
total = sum(p.stat().st_size for p in files)
print("actual_files:", len(files))
print("actual_size_bytes:", total)
print("actual_size_gib:", round(total / 1024 / 1024 / 1024, 2))
PY
```

Проверить, что сейчас отдаёт публичная папка Яндекс.Диска, не скачивая всё заново:

```bash
python3 - <<'PY'
import httpx

public_key = "https://disk.yandex.ru/d/npigiuw4Rbe9Pg"
api = "https://cloud-api.yandex.net/v1/disk/public/resources"
queue = ["/"]
files = []
with httpx.Client(timeout=60.0) as client:
    while queue:
        path = queue.pop(0)
        r = client.get(api, params={"public_key": public_key, "path": path, "limit": 1000})
        r.raise_for_status()
        for item in r.json().get("_embedded", {}).get("items", []):
            if item.get("type") == "dir":
                queue.append(item["path"])
            elif item.get("type") == "file":
                files.append(item)
total = sum(int(item.get("size") or 0) for item in files)
print("remote_files:", len(files))
print("remote_size_bytes:", total)
print("remote_size_gib:", round(total / 1024 / 1024 / 1024, 2))
for item in sorted(files, key=lambda x: int(x.get("size") or 0), reverse=True)[:20]:
    print(item.get("size"), item.get("path"))
PY
```

Интерпретация:

- если `remote_size_gib` тоже около 2.2, внешний публичный источник сейчас не содержит ожидаемые 5G;
- если `remote_size_gib` около 5, локальное скачивание неполное и нужно докачивать;
- если `manifest_size_gib` около 2.2 и `remote_size_gib` около 5, manifest был создан по неполному или старому remote listing;
- если на VM где-то есть ещё 2-3G документов, они лежат вне `demo/seed_data/yandex_disk_corpus`.

Найти остальные крупные файлы на VM:

```bash
find ~/ScientificTangle ~ -type f \( -iname '*.pdf' -o -iname '*.docx' -o -iname '*.pptx' -o -iname '*.xlsx' -o -iname '*.csv' -o -iname '*.txt' -o -iname '*.md' -o -iname '*.zip' -o -iname '*.rar' -o -iname '*.7z' \) -printf '%s %p\n' 2>/dev/null | sort -nr | head -300
```

До выяснения этого пункта правильная формулировка такая: на VM найден не полный доказанный датасет, а локальная папка corpus объёмом 2.2G. Её всё равно нужно грузить batch-ами, но параллельно надо подтвердить, где остальные примерно 2.8G или почему ожидание 5G устарело.

## Исправление команд для поиска файлов

Команда `find` сломалась из-за пробелов после `\`. В bash обратный слеш продолжает строку только если он последний символ строки. Если после него есть пробел, shell ломает выражение.

Безопасная однострочная команда:

```bash
find ~/ScientificTangle ~ -type f \( -iname '*.pdf' -o -iname '*.docx' -o -iname '*.xlsx' -o -iname '*.csv' -o -iname '*.txt' -o -iname '*.md' -o -iname '*.zip' \) -printf '%s %p\n' 2>/dev/null | sort -nr | head -200
```

Для уже найденного корпуса:

```bash
du -sh ~/ScientificTangle/demo/seed_data/yandex_disk_corpus && find ~/ScientificTangle/demo/seed_data/yandex_disk_corpus -type f | wc -l && find ~/ScientificTangle/demo/seed_data/yandex_disk_corpus -type f -printf '%s %p\n' | sort -nr | head -50
```

## Целевая архитектурная идея

Нужен "мощный внутри, слабый снаружи" стенд.

Это значит:

- внутри Docker-сети сервисы могут свободно общаться друг с другом;
- снаружи открыт только nginx;
- снаружи доступны только UI, `/api/*`, health и при необходимости Grafana под Basic Auth;
- `/model`, `/retrieval`, `/knowledge`, `/ingestion`, `/orchestrator`, `/qdrant`, `/minio`, `/postgres`, `/neo4j`, `/redis` снаружи недоступны;
- данные проходят только через gateway и auth;
- Yandex API никогда не вызывается напрямую с публичного endpoint;
- загрузка большого корпуса идёт через управляемый batch-ingestion, а не через один огромный запрос.

Внутри это "франкенштейн" в хорошем смысле: много специализированных органов - auth, gateway, orchestrator, ingestion, knowledge, retrieval, model, export, notification, MinIO, Qdrant, Neo4j, Postgres. Снаружи он должен выглядеть как один спокойный продукт: web UI и API, без торчащих внутренних органов.

## План исправлений по независимым задачам

Ниже задачи разбиты так, чтобы несколько человек могли делать их одновременно с минимальными конфликтами. Каждую задачу лучше вести в отдельной ветке `feat/*` и вливать через PR.

### Task A. Закрыть внешний периметр HTTP cloud

Приоритет: P0  
Можно делать параллельно с: B, C, D, E, F  
Основные файлы:

- `docker-compose.cloud.http.yml`
- `infra/nginx/nginx.prod.conf.template`
- новый `infra/nginx/nginx.cloud.http.conf`, если решим делать отдельный HTTP edge config
- `scripts/cloud_deploy.sh`
- `infra/deploy/OPERATOR.md`

Проблема:

HTTP cloud сейчас использует dev nginx. Из-за этого публично доступны `/model`, `/retrieval`, `/knowledge`, `/ingestion`, `/orchestrator`.

Что сделать:

1. Убрать mount `nginx.dev.conf` из `docker-compose.cloud.http.yml`.
2. Сделать HTTP cloud config, который слушает 80 порт без TLS, но блокирует internal prefixes.
3. Оставить наружу только `/`, `/api/`, `/api/auth/`, `/.well-known/jwks.json`, `/grafana/` под Basic Auth.
4. Добавить smoke check:

```bash
curl -i http://51.250.103.29/model/v1/status
curl -i http://51.250.103.29/retrieval/health
curl -i http://51.250.103.29/api/health
```

Ожидание:

- `/api/health` -> 200;
- `/model/...` -> 404;
- `/retrieval/...` -> 404.

Критерий готовности:

- internal services недоступны снаружи;
- cloud deploy продолжает поднимать UI и API;
- документация оператора обновлена.

### Task B. Batch ingestion script для полного корпуса

Приоритет: P0  
Можно делать параллельно с: A, C, D, E, F  
Основные файлы:

- новый `scripts/seed_corpus_batches.py` или доработка `scripts/seed_demo.py`
- возможно `infra/deploy/OPERATOR.md`
- возможно `docs/cloud_stand_audit_2026-07-05.md`

Проблема:

Датасет 2.2G уже скачан, но текущий seed script отправляет всё одним запросом и получает 413.

Что сделать:

1. Скрипт принимает `--corpus-dir`, `--api-url`, `--username`, `--password`.
2. Собирает файлы рекурсивно.
3. Исключает `manifest.json` и служебные файлы.
4. Группирует файлы по лимиту, например `--max-batch-bytes 80000000`.
5. Отправляет каждую пачку в `/api/documents/upload`.
6. Poll-ит `/api/tasks/{task_id}` до `completed` или `failed`.
7. После каждой пачки печатает:

```text
batch number
files count
bytes
task_id
status
documents_count
source_spans_count
indexed_points_count
warnings
```

8. Умеет `--resume`, чтобы не начинать с нуля после падения.
9. Пишет state file, например `.seed_corpus_batches_state.json`.

Критерий готовности:

- можно загрузить 2.2G corpus без 413;
- после загрузки `indexed_documents > 0`, `source_spans > 0`, `Qdrant points_count > 0`;
- падение одной пачки не теряет прогресс.

### Task C. Проверить и усилить ingestion pipeline на больших PDF/PPTX

Приоритет: P0/P1  
Можно делать параллельно с: A, B, D, E, F  
Основные зоны:

- `services/ingestion`
- `services/orchestrator/app/service/service.py`
- LibreOffice/PDF normalization path
- logs и timeout settings

Проблема:

Даже после batch upload отдельные большие файлы могут упасть на normalize/extract/index. Самый большой файл около 111 MB, то есть он один уже больше текущего 100 MB upload limit.

Что сделать:

1. Для файлов больше 100 MB решить политику:
   - либо временно поднять лимит до 150-200 MB;
   - либо предварительно дробить/исключать такие файлы;
   - либо грузить через внутренний server-side importer, который читает локальную папку без HTTP upload.
2. Добавить явный отчёт по unsupported files.
3. Проверить timeout normalize для больших PDF/PPTX.
4. Проверить, что failed task пишет понятный `error_message`.

Критерий готовности:

- большой корпус проходит не только upload, но и normalize/index;
- проблемные файлы перечислены явно;
- оператор понимает, что делать с каждым failed file.

### Task D. Починить export 500

Приоритет: P1  
Можно делать параллельно с: A, B, C, E, F  
Основные файлы:

- `infra/postgres/orchestrator_db/repository.py`
- `infra/postgres/orchestrator_db/product_events_storage.py`
- `services/orchestrator/app/service/service.py`
- тесты orchestrator export

Проблема:

Export service создаёт artifact, но orchestrator падает при записи export artifacts:

```text
sqlalchemy.exc.InvalidRequestError: A transaction is already begun on this Session.
```

Что сделать:

1. Убрать вложенный `async with self._session.begin()` в path `complete_export_with_artifacts -> attach_export_artifacts`.
2. Оставить один commit на верхнем уровне repository.
3. Добавить regression test: export completed run создаёт `export_jobs` и `export_artifacts`.
4. Проверить все форматы: `markdown`, `json`, `jsonld`.

Критерий готовности:

- `/api/export` возвращает 200 на completed query run;
- artifact можно скачать;
- в БД нет pending/processing export jobs после успешного запроса.

### Task E. Починить strategic evaluation 500

Приоритет: P1  
Можно делать параллельно с: A, B, C, D, F  
Основные файлы:

- `services/gateway/app/service/analytics_service.py`
- `services/gateway/Dockerfile`
- тесты gateway analytics/admin

Проблема:

Gateway падает:

```text
FileNotFoundError: eval/gold_questions.json
```

Что сделать:

1. Не падать, если нет `eval/reports/latest.json`.
2. Не падать, если нет `eval/gold_questions.json`.
3. Вернуть нормальный `blocked_by_data`/empty payload.
4. Если нужен fallback gold file в runtime, явно копировать `eval/` в Docker image.

Критерий готовности:

- `/api/strategic/evaluation` никогда не даёт 500 из-за отсутствующего eval file;
- `/api/eval/report/summary` и `/api/strategic/evaluation` согласованы по смыслу.

### Task F. Починить dictionary upload в UI

Приоритет: P1/P2  
Можно делать параллельно с: A, B, C, D, E  
Основные файлы:

- `ui/src/api/uploadCore.js`
- `ui/src/pages/UploadPage.jsx`
- UI/e2e tests

Проблема:

UI helper отправляет dictionary на `/documents/upload/dictionary`, а backend endpoint - `/dictionaries/upload` и ожидает field `package`.

Что сделать:

1. Для `kind === "dictionary"` отправлять `/dictionaries/upload`.
2. В FormData использовать `package`, не `files`.
3. Проверить, что document upload остался на `/documents/upload`.

Критерий готовности:

- dictionary upload из UI работает;
- document upload из UI работает;
- e2e/mock API обновлены.

### Task G. Реальный каталог документов и видимость ingestion

Приоритет: P2  
Можно делать параллельно после B/C или частично параллельно  
Основные зоны:

- gateway admin/search endpoints
- orchestrator repository
- UI admin/upload pages

Проблема:

Сейчас оператор не видит простой список: какие документы загружены, какие проиндексированы, какие упали.

Что сделать:

1. Добавить endpoint document catalog:

```text
GET /api/documents
```

2. Для каждого документа показывать:

```text
document_id
title/path
source_type
ingestion_task_id
status
source_spans_count
indexed_points_count
created_at
warnings/errors
```

3. В UI добавить страницу или блок Admin/Documents.
4. Добавить фильтры: completed, failed, no_index, no_source_spans.

Критерий готовности:

- оператор без SQL видит, загружен ли корпус;
- видно, какие файлы надо перезалить или исключить.

### Task H. Recovery runbook и one-command verify

Приоритет: P1  
Можно делать параллельно с: A-F  
Основные файлы:

- `infra/deploy/OPERATOR.md`
- новый `scripts/cloud_verify.sh`
- возможно `scripts/seed_inventory.py`

Проблема:

Сейчас диагностика требует много ручных SQL/curl команд.

Что сделать:

1. Скрипт `scripts/cloud_verify.sh` печатает:
   - compose ps;
   - health/all;
   - MinIO source-files count;
   - Postgres ingestion counts;
   - Qdrant points count;
   - public perimeter check;
   - export/eval smoke status.
2. Документация говорит, что считать нормой.

Критерий готовности:

- оператор одной командой понимает: стенд живой, данные есть, периметр закрыт, поиск работает.

## Параллельный план работ без конфликтов

Можно распределить так:

```text
Инженер 1: Task A - внешний периметр nginx/cloud HTTP
Инженер 2: Task B - batch ingestion script
Инженер 3: Task C - большие файлы и устойчивость ingestion
Инженер 4: Task D - export transaction bug
Инженер 5: Task E - strategic evaluation fallback
Инженер 6: Task F - UI dictionary upload
Инженер 7: Task H - verify/runbook
```

Зависимости:

- Task B и C вместе дают восстановление корпуса.
- Task A надо сделать до публичного активного использования стенда.
- Task D/E/F можно чинить независимо от данных.
- Task G лучше делать после B/C, потому что станет ясно, какие реальные статусы и метрики нужны.

## Немедленный план на текущей VM

Без ожидания кодовых PR можно сделать так:

1. Не трогать volumes.
2. Не запускать `seed_demo.py` как есть.
3. Закрыть public internal endpoints или перейти на `--https`.
4. Сделать batch uploader или временно загрузить через UI маленькими пачками.
5. Начать с маленькой тестовой пачки 1-3 файла до 50 MB.
6. После пачки проверить:

```bash
"${COMPOSE[@]}" exec -T postgres psql -U st_user -d scientific_tangle -c "select status, count(*) from ingestion_tasks group by status; select count(*) indexed_documents, coalesce(sum(indexed_points_count),0) indexed_points from indexed_documents; select count(*) source_spans from source_span_lookup;"
```

7. Если counts выросли, продолжать batch ingestion.
8. Если task failed, читать:

```bash
"${COMPOSE[@]}" exec -T postgres psql -U st_user -d scientific_tangle -c "select id,status,error_message,report from ingestion_tasks order by created_at desc limit 5;"
```

9. После полного ingestion проверить search/query.

## Что считать успехом проекта

Минимальный успешный стенд:

- public internal endpoints закрыты;
- корпус загружен;
- `indexed_documents > 0`;
- `source_spans > 0`;
- Qdrant `points_count > 0`;
- `/api/search` возвращает источники;
- `/api/query` отвечает с `sources_count > 0`;
- `/api/export` возвращает 200;
- `/api/strategic/evaluation` не падает 500;
- оператор видит состояние данных без ручного SQL.

Целевой хороший стенд:

- все 369 файлов обработаны или явно перечислены как unsupported/failed;
- каждый failed file имеет понятную причину;
- повторный deploy с `--no-demo` не ломает данные;
- batch uploader умеет resume;
- verify script одной командой показывает состояние;
- внешний пользователь видит только аккуратный UI/API, а не внутреннюю механику.
