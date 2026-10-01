# Authentication

> Current (none) and target authentication posture of the API.

## Status

**Planned — not implemented.** The API has no authentication or authorization. Any process that can reach the port can read, modify or delete everything.

## Current implementation

- No users table, tokens, sessions or API keys.
- CORS restricts browsers to configured origins but is **not** a security control for other clients.
- Mitigation: run on localhost only; do not expose port 8000. See [security-overview](../security/security-overview.md) and [threat-model](../security/threat-model.md).
- Provider keys (LLM, etc.) live in server-side `.env` and are never returned by any endpoint.

## Target

Single-user local tool first; multi-user is not a goal yet ([product/goals-and-non-goals](../product/goals-and-non-goals.md)). Options if the API is ever exposed (e.g. self-hosted on a LAN or cloud): a static bearer token from env, or OIDC. **Decision pending**; deferred until required by the production workflow. Any scheme should be a FastAPI dependency applied at the router level (`api/v1/router.py`), requiring no changes per resource.

Related: [API-conventions](API-conventions.md)
