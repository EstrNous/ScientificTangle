.PHONY: bootstrap bootstrap-prod ensure-env up up-prod prod down down-prod build build-prod logs logs-prod seed seed-prod prod-demo ingest-demo e2e eval eval-offline-quality eval-yandex-live perf-smoke reset-demo lint test test-model test-neo4j-integration test-yandex-live export-demo deploy-cloud cloud-up cloud-ps cloud-logs cloud-down

COMPOSE_DEV = docker compose -f docker-compose.yml -f docker-compose.dev.yml
COMPOSE_PROD = docker compose -f docker-compose.yml -f docker-compose.prod.yml
COMPOSE_CLOUD = docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.cloud.yml -f docker-compose.cloud.http.yml

bootstrap:
	python scripts/generate_auth_keys.py

bootstrap-prod: bootstrap
	python scripts/generate_tls_certs.py

ensure-env:
	python scripts/ensure_env.py

up: bootstrap ensure-env
	$(COMPOSE_DEV) up -d

up-prod: ensure-env bootstrap-prod
	$(COMPOSE_PROD) up -d --build --wait

prod: up-prod seed-prod
	@echo Prod ready: https://localhost/  curl -k https://localhost/api/health

down:
	$(COMPOSE_DEV) down -v

down-prod:
	$(COMPOSE_PROD) down -v

build:
	$(COMPOSE_DEV) build

build-prod:
	$(COMPOSE_PROD) build

logs:
	$(COMPOSE_DEV) logs -f $(SERVICE)

logs-prod:
	$(COMPOSE_PROD) logs -f $(SERVICE)

seed:
	$(COMPOSE_DEV) exec auth_audit auth-seed-users
	$(COMPOSE_DEV) exec notification sh -c "cd /app/infra/postgres/notification_db && PYTHONPATH=. python seed.py"
	python scripts/seed_demo.py

seed-prod:
	$(COMPOSE_PROD) exec -T auth_audit auth-seed-users
	$(COMPOSE_PROD) exec -T notification sh -c "cd /app/infra/postgres/notification_db && PYTHONPATH=. python seed.py"

prod-demo: prod
	DEMO_API_URL=https://localhost/api EDGE_TLS_VERIFY=false python scripts/seed_demo.py

ingest-demo:
	python scripts/seed_demo.py

e2e:
	RUN_E2E=1 python scripts/run_tests.py

eval:
	python eval/run_eval.py --service-url $${EVAL_SERVICE_URL:-http://localhost:8000/api/query} --gold $${EVAL_GOLD:-eval/gold_questions.json} --auth-token-env EVAL_AUTH_TOKEN --official-only

eval-offline-quality:
	python eval/offline_quality_gate.py $(EVAL_OFFLINE_ARGS)

eval-yandex-live:
	RUN_MODEL_TESTS=1 python scripts/yandex_live_smoke.py
	RUN_MODEL_TESTS=1 python scripts/seed_demo.py --fail-on-degraded
	RUN_MODEL_TESTS=1 python scripts/eval_yandex_live.py

perf-smoke:
	python scripts/perf_smoke.py

reset-demo:
	$(COMPOSE_DEV) down -v
	python scripts/generate_auth_keys.py
	$(COMPOSE_DEV) up -d
	$(COMPOSE_DEV) exec auth_audit auth-seed-users
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

deploy-cloud:
	@test -n "$(HOST)" || (echo "Usage: make deploy-cloud HOST=203.0.113.10 [DEPLOY_ARGS='--install-docker']" && exit 1)
	bash scripts/cloud_deploy.sh $(HOST) $(DEPLOY_ARGS)

cloud-up:
	$(COMPOSE_CLOUD) up -d --build --wait

cloud-ps:
	$(COMPOSE_CLOUD) ps

cloud-logs:
	$(COMPOSE_CLOUD) logs -f $(SERVICE)

cloud-down:
	$(COMPOSE_CLOUD) down
