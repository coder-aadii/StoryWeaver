# Configuration

> How configuration is loaded and where defaults live.

## Status

Implemented.

## Mechanism

`apps/api/app/core/config.py` defines `Settings` (pydantic-settings). Sources, highest priority first: process environment, then `<repo>/.env`. Unknown keys are ignored. `get_settings()` is `lru_cache`d — **restart the API after changing `.env`**.

Defaults make the app bootable with nothing set: Ollama URL `http://localhost:11434`, DB `postgresql+psycopg://storyweaver:storyweaver@localhost:5433/storyweaver`, storage root `<repo>/data`, upload cap 512 MiB. Exact defaults live in the [environment reference](../reference/environment-reference.md).

> **Note — empty values.** `STORAGE_ROOT` treats an empty or blank value as unset and resolves to `<repo>/data` (previously KI-1, resolved in P0); a relative value resolves against the repository root. For other string settings an empty value simply means "not configured". Next.js reads env files from `apps/web/` (see `apps/web/.env.example`).

## Groups

- **Database:** `DATABASE_URL`. (`POSTGRES_*` in `.env.example` feed Docker Compose only.)
- **Storage:** `STORAGE_ROOT`, `MAX_UPLOAD_BYTES`.
- **Providers:** `OLLAMA_BASE_URL`, `GOOGLE_AI_API_KEY`, `GROK_API_KEY`, `OPENROUTER_API_KEY`, `ANTHROPIC_BASE_URL`, `ANTHROPIC_API_KEY`, `COMFYUI_BASE_URL`, `TEMPORAL_ADDRESS`.
- **Model routing:** `DEFAULT_LLM_PROVIDER`, `DEFAULT_LLM_MODEL`, `ANALYSIS_LLM_MODEL`, `STORY_LLM_MODEL`, `SCRIPT_LLM_MODEL`, `CLASSIFICATION_LLM_MODEL`, `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`. `Settings.model_for(task)` falls back to `DEFAULT_LLM_MODEL`. See [model routing](../ai/model-routing.md).
- **App:** `ENVIRONMENT`, `LOG_LEVEL`, `CORS_ORIGINS` (a JSON array, e.g. `["http://localhost:3100"]`, as parsed by pydantic-settings).
- **Web:** `NEXT_PUBLIC_API_URL` (browser-visible, contains no secrets). Put it in `apps/web/.env.local` or the shell ([KI-21](../reference/status.md#known-issues-and-limitations)).

## Gaps

- `EMBEDDING_DIMENSIONS` exists in `Settings` (default 768) but the DB column width is the separate constant `EMBEDDING_DIM` in `models/domain.py`; the two are independent and unchecked ([KI-6](../reference/status.md#known-issues-and-limitations)).
- `.env.example` documents `ENVIRONMENT`, `LOG_LEVEL`, `CORS_ORIGINS` and `MAX_UPLOAD_BYTES` as commented defaults and no longer sets `STORAGE_ROOT` (previously KI-26 / KI-1, fixed in P0). It still omits `EMBEDDING_DIMENSIONS`, `LLM_TIMEOUT_SECONDS` and `DB_CONNECT_TIMEOUT_SECONDS` (they work if set — see the [environment reference](../reference/environment-reference.md)).
- `NEXT_PUBLIC_API_URL` is read by Next.js from `apps/web/`, not from the repository-root `.env` ([KI-21](../reference/status.md#known-issues-and-limitations)).
- No config validation at startup beyond types; a missing model is reported when a provider is used.

Reference table: [environment variables](environment-variables.md).
