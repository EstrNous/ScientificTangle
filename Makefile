.PHONY: up down build logs seed ingest-demo e2e eval perf-smoke reset-demo lint test export-demo

up:
	docker compose up -d

up-auth:
	docker compose up -d auth_audit

down:
	docker compose down -v

build:
	docker compose build

logs:
	docker compose logs -f $(SERVICE)

seed:
	@echo "TODO: seed data"

ingest-demo:
	@echo "TODO: ingest demo data"

e2e:
	@echo "TODO: run e2e tests"

eval:
	python eval/run_eval.py --service-url $${EVAL_SERVICE_URL:-http://localhost:8000/api/query} --gold $${EVAL_GOLD:-eval/gold_questions.json} $${EVAL_DOCUMENTS:+--documents $$EVAL_DOCUMENTS} $${INGESTION_NORMALIZE_URL:+--ingestion-normalize-url $$INGESTION_NORMALIZE_URL} --auth-token-env EVAL_AUTH_TOKEN

perf-smoke:
	@echo "TODO: run performance smoke test"

reset-demo:
	@echo "TODO: reset demo data"

lint:
	@echo "TODO: run linters"

test:
	@echo "TODO: run tests"

export-demo:
	@echo "TODO: export demo"
