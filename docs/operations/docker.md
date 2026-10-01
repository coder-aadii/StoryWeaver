# Docker

> What `docker-compose.yml` provides.

## Status

Partially implemented. The file exists and is syntactically plain, but it was **never run** (Docker was unavailable on the dev machine). Treat it as unverified.

## Services

| Service | Image | Profile | Notes |
| --- | --- | --- | --- |
| `postgres` | `pgvector/pgvector:pg16` | default | Binds `127.0.0.1:${POSTGRES_PORT:-5433}`; volume `pgdata`; mounts `infrastructure/postgres/init` (creates the `vector` extension on first init); `pg_isready` healthcheck |
| `temporal` | `temporalio/temporal:latest` | `temporal` | `server start-dev`, ports 7233 and UI 8233. **Not used by any code** |
| `minio` | `minio/minio:latest` | `storage` | Ports 9000/9001, volume `miniodata`. **Not used by any code** (storage is local files) |

## Commands

```bash
make db-up        # docker compose up -d --wait postgres
make db-down      # docker compose down  (keeps volumes)
docker compose --profile temporal up -d temporal
```

Remove data: `docker compose down -v` (destructive).

## Notes and gaps

- Credentials default to `storyweaver/storyweaver`; local development only. MinIO's default password is a placeholder.
- Images use `latest` for Temporal/MinIO; pinning is a Decision pending.
- The init script only runs on an empty data volume; migrations also issue `CREATE EXTENSION IF NOT EXISTS vector`.
- No Dockerfiles for api/web; apps run on the host (`infrastructure/docker/` is a placeholder). Production images: Planned — not implemented ([deployment](deployment.md)).
