# Security Architecture

> The security posture of StoryWeaver as a local-first, single-user tool, and what must change before it is exposed anywhere.

## Status

**Partially implemented.** Input/path hardening primitives exist; **authentication, authorisation, rate limiting, TLS and multi-tenancy do not**. Detailed docs: [security/security-overview](../security/security-overview.md), [security/threat-model](../security/threat-model.md).

## Purpose

State the trust assumptions and the controls that actually exist, so nobody mistakes the dev setup for a hardened deployment.

## Current implementation

| Control | Where | Notes |
| --- | --- | --- |
| Secrets only in `.env` (git-ignored); `.env.example` contains no secrets or API keys (dev-only defaults) | `.gitignore`, `.env.example` | Keys read by the API only; `NEXT_PUBLIC_*` is the only browser-visible config |
| Provider status without secrets | `/api/v1/health/providers` | Booleans only; covered by a test that a key does not appear in the response |
| Log redaction by key name | `core/logging.py` | Keys containing `key/token/secret/password/authorization/credential` → `***`. Name-based: secrets embedded in message *values* are not detected |
| Path traversal protection | `LocalStorage.path_for` | Rejects absolute, NUL, `..` escapes (tests) |
| Filename sanitising, streaming size cap | `sanitize_filename`, `LocalStorage.put` | No upload endpoint yet |
| YouTube URL allow-list | `ingestion/youtube.py` `classify_youtube_url` | Scheme must be http(s); host must be in an exact allow-list; video id regex; length ≤ 2048 (tests include look-alike hosts and `file://`) |
| Parameterised SQL | SQLAlchemy ORM | No raw string SQL in app code |
| Request validation | Pydantic v2; `extra="forbid"` on patch models | Unknown fields in PATCH → 422 |
| CORS allow-list | `Settings.cors_origins` (localhost:3000, :3100) | Methods/headers `*` |
| Compose binds to 127.0.0.1 | `docker-compose.yml` | Postgres and optional services |
| No shell execution of user input | — | yt-dlp is used via its Python API; no `subprocess` calls exist yet |

## Target architecture

Before any non-localhost use (**Decision pending** — deployment is not planned): authentication and per-user ownership of projects/sources, authorisation checks in every route, rate limiting, TLS via a reverse proxy, secret management beyond `.env`, upload endpoints with content-type/magic-byte validation, audit logging, dependency scanning. Renderer/subprocess invocation by argument list only.

## Components and responsibilities

API: validate and authorise. Storage layer: path safety. Providers: keep keys server-side; never log request headers or bodies. UI: no secrets.

## Data flow

Untrusted inputs: URLs, uploaded files/transcripts, source text (and therefore LLM prompts — prompt injection via transcripts is a real risk once generation exists), API payloads. Trust boundary: the API process.

## Failure modes

Malicious/looking-alike URL → `InvalidSourceError` (not yet mapped to an HTTP status); oversized file → `ValueError`; hostile transcript steering an LLM → output must still pass schema validation and must never trigger tool/shell actions.

## Extension points

Add auth as FastAPI dependencies on the router; add validators beside `classify_youtube_url` for new source kinds ([security/input-validation](../security/input-validation.md)).

## Current limitations

- **No authentication**: anyone who can reach port 8000 can read/modify/delete all data. Keep it on localhost.
- CORS wildcard methods/headers; no CSRF concern only because there are no cookies/sessions.
- yt-dlp fetches arbitrary-resolved media for allow-listed hosts only, but redirects/extractor behaviour inside yt-dlp are not audited.
- Dev Postgres defaults (`storyweaver/storyweaver`) are for local use only.
- Error types are not mapped to HTTP responses, so some failures would surface as 500 ([KI-8](../reference/status.md#known-issues-and-limitations)).
- API-created `sources`/`channels` rows are not URL-validated ([KI-12](../reference/status.md#known-issues-and-limitations)); the Next.js dev server binds beyond localhost, so the UI is LAN-reachable ([KI-20](../reference/status.md#known-issues-and-limitations)); log redaction is by key name only ([KI-2](../reference/status.md#known-issues-and-limitations)); `TEST_DATABASE_URL` is destructive and unguarded ([KI-19](../reference/status.md#known-issues-and-limitations)).

## Future evolution

See [security/threat-model](../security/threat-model.md) and [operations/deployment](../operations/deployment.md).
