# Logging

> Structured logging as implemented.

## Status

Partially implemented. Logger and redaction exist; HTTP request logging, correlation ids and log shipping do not.

## Implementation

`app/core/logging.py`: `configure_logging(level)` (called in `create_app`) sets structlog to emit one **JSON object per line** to stdout with `level` and ISO `timestamp`. A processor replaces the value of any event key whose name **contains** (substring match, case-insensitive) `key`, `token`, `secret`, `password`, `authorization` or `credential` with `***`. `get_logger(**ctx)` returns a bound logger.

The structlog JSON stream covers **application events only**. Uvicorn's own access and error log is plain text, not JSON, and is not routed through structlog, so a log collector sees two formats.

Events emitted today:

| Event | Where | Fields |
| --- | --- | --- |
| `llm.generated` | `LLMProvider.generate` | `provider`, `model`, `duration`, `output_tokens`, `status`. **`output_tokens` is emitted as `"***"`** because its name contains `token` ([KI-2](../reference/status.md#known-issues-and-limitations)); the real count is never visible in logs today |
| `llm.failed` | same | `provider`, `model`, `error` (exception class only) |
| `workflow.started/finished/failed` | `LocalRunner` | `workflow_id`, `workflow`, `status`, `error` |

## Rules

- Never log prompts/transcripts at INFO (privacy and size); never log request headers.
- Redaction is key-name based only: a secret placed inside a message string, an exception message (the workflow runner logs `error="<Type>: <message>"`) or an innocuously named field is **not** caught.
- Substring matching also produces **false positives**: `output_tokens`, `max_tokens` and any key merely containing `key` (e.g. `monkey`, `hotkey`) are masked ([KI-2](../reference/status.md#known-issues-and-limitations)). Choose log field names with this in mind (e.g. `output_count`) until redaction is changed.
- Bind context (`workflow_id`, `project_id`, `source_id`, `scene_id`, `provider`, `model`) where available — the target field list; `project_id`/`source_id`/`scene_id` are not yet bound anywhere because those workflows do not exist.

## Gaps / planned

Request/response access logging format, token usage and latency persisted to the database ([monitoring](monitoring.md)), log levels per module: Planned — not implemented.
