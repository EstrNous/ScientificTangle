.PHONY: up down build logs seed ingest-demo e2e eval perf-smoke reset-demo lint test export-demo

up:
	docker compose up -d

up-auth:
	docker compose --profile auth up -d

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
	@echo "TODO: run evaluation"

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
