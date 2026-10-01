# Deployment

> Deployment status: there is none, by design.

## Status

Planned — not implemented. StoryWeaver is local-first and has no authentication; **do not expose the API or web app beyond localhost**. Note that `next dev` binds beyond localhost by default (it prints a LAN address), so the web dev server is reachable from the local network unless you bind it to `127.0.0.1` (for example `next dev -H 127.0.0.1`) ([KI-20](../reference/status.md#known-issues-and-limitations)).

## Today

Development only: apps run on the host with `uvicorn` / `next dev`; Postgres via Compose or the Docker-free helper ([local environment](local-environment.md)). `next build` succeeds, which is the only production-style artifact verified.

## Not present

Dockerfiles, CI/CD, TLS/reverse proxy, authentication/authorisation, rate limiting, secrets manager integration, multi-user isolation, process supervision, workers for long jobs, object storage.

## Decision pending

- Single-machine self-hosting (compose with api/web images) versus cloud.
- Whether rendering/image generation move to a separate GPU worker (`services/` exists for that, empty).
- Auth model before any network exposure ([security overview](../security/security-overview.md)).

Related: [scalability](../architecture/scalability.md), [ADR-006](../decisions/ADR-006-modular-monolith.md).
