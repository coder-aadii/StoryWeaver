# Security Overview

> Security posture of StoryWeaver today, and the rules new code must follow.

## Status

Partially implemented. Input hardening primitives exist; there is **no authentication or authorisation**.

## Posture

StoryWeaver is a single-user, local-first tool. The API trusts every caller. **Do not bind the API or the web app to a non-loopback interface or expose either to a network** until an auth model exists (Decision pending, see [deployment](../operations/deployment.md)). The supported commands bind both dev servers to `127.0.0.1` (`make dev-api` uses `--host 127.0.0.1`; the web scripts use `-H 127.0.0.1`; previously KI-20, resolved in P0). CORS restricts browsers to configured origins but does not protect against non-browser clients.

## Implemented controls

| Control | Where | Detail |
| --- | --- | --- |
| Secrets server-side only | `core/config.py` | Provider keys are read by the API; the browser gets `NEXT_PUBLIC_API_URL` only |
| Key-safe health output | `api/v1/health.py` | `/health/providers` returns booleans, never values; tested |
| Log redaction | `core/logging.py` | A key is secret if its final word is a secret word (`api_key`, `password`, `authorization`, `token`/`access_token`, …), so `output_tokens` is kept; string values (including exception text) are scrubbed for secret-shaped substrings. Best-effort, not a guarantee |
| URL allow-listing | `ingestion/youtube.py`, `schemas/resources.py` | http(s) + YouTube hosts only, strict id patterns, 2048-char cap; sources are created only via the validating `from-url`/`from-transcript` routes. Caption downloads additionally require `https` and a `youtube.com`/`googlevideo.com` host (no credentials, redirects and playlist segments re-checked) |
| Transcript upload validation | `api/v1/sources.py`, `ingestion/parsers.py` | Extension allow-list, `MAX_TRANSCRIPT_BYTES`, strict UTF-8, bounded parsing, filenames never used as paths ([file security](file-security.md)) |
| Search output encoding | `ingestion/queries.py`, web `safe-snippet.tsx` | Server HTML-escapes snippets (only `<mark>` survives); the web app renders them as text |
| Path traversal defence | `core/storage.py` | Keys resolved under root; absolute/`..`/NUL rejected; filename sanitiser |
| Streaming size-capped writes | `LocalStorage.put` | 1 MiB chunks, `MAX_UPLOAD_BYTES`, temp `.part` then rename |
| Parameterised SQL | SQLAlchemy | No string-built SQL (only fixed DDL strings in tests/health) |
| No shell from user input | ingestion | yt-dlp via Python API; no `subprocess`; `skip_download` is forced so no media is fetched |
| Request-body validation | Pydantic | `extra="forbid"` on PATCH models, length limits on create **and** update models, `null` rejected on NOT NULL fields, URL validation on source/channel create (previously KI-4/KI-12, resolved in P0) |
| Provider isolation | `intelligence/providers/base.py` | All provider HTTP in adapters; configurable client timeout (`LLM_TIMEOUT_SECONDS`, default 120 s); every failure wrapped into the `ProviderError` family without URLs, headers or bodies (previously KI-3, resolved in P0); mocked-HTTP contract tests only |

## Not implemented

Authentication, authorisation, rate limiting, image/audio/video upload and any file-serving endpoint (`LocalStorage` is used only by the transcript ingestion — [KI-9](../reference/status.md#known-issues-and-limitations)), content-type sniffing beyond the extension allow-list (transcripts are decoded as strict UTF-8 text), dependency/secret scanning, security headers, audit log, CI. (Typed errors are now mapped to HTTP statuses with stable codes — previously KI-8.)

## Detail

[Secrets](secrets.md) · [Provider security](provider-security.md) · [Input validation](input-validation.md) · [File security](file-security.md) · [Local storage](local-storage-security.md) · [Threat model](threat-model.md) · [Security architecture](../architecture/security-architecture.md)
