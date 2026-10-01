.PHONY: db-up-nodocker schemas help setup dev dev-api dev-web test test-api test-web lint format typecheck db-up db-down db-migrate db-revision render-sample e2e

export PATH := $(HOME)/.local/bin:$(PATH)

help:      ## list commands
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-16s %s\n", $$1, $$2}'

setup:     ## install all dependencies (uv + pnpm) and create .env if missing
	cd apps/api && uv sync
	pnpm install
	@test -f .env || cp .env.example .env

db-up:     ## start PostgreSQL (+pgvector) via docker compose
	docker compose up -d --wait postgres

db-down:   ## stop containers
	docker compose down

db-migrate: ## apply Alembic migrations
	cd apps/api && uv run alembic upgrade head

db-revision: ## autogenerate a migration: make db-revision m="message"
	cd apps/api && uv run alembic revision --autogenerate -m "$(m)"

dev-api:   ## API on :8000
	cd apps/api && uv run uvicorn app.main:app --reload --port 8000

dev-web:   ## web on :3100
	pnpm --filter @storyweaver/web dev

dev:       ## API + web together (Ctrl-C stops both)
	@trap 'kill 0' INT TERM; $(MAKE) dev-api & $(MAKE) dev-web & wait

test: test-api test-web ## all unit tests

test-api:  ## pytest (DB tests need TEST_DATABASE_URL, otherwise they skip)
	cd apps/api && uv run pytest

test-web:  ## vitest (web + video package)
	pnpm --filter @storyweaver/web test
	pnpm --filter @storyweaver/video test

e2e:       ## Playwright end-to-end
	pnpm --filter @storyweaver/web test:e2e

lint:      ## ruff + pyright + eslint + tsc
	cd apps/api && uv run ruff check app tests && uv run ruff format --check app tests && uv run pyright
	pnpm --filter @storyweaver/web lint
	pnpm --filter @storyweaver/web typecheck
	pnpm --filter @storyweaver/video typecheck

format:    ## ruff format + prettier
	cd apps/api && uv run ruff format app tests && uv run ruff check --fix app tests
	pnpm --filter @storyweaver/web format

render-sample: ## render packages/video/sample/timeline.json to MP4
	pnpm --filter @storyweaver/video render

schemas:   ## regenerate packages/schemas from Pydantic models
	cd apps/api && uv run python ../../scripts/export_schemas.py

db-up-nodocker: ## Postgres+pgvector without Docker (prints DATABASE_URL / TEST_DATABASE_URL)
	cd apps/api && uv run --with pgserver python ../../scripts/dev_postgres.py
