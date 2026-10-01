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

Job progress records, provider latency and token usage tables (`output_tokens` is logged as a number by `llm.generated`; nothing persists or aggregates it yet), generation/render duration metrics, failure-rate views. The design intent is "simple structured logs + database records" rather than a metrics stack; Prometheus/Grafana/OpenTelemetry are **Deferred until required by the production workflow**.

## Limitations

Provider health checks run synchronously per request; no alerting; no uptime monitoring. `GET /health/ready` logs `health.ready.failed` on failure and the engine has a connect timeout (`DB_CONNECT_TIMEOUT_SECONDS`; previously KI-5). Uvicorn access logs are plain text, separate from the JSON application log.
