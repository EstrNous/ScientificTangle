.PHONY: bootstrap up down build logs seed ingest-demo e2e eval eval-yandex-live perf-smoke reset-demo lint test test-yandex-live export-demo

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
	python scripts/seed_demo.py

ingest-demo:
	python scripts/seed_demo.py

e2e:
	RUN_E2E=1 python scripts/run_tests.py

eval:
	python eval/run_eval.py --service-url $${EVAL_SERVICE_URL:-http://localhost:8000/api/query} --gold $${EVAL_GOLD:-eval/gold_questions.json} --auth-token-env EVAL_AUTH_TOKEN

eval-yandex-live:
	python scripts/yandex_live_smoke.py
	python scripts/seed_demo.py --fail-on-degraded
	python scripts/eval_yandex_live.py

perf-smoke:
	python scripts/perf_smoke.py

reset-demo:
	python scripts/seed_demo.py

lint:
	ruff check shared services scripts tests
	cd ui && npm run lint

test:
	python -m pytest services/retrieval/tests
	python -m pytest services/ingestion/tests
	python -m pytest services/orchestrator/tests
	python -m pytest tests/integration/test_eval_runner.py

test-yandex-live:
	python scripts/yandex_live_smoke.py

export-demo:
	@echo "export-demo: use ui ExportPanel or eval reports"
