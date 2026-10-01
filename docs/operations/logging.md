# Logging

> Structured logging as implemented.

## Status

Partially implemented. Logger and redaction exist; HTTP request logging, correlation ids and log shipping do not.

## Implementation

`app/core/logging.py`: `configure_logging(level)` (called in `create_app`) sets structlog to emit one **JSON object per line** to stdout with `level` and ISO `timestamp`. A processor masks (`***`) the value of any event key whose **final word** is a secret word (`api_key`, `secret`/`secret_key`, `password`, `authorization`, `credential(s)`, `bearer`, `token`/`access_token`/…) and scrubs secret-shaped substrings inside every string value. `get_logger(**ctx)` returns a bound logger.

The structlog JSON stream covers **application events only**. Uvicorn's own access and error log is plain text, not JSON, and is not routed through structlog, so a log collector sees two formats.

Events emitted today:

| Event | Where | Fields |
| --- | --- | --- |
| `llm.generated` | `LLMProvider.generate` | `provider`, `model`, `duration`, `output_tokens`, `status`. Token counts are logged as numbers (previously masked — KI-2, resolved in P0); nothing persists them yet |
| `llm.failed` | same | `provider`, `model`, `error` (exception class only) |
| `workflow.started/finished/failed` | `LocalRunner` | `workflow_id`, `workflow`, `status`, `error` |

## Rules

- Never log prompts/transcripts at INFO (privacy and size); never log request headers.
- Redaction is best-effort pattern matching: a secret in an unrecognised format, or split across fields, is **not** caught. Secret-shaped substrings in message strings and exception messages (the workflow runner logs `error="<Type>: <message>"`) are scrubbed, but do not rely on it — never put secrets or prompts in log fields.
- Redaction matches a key only when its **final word** is a secret word, so `output_tokens`, `max_tokens`, `cache_key` and `monkey` are kept, while `api_key`, `x-api-key`, `password`, `authorization` and `access_token` are masked as `***`. String values (including nested dicts/lists and exception text) are additionally scrubbed for secret-shaped substrings: `sk-…`, `AIza…`, `AQ.…`, `ghp_…`, `xox…`, SendGrid `SG.…`, `Bearer …` and `user:password@` in URLs. This is best-effort; do not log prompts or request bodies at INFO.
- Bind context (`workflow_id`, `project_id`, `source_id`, `scene_id`, `provider`, `model`) where available — the target field list; `project_id`/`source_id`/`scene_id` are not yet bound anywhere because those workflows do not exist.

## Gaps / planned

Request/response access logging format, token usage and latency persisted to the database ([monitoring](monitoring.md)), log levels per module: Planned — not implemented.
