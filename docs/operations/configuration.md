# Configuration

> How configuration is loaded and where defaults live.

## Status

Implemented.

## Mechanism

`apps/api/app/core/config.py` defines `Settings` (pydantic-settings). Sources, highest priority first: process environment, then `<repo>/.env`. Unknown keys are ignored. `get_settings()` is `lru_cache`d — **restart the API after changing `.env`**.

Defaults make the app bootable with nothing set: Ollama URL `http://localhost:11434`, DB `postgresql+psycopg://storyweaver:storyweaver@localhost:5433/storyweaver`, storage root `<repo>/data`, upload cap 512 MiB. Exact defaults live in the [environment reference](../reference/environment-reference.md).

> **Warning — empty values are not "unset" ([KI-1](../reference/status.md#known-issues-and-limitations)).** `.env.example` ships `STORAGE_ROOT=` (empty). pydantic-settings parses an empty value as `Path('')`, i.e. `.`, so after `cp .env.example .env` the storage root becomes the process working directory (for example `apps/api`) instead of `<repo>/data`. The `<repo>/data` default applies only when the variable is **unset**. Workaround: delete or comment out the `STORAGE_ROOT=` line in `.env`. The same applies to any other variable you leave as an empty string and expect to fall back to a default (for string settings an empty value simply means "not configured").

## Groups

- **Database:** `DATABASE_URL`. (`POSTGRES_*` in `.env.example` feed Docker Compose only.)
- **Storage:** `STORAGE_ROOT`, `MAX_UPLOAD_BYTES`.
- **Providers:** `OLLAMA_BASE_URL`, `GOOGLE_AI_API_KEY`, `GROK_API_KEY`, `OPENROUTER_API_KEY`, `ANTHROPIC_BASE_URL`, `ANTHROPIC_API_KEY`, `COMFYUI_BASE_URL`, `TEMPORAL_ADDRESS`.
- **Model routing:** `DEFAULT_LLM_PROVIDER`, `DEFAULT_LLM_MODEL`, `ANALYSIS_LLM_MODEL`, `STORY_LLM_MODEL`, `SCRIPT_LLM_MODEL`, `CLASSIFICATION_LLM_MODEL`, `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`. `Settings.model_for(task)` falls back to `DEFAULT_LLM_MODEL`. See [model routing](../ai/model-routing.md).
- **App:** `ENVIRONMENT`, `LOG_LEVEL`, `CORS_ORIGINS` (a JSON array, e.g. `["http://localhost:3100"]`, as parsed by pydantic-settings).
- **Web:** `NEXT_PUBLIC_API_URL` (browser-visible, contains no secrets). Put it in `apps/web/.env.local` or the shell ([KI-21](../reference/status.md#known-issues-and-limitations)).

## Gaps

- `EMBEDDING_DIMENSIONS` exists in `Settings` (default 768) but the DB column width is the separate constant `EMBEDDING_DIM` in `models/domain.py`; the two are independent and unchecked ([KI-6](../reference/status.md#known-issues-and-limitations)).
- `.env.example` omits `ENVIRONMENT`, `LOG_LEVEL`, `CORS_ORIGINS`, `MAX_UPLOAD_BYTES`, `EMBEDDING_DIMENSIONS` (they work if set), and ships the empty `STORAGE_ROOT=` described above ([KI-26](../reference/status.md#known-issues-and-limitations)). The file is outside `docs/` and has not been changed.
- `NEXT_PUBLIC_API_URL` is read by Next.js from `apps/web/`, not from the repository-root `.env` ([KI-21](../reference/status.md#known-issues-and-limitations)).
- No config validation at startup beyond types; a missing model is reported when a provider is used.

Reference table: [environment variables](environment-variables.md).
