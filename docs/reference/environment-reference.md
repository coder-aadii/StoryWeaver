# Environment Reference

> Every setting the API reads, its default, and what it controls.

## Status

Implemented. Source of truth: [`apps/api/app/core/config.py`](../../apps/api/app/core/config.py) and [`.env.example`](../../.env.example). Narrative guidance: [environment variables](../operations/environment-variables.md), [configuration](../operations/configuration.md).

Settings are read from the process environment, then `<repo>/.env`. Names are case-insensitive. Unknown variables are ignored. **No provider variable is required to boot.**

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+psycopg://storyweaver:storyweaver@localhost:5433/storyweaver` | SQLAlchemy URL (psycopg 3) |
| `TEST_DATABASE_URL` | unset | Used only by pytest (read from the environment, not `Settings`); DB tests skip without it. **Tests drop and recreate all tables** — the database name must end in `_test` and must differ from `DATABASE_URL`, or the run is refused before any DDL (see `STORYWEAVER_ALLOW_DESTRUCTIVE_TESTS`) |
| `STORAGE_ROOT` | `<repo>/data` | Local storage root. An empty or blank value means "unset" and also resolves to `<repo>/data`; a relative value resolves against the repository root (previously KI-1, resolved in P0 — [history](status.md#known-issues-and-limitations)) |
| `MAX_UPLOAD_BYTES` | 536870912 | Cap enforced by `LocalStorage.put` |
| `ENVIRONMENT` | `development` | Label only |
| `LOG_LEVEL` | `INFO` | Structured log level |
| `CORS_ORIGINS` | `["http://localhost:3000","http://localhost:3100","http://127.0.0.1:3100"]` | JSON list of allowed browser origins |
| `LLM_TIMEOUT_SECONDS` | 120 | HTTP timeout for every provider call (LLM and embeddings); a timeout raises `ProviderTimeoutError` |
| `DB_CONNECT_TIMEOUT_SECONDS` | 10 | Database connect timeout (1–120); bounds how long an unreachable host can stall a request or `/health/ready` |
| `STORYWEAVER_ALLOW_DESTRUCTIVE_TESTS` | unset | Tests only: set to `1` to allow a `TEST_DATABASE_URL` whose name does not end in `_test` (never the application database) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama (LLM + embeddings) |
| `GOOGLE_AI_API_KEY` | empty | Google adapter (header auth) |
| `GROK_API_KEY` | empty | xAI adapter |
| `OPENROUTER_API_KEY` | empty | OpenRouter adapter |
| `ANTHROPIC_BASE_URL`, `ANTHROPIC_API_KEY` | empty | Claude-compatible Messages endpoint; both needed |
| `COMFYUI_BASE_URL` | empty | Enables the ComfyUI stub's reachability check |
| `TEMPORAL_ADDRESS` | empty | Reported by `/health/providers`; not otherwise used |
| `DEFAULT_LLM_PROVIDER` | `ollama` | `ollama`, `google`, `openrouter`, `grok`, `claude` |
| `DEFAULT_LLM_MODEL` | empty | Required before any generation call |
| `ANALYSIS_LLM_MODEL`, `STORY_LLM_MODEL`, `SCRIPT_LLM_MODEL`, `CLASSIFICATION_LLM_MODEL` | empty | Per-task override; falls back to `DEFAULT_LLM_MODEL` |
| `EMBEDDING_PROVIDER` | `ollama` | `ollama` or `google` |
| `EMBEDDING_MODEL` | empty | |
| `EMBEDDING_DIMENSIONS` | 768 | Independent of the DB column, which is fixed at 768 by a constant; nothing checks they match, and the setting is not read by any code ([KI-6](status.md#known-issues-and-limitations); see [vectors](../data/embeddings-and-vector-search.md)) |
| `POSTGRES_USER/PASSWORD/DB/PORT` | `storyweaver` ×3 / `5433` | Read by `docker-compose.yml` only |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Web → API base URL (browser-visible; no secrets). Next.js reads env files from `apps/web/`, so set it in `apps/web/.env.local` or the shell, not the root `.env` ([KI-21](status.md#known-issues-and-limitations)) |
| `PLAYWRIGHT_CHROMIUM_PATH` | unset | Use an existing Chromium for e2e |

Note: `ENVIRONMENT`, `LOG_LEVEL`, `MAX_UPLOAD_BYTES` and `CORS_ORIGINS` are listed in `.env.example` as commented defaults (KI-26, partly resolved in P0); `LLM_TIMEOUT_SECONDS`, `DB_CONNECT_TIMEOUT_SECONDS` and `EMBEDDING_DIMENSIONS` are settings that work if set but are not listed there. This table is the canonical variable reference; [operations/environment-variables](../operations/environment-variables.md) and [configuration](../operations/configuration.md) give guidance and link here.
