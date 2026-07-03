.PHONY: up down build logs seed ingest-demo e2e eval perf-smoke reset-demo lint test export-demo audit

up:
	docker compose up -d

down:
	docker compose down -v

build:
	docker compose build

logs:
	docker compose logs -f $(SERVICE)

seed:
	python -m infra.postgres.auth_audit_db.seed

ingest-demo:
	@echo "ingest-demo: use eval with EVAL_DOCUMENTS"

e2e:
	RUN_E2E=1 python scripts/run_tests.py

eval:
	python eval/run_eval.py --service-url $${EVAL_SERVICE_URL:-http://localhost:8000/api/query} --gold $${EVAL_GOLD:-eval/gold_questions.json} $${EVAL_DOCUMENTS:+--documents $$EVAL_DOCUMENTS} $${INGESTION_NORMALIZE_URL:+--ingestion-normalize-url $$INGESTION_NORMALIZE_URL} --auth-token-env EVAL_AUTH_TOKEN

perf-smoke:
	python -m pytest -q tests/performance

reset-demo:
	docker compose down -v

lint:
	ruff check shared services scripts tests
	cd ui && npm run lint

test:
	python scripts/run_tests.py

audit:
	python scripts/audit_repo.py

export-demo:
	@echo "export-demo: use ui ExportPanel or eval reports"
