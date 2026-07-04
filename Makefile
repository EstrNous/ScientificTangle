.PHONY: bootstrap up down build logs seed ingest-demo e2e eval eval-yandex-live perf-smoke reset-demo seed-counts reset-reseed-offline reset-reseed lint test test-model test-neo4j-integration test-yandex-live export-demo

bootstrap:
	python scripts/generate_auth_keys.py

up: bootstrap
	docker compose up -d

down:
	docker compose down -v

build:
	docker compose build

logs:
	docker compose logs -f $(SERVICE)

seed:
	docker compose exec auth_audit auth-seed-users
	docker compose exec gateway sh -c "cd /app/infra/postgres/notification_db && PYTHONPATH=. python seed.py"
	python scripts/seed_demo.py

ingest-demo:
	python scripts/seed_demo.py

e2e:
	RUN_E2E=1 python scripts/run_tests.py

eval:
	python eval/run_eval.py --service-url $${EVAL_SERVICE_URL:-http://localhost:8000/api/query} --gold $${EVAL_GOLD:-eval/gold_questions.json} --auth-token-env EVAL_AUTH_TOKEN --official-only

eval-yandex-live:
	RUN_MODEL_TESTS=1 python scripts/yandex_live_smoke.py
	RUN_MODEL_TESTS=1 python scripts/seed_demo.py --fail-on-degraded
	RUN_MODEL_TESTS=1 python scripts/eval_yandex_live.py

perf-smoke:
	python scripts/perf_smoke.py

reset-demo:
	docker compose down -v
	python scripts/generate_auth_keys.py
	docker compose up -d
	docker compose exec auth_audit auth-seed-users
	python scripts/seed_demo.py

seed-counts:
	python scripts/seed_inventory.py --mode report --include-remote

reset-reseed-offline:
	python scripts/seed_inventory.py --mode offline --output tmp/seed_offline_report.json

reset-reseed:
	python scripts/seed_inventory.py --mode full --output tmp/seed_full_report.json

lint:
	ruff check shared services scripts tests
	cd ui && npm run lint

test:
	python scripts/run_tests.py

test-model:
	RUN_MODEL_TESTS=1 python scripts/run_tests.py

test-neo4j-integration:
	cd tests/integration && RUN_NEO4J_INTEGRATION=1 python -m pytest test_neo4j_smoke.py -v

test-yandex-live:
	RUN_MODEL_TESTS=1 python scripts/yandex_live_smoke.py

export-demo:
	@echo "export-demo: use ui ExportPanel or eval reports"
