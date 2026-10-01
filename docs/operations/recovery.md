# Recovery

> Getting back to a working state after failures.

## Status

Partially implemented (in-app failure recording); operational recovery is manual.

## Application-level failures

Entities carry `status` and `error` so a failed step does not poison the project (a failed scene image affects only that scene/asset). Retrying a failed operation is **Planned — not implemented**: no retry endpoints or workflows exist. Design intent: [retry and recovery](../workflows/retry-and-recovery.md).

## Environment recovery

| Situation | Action |
| --- | --- |
| DB down / wrong URL | Fix `DATABASE_URL`, start DB, check `/health/ready` |
| Schema behind code | `make db-migrate` |
| Corrupt dev DB | Drop and recreate, `make db-migrate`; or restore a dump ([backups](backups.md)) |
| Docker-free cluster broken | Stop it with `cd apps/api && uv run --with pgserver python ../../scripts/dev_postgres.py --stop` (`pgserver` is not a project dependency, so a bare `python scripts/dev_postgres.py --stop` fails), delete `data/temporary/pgdata`, rerun `make db-up-nodocker`, migrate. **Deleting that directory deletes all data in the dev database** ([backups](backups.md)) |
| Stuck `.part` files | `LocalStorage.put` writes `<name>.part` and removes it in `finally`; a hard crash can leave one — safe to delete |
| Background job lost on API restart | `LocalRunner` is in-process and not durable; jobs are lost. Durable execution (Temporal) is Planned |

## Rebuilding derived data

Chunks/embeddings can be regenerated from transcripts once that workflow exists; timelines from scenes via `build_timeline`; renders from timelines. Until the workflows exist these are conceptual.
