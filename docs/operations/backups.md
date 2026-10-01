# Backups

> What to back up and how, as guidance.

## Status

Planned — not implemented. Nothing automates backups. The commands below are manual guidance and have not been run as part of this project.

## What holds state

1. **PostgreSQL** — all metadata, transcripts, versions, embeddings.
2. **`data/`** — binary assets, transcripts files, renders (once workflows write them; today nothing writes there except what you place manually). Asset rows point into it via `storage_key`.
3. **`.env`** — keep in a password manager, not in backups of the repo.
4. **The Docker-free cluster** — with `make db-up-nodocker` the entire database lives in `data/temporary/pgdata`. That path is git-ignored (so it is never committed) and sits under a directory named `temporary`, which makes it easy to delete by accident (`rm -rf data/temporary`, or a "clean" script). Treat it as real data: `pg_dump` it (the helper prints the socket URL) before deleting or recreating it. Docker users keep data in the `pgdata` named volume instead; `docker compose down -v` destroys it.

## Manual guidance

```bash
pg_dump -Fc -d "<postgres url without +psycopg>" -f storyweaver-$(date +%F).dump
pg_restore --clean --if-exists -d <target db> storyweaver-<date>.dump
rsync -a --delete data/ /path/to/backup/data/     # or any file-level backup
```

Back up DB and `data/` at the same moment where possible: `assets.checksum` (sha256) lets you detect divergence later.

## Reproducible vs irreplaceable

Renders and generated images are regenerable in principle but cost compute; scripts, edits and source transcripts are the valuable data. Decision pending on retention policy ([data lifecycle](../data/data-lifecycle.md)).

See [recovery](recovery.md).
