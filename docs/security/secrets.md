# Secrets

> Handling API keys and credentials.

## Status

Implemented (conventions and ignore rules); no secrets manager.

## Rules

- Secrets live in `.env` (git-ignored: `.env`, `.env.*` except `.env.example`) or the process environment. `.env.example` contains only empty placeholders and local-dev DB defaults.
- Keys: `GOOGLE_AI_API_KEY`, `GROK_API_KEY`, `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`; DB password inside `DATABASE_URL`; MinIO password for the optional profile. Full table: [environment reference](../reference/environment-reference.md); handling guidance: [environment variables](../operations/environment-variables.md).
- Never put secrets in `NEXT_PUBLIC_*` variables (they are shipped to the browser).
- Send keys in headers (`Authorization`, `x-api-key`, `x-goog-api-key`), not URLs, so they do not land in access logs or exceptions. Adapters follow this.
- Never log keys; redaction is key-name based (substring match on the field name), so do not interpolate secrets into message strings, and remember that exception text logged by the workflow runner is not scrubbed ([KI-2](../reference/status.md#known-issues-and-limitations)).
- Compose defaults (`storyweaver/storyweaver`) are for localhost only; change them if the DB port is ever reachable beyond loopback (it binds `127.0.0.1`).

## Verification done

Before the initial commit a pattern scan of tracked files for key-like assignments found nothing, and no `.env` was tracked. This was a one-time manual check; **no automated secret scanning** runs. Planned: pre-commit/CI scanner (Decision pending).

## If a key leaks

Revoke at the provider, replace in `.env`, restart the API (settings are cached). Rewriting git history does not un-leak a pushed key.
