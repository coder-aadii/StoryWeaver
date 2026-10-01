# Monitoring

> What observability exists and what is intentionally deferred.

## Status

Partially implemented (health endpoints and logs only).

## Exists

- `GET /api/v1/health` — liveness, no dependencies.
- `GET /api/v1/health/ready` — runs `SELECT 1` and checks the `vector` extension; HTTP 503 when not ready.
- `GET /api/v1/health/providers` — which LLM providers are configured, Ollama/ComfyUI reachability (2 s timeout), `temporal_configured`; no credentials. See [health and readiness](../api/health-and-readiness.md).
- Structured logs ([logging](logging.md)).
- Persisted per-entity `status`/`error` columns on channels, source videos, transcripts, projects, scenes, assets, renders.

## Planned — not implemented

Job progress records, provider latency and token usage tables (logged token counts are currently masked as `***` by the key-name redaction, so token-usage observability from logs is not possible as designed — [KI-2](../reference/status.md#known-issues-and-limitations)), generation/render duration metrics, failure-rate views. The design intent is "simple structured logs + database records" rather than a metrics stack; Prometheus/Grafana/OpenTelemetry are **Deferred until required by the production workflow**.

## Limitations

Provider health checks run synchronously per request; no alerting; no uptime monitoring. `GET /health/ready` swallows the underlying exception and logs nothing when the database check fails, and the engine has no connect timeout, so a probe against an unreachable host may be slow or hang ([KI-5](../reference/status.md#known-issues-and-limitations)). Uvicorn access logs are plain text, separate from the JSON application log.
