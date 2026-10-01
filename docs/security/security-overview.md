# Security Overview

> Security posture of StoryWeaver today, and the rules new code must follow.

## Status

Partially implemented. Input hardening primitives exist; there is **no authentication or authorisation**.

## Posture

StoryWeaver is a single-user, local-first tool. The API trusts every caller. **Do not bind the API or the web app to a non-loopback interface or expose either to a network** until an auth model exists (Decision pending, see [deployment](../operations/deployment.md)). uvicorn defaults to `127.0.0.1`, but `next dev` binds beyond localhost and prints a LAN address, so the web dev server (which proxies nothing but serves the UI that talks to the unauthenticated API) is reachable from the local network unless started with `-H 127.0.0.1` ([KI-20](../reference/status.md#known-issues-and-limitations)). CORS restricts browsers to configured origins but does not protect against non-browser clients.

## Implemented controls

| Control | Where | Detail |
| --- | --- | --- |
| Secrets server-side only | `core/config.py` | Provider keys are read by the API; the browser gets `NEXT_PUBLIC_API_URL` only |
| Key-safe health output | `api/v1/health.py` | `/health/providers` returns booleans, never values; tested |
| Log redaction | `core/logging.py` | Key-name based, substring match: masks `output_tokens`/`max_tokens` too ([KI-2](../reference/status.md#known-issues-and-limitations)) and does not scrub exception text or message strings |
| URL allow-listing | `ingestion/youtube.py` | http(s) + YouTube hosts only, strict id patterns, 2048-char cap |
| Path traversal defence | `core/storage.py` | Keys resolved under root; absolute/`..`/NUL rejected; filename sanitiser |
| Streaming size-capped writes | `LocalStorage.put` | 1 MiB chunks, `MAX_UPLOAD_BYTES`, temp `.part` then rename |
| Parameterised SQL | SQLAlchemy | No string-built SQL (only fixed DDL strings in tests/health) |
| No shell from user input | ingestion | yt-dlp via Python API; no `subprocess` |
| Request-body validation | Pydantic | `extra="forbid"` on PATCH models, length limits on **create** models only. Update models have no length limits and accept explicit `null` ([KI-4](../reference/status.md#known-issues-and-limitations)) |
| Provider isolation | `intelligence/providers/base.py` | All provider HTTP in adapters; 120 s client timeout; transport/HTTP-status failures (`httpx.HTTPError`) wrapped as `ProviderError` without response bodies. **Only those**: a malformed 200 response raises raw `KeyError`/`IndexError`/`JSONDecodeError` ([KI-3](../reference/status.md#known-issues-and-limitations)) |

## Not implemented

Authentication, authorisation, rate limiting, upload endpoints (so file validation is unexercised; `LocalStorage` is not used by any route — [KI-9](../reference/status.md#known-issues-and-limitations)), mapping of typed errors to HTTP statuses ([KI-8](../reference/status.md#known-issues-and-limitations)), content-type sniffing, dependency/secret scanning, security headers, audit log, CI.

## Detail

[Secrets](secrets.md) · [Provider security](provider-security.md) · [Input validation](input-validation.md) · [File security](file-security.md) · [Local storage](local-storage-security.md) · [Threat model](threat-model.md) · [Security architecture](../architecture/security-architecture.md)
